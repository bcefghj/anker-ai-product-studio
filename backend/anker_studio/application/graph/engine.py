"""StateGraph 编排引擎（Application 层）。

语义对齐 LangGraph（节点 / 条件边 / checkpoint / interrupt_before），但为保持依赖
极轻、离线可复现而自研最小实现。借鉴 Harness 工程："错误即信息"（节点异常被记录后
按策略路由，而非直接崩溃）。
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Set

from anker_studio.application.graph.checkpoint import JsonCheckpointer
from anker_studio.application.graph.state import PipelineState
from anker_studio.common.logging import log
from anker_studio.infrastructure.observability.trace import Tracer

END = "__end__"
NodeFn = Callable[[PipelineState], PipelineState]
RouterFn = Callable[[PipelineState], str]


class StateGraph:
    def __init__(self, tracer: Optional[Tracer] = None, hitl: bool = False):
        self.nodes: Dict[str, NodeFn] = {}
        self.static_edges: Dict[str, str] = {}
        self.conditional: Dict[str, RouterFn] = {}
        self.entry: Optional[str] = None
        self.interrupt_before: Set[str] = set()
        self.tracer = tracer
        self.hitl = hitl

    def add_node(self, name: str, fn: NodeFn) -> "StateGraph":
        self.nodes[name] = fn
        return self

    def set_entry(self, name: str) -> "StateGraph":
        self.entry = name
        return self

    def add_edge(self, src: str, dst: str) -> "StateGraph":
        self.static_edges[src] = dst
        return self

    def add_conditional(self, src: str, router: RouterFn) -> "StateGraph":
        self.conditional[src] = router
        return self

    def set_interrupt_before(self, names: List[str]) -> "StateGraph":
        self.interrupt_before = set(names)
        return self

    def _next(self, node: str, state: PipelineState) -> str:
        if node in self.conditional:
            return self.conditional[node](state)
        return self.static_edges.get(node, END)

    def run(
        self,
        state: PipelineState,
        checkpointer: Optional[JsonCheckpointer] = None,
        thread_id: str = "default",
        resume: bool = False,
    ) -> PipelineState:
        if resume and checkpointer is not None:
            loaded = checkpointer.load(thread_id)
            if loaded is None:
                raise RuntimeError(f"无法恢复：找不到 checkpoint thread_id={thread_id}")
            state, current = loaded
            state.awaiting_human = False
            allow_interrupt = False  # 恢复后跳过这一次中断
        else:
            current = self.entry or END
            allow_interrupt = True

        steps = 0
        while current != END:
            steps += 1
            if steps > 100:
                log.bind(node="graph").error("步数超限，强制结束（防死循环）。")
                break

            if allow_interrupt and self.hitl and current in self.interrupt_before:
                if checkpointer is not None:
                    checkpointer.save(thread_id, state, current)
                state.awaiting_human = True
                if self.tracer:
                    self.tracer.emit(current, "interrupt", message="等待人工确认（HITL）")
                log.bind(node="graph").warning(f"在 '{current}' 前暂停，等待人工确认。")
                return state
            allow_interrupt = True

            fn = self.nodes.get(current)
            if fn is None:
                log.bind(node="graph").error(f"未知节点 '{current}'，结束。")
                break

            span_ctx = self.tracer.node_span(current) if self.tracer else _NullSpan()
            with span_ctx:
                try:
                    state = fn(state)
                except Exception as exc:  # noqa: BLE001 - 错误即信息
                    log.bind(node=current).error(f"节点异常：{exc}")
                    if self.tracer:
                        self.tracer.emit(current, "node_error", error=str(exc))
                    # 节点失败：记录后按静态边继续（降级），不崩溃
            current = self._next(current, state)
        return state


class _NullSpan:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False
