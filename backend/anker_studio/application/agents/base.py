"""Agent 基类（Application 层）。

每个 Agent 通过注入的 LLMGateway / RagService 访问外部能力，禁止自行 import provider。
产出的论断都应带 evidence_ids。
"""
from __future__ import annotations

from typing import List, Optional

from anker_studio.application.graph.state import PipelineState
from anker_studio.infrastructure.llm.gateway import LLMGateway
from anker_studio.infrastructure.observability.trace import Tracer


class Agent:
    name: str = "agent"
    role: str = ""

    def __init__(
        self,
        gateway: LLMGateway,
        rag=None,
        tracer: Optional[Tracer] = None,
    ):
        self.gw = gateway
        self.rag = rag
        self.tracer = tracer

    def run(self, state: PipelineState) -> PipelineState:  # pragma: no cover - 抽象
        raise NotImplementedError

    @staticmethod
    def dedup(items: List[str]) -> List[str]:
        seen, out = set(), []
        for x in items:
            if x and x not in seen:
                seen.add(x)
                out.append(x)
        return out
