"""轻量 trace 观测（Infrastructure 层）。

把每个节点的执行写成 JSONL（runs/<run_id>.jsonl）+ 内存事件流，
供评测统计与前端实时可视化（对标 LangSmith/Langfuse 的最小可用形态）。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from anker_studio.common.config import settings
from anker_studio.common.logging import log


class Tracer:
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or time.strftime("run-%Y%m%d-%H%M%S")
        self.events: List[Dict[str, Any]] = []
        self.path: Path = settings().trace_path / f"{self.run_id}.jsonl"
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []

    def subscribe(self, fn: Callable[[Dict[str, Any]], None]) -> None:
        self._subscribers.append(fn)

    def emit(self, node: str, kind: str, **data: Any) -> None:
        event = {"ts": round(time.time(), 3), "node": node, "kind": kind, **data}
        self.events.append(event)
        try:
            with self.path.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        except OSError as exc:
            log.bind(node="trace").warning(f"trace 写入失败：{exc}")
        for fn in list(self._subscribers):
            try:
                fn(event)
            except Exception as exc:  # noqa: BLE001 - 订阅者异常不影响主流程
                log.bind(node="trace").warning(f"trace 订阅者异常：{exc}")

    def node_span(self, node: str):
        return _Span(self, node)


class _Span:
    def __init__(self, tracer: Tracer, node: str):
        self.tracer = tracer
        self.node = node
        self._start = 0.0

    def __enter__(self) -> "_Span":
        self._start = time.time()
        self.tracer.emit(self.node, "start")
        log.bind(node=self.node).info("开始")
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        elapsed = round((time.time() - self._start) * 1000, 1)
        if exc_type is not None:
            self.tracer.emit(self.node, "error", error=str(exc), elapsed_ms=elapsed)
            log.bind(node=self.node).error(f"失败：{exc}")
            return False
        self.tracer.emit(self.node, "end", elapsed_ms=elapsed)
        log.bind(node=self.node).info(f"完成 ({elapsed}ms)")
        return False

    def info(self, **data: Any) -> None:
        self.tracer.emit(self.node, "info", **data)
