"""流水线共享状态（Application 层）。

贯穿整个 AI 原生工作流的状态对象。节点读取并增量更新它。
`claims` 收集 (论断, evidence_ids) 供评测计算 groundedness/faithfulness。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from anker_studio.common.models import (
    DecisionRecord,
    Evidence,
    ExperiencePoint,
    FeasibilityAssessment,
    MarketIntel,
    NPSPrediction,
    Persona,
    PersonaInterview,
    PRFAQ,
    ProductConcept,
    ProductProposal,
    VocReport,
)


class PipelineState(BaseModel):
    # 输入
    category: str = "audio"
    target_brand: str = "soundcore"
    brief: str = ""

    # 数据
    target_evidences: List[Evidence] = Field(default_factory=list)
    competitor_evidences: Dict[str, List[Evidence]] = Field(default_factory=dict)
    trend_evidences: List[Evidence] = Field(default_factory=list)

    # 平台产物
    voc_report: Optional[VocReport] = None
    market_intel: Optional[MarketIntel] = None
    experience_trend: List[ExperiencePoint] = Field(default_factory=list)

    # 概念与验证
    concepts: List[ProductConcept] = Field(default_factory=list)
    chosen_concept: Optional[ProductConcept] = None
    personas: List[Persona] = Field(default_factory=list)
    interviews: List[PersonaInterview] = Field(default_factory=list)
    feasibility: Optional[FeasibilityAssessment] = None
    nps: Optional[NPSPrediction] = None

    # 决策与产出
    prfaq: Optional[PRFAQ] = None
    decision: Optional[DecisionRecord] = None
    proposal: Optional[ProductProposal] = None

    # 控制 / 评测
    pm_iteration: int = 0
    max_pm_iterations: int = 2
    retrieval_iters: int = 0
    claims: List[Tuple[str, List[str]]] = Field(default_factory=list)
    awaiting_human: bool = False

    def add_claim(self, text: str, evidence_ids: List[str]) -> None:
        self.claims.append((text, list(evidence_ids or [])))

    def all_evidences(self) -> List[Evidence]:
        evs: List[Evidence] = list(self.target_evidences) + list(self.trend_evidences)
        for lst in self.competitor_evidences.values():
            evs.extend(lst)
        return evs

    class Config:
        arbitrary_types_allowed = True
