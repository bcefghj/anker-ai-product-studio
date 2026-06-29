"""端到端 Runner（Application 层）：装配数据 → RAG → 图 → 评测 → 对比。

被 CLI 与 FastAPI 复用。支持 HITL 暂停/恢复。
"""
from __future__ import annotations

import time
from typing import Optional

from pydantic import BaseModel

from anker_studio.application.baseline.experience_driven import run_experience_driven
from anker_studio.application.evaluation.comparison import build_comparison
from anker_studio.application.evaluation.rubric import evaluate
from anker_studio.application.graph.checkpoint import JsonCheckpointer
from anker_studio.application.graph.pipeline import build_studio_graph
from anker_studio.application.graph.state import PipelineState
from anker_studio.common.config import settings
from anker_studio.common.logging import log
from anker_studio.common.models import ComparisonReport, RubricScore
from anker_studio.infrastructure.data.loader import load_evidence, split_by_brand
from anker_studio.infrastructure.llm.gateway import LLMGateway
from anker_studio.infrastructure.observability.trace import Tracer
from anker_studio.infrastructure.rag.retrieval import build_rag

DEFAULT_BRIEF = "为 soundcore 设计下一款 TWS 耳机：用 AI 原生方法从洞察到定义，跑通一次。"


class RunArtifacts(BaseModel):
    run_id: str
    awaiting_human: bool = False
    thread_id: str = "default"
    state: PipelineState
    rubric: Optional[RubricScore] = None
    comparison: Optional[ComparisonReport] = None
    elapsed_seconds: float = 0.0


def _finalize(state: PipelineState, run_id: str, elapsed: float, brief: str,
              gateway: LLMGateway, thread_id: str) -> RunArtifacts:
    rubric = evaluate(state)
    baseline = run_experience_driven(state.category, brief, gateway)
    comparison = build_comparison(state, baseline, brief)
    comparison.arm_b.elapsed_seconds = round(elapsed, 3)
    log.bind(node="runner").info(
        f"完成：决策={state.decision.verdict.value if state.decision else 'n/a'} "
        f"NPS={state.nps.score if state.nps else 'n/a'} 总分={rubric.overall}"
    )
    return RunArtifacts(
        run_id=run_id, awaiting_human=False, thread_id=thread_id,
        state=state, rubric=rubric, comparison=comparison,
        elapsed_seconds=round(elapsed, 3),
    )


def run_studio(
    category: str = "audio",
    brief: str = DEFAULT_BRIEF,
    hitl: Optional[bool] = None,
    thread_id: str = "default",
    tracer: Optional[Tracer] = None,
) -> RunArtifacts:
    cfg = settings()
    hitl = cfg.hitl if hitl is None else hitl
    gateway = LLMGateway.from_settings(cfg)
    tracer = tracer or Tracer()

    evidences = load_evidence(category)
    split = split_by_brand(evidences)
    state = PipelineState(
        category=category,
        target_brand="soundcore",
        brief=brief,
        target_evidences=split["target"],
        competitor_evidences=split["competitors"],
    )
    if not state.target_evidences:
        log.bind(node="runner").warning(
            "未找到 soundcore 目标评论：将用全部评论兜底（请检查 data/ 数据）。"
        )
        state.target_evidences = evidences

    rag = build_rag(evidences)
    graph = build_studio_graph(gateway, rag, tracer, hitl=hitl)
    checkpointer = JsonCheckpointer()

    start = time.time()
    state = graph.run(state, checkpointer=checkpointer, thread_id=thread_id)
    if state.awaiting_human:
        log.bind(node="runner").warning("流程在决策闸暂停（HITL）。调用 resume_studio 继续。")
        return RunArtifacts(
            run_id=tracer.run_id, awaiting_human=True, thread_id=thread_id, state=state,
            elapsed_seconds=round(time.time() - start, 3),
        )
    return _finalize(state, tracer.run_id, time.time() - start, brief, gateway, thread_id)


def resume_studio(thread_id: str = "default", tracer: Optional[Tracer] = None) -> RunArtifacts:
    """HITL：人工确认后从 checkpoint 恢复。"""
    cfg = settings()
    gateway = LLMGateway.from_settings(cfg)
    tracer = tracer or Tracer()
    checkpointer = JsonCheckpointer()
    loaded = checkpointer.load(thread_id)
    if loaded is None:
        raise RuntimeError(f"无 checkpoint 可恢复：thread_id={thread_id}")

    # 重新装配图与 RAG（用 checkpoint 中的 state 数据）
    state, _ = loaded
    rag = build_rag(state.all_evidences())
    graph = build_studio_graph(gateway, rag, tracer, hitl=cfg.hitl)
    start = time.time()
    state = graph.run(state, checkpointer=checkpointer, thread_id=thread_id, resume=True)
    return _finalize(state, tracer.run_id, time.time() - start, state.brief, gateway, thread_id)
