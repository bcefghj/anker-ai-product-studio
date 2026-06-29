"""领域数据模型（Common 层）。

所有跨层数据均为 Pydantic v2 模型，禁止裸 dict 在层间传递。
模型贯穿：Evidence(可溯源底座) → VOC 洞察 → 竞品/趋势 → 概念 → 用户替身 →
可行性 → NPS → 决策 → 提案 → 评测/对比。
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ─────────────────────────── 可溯源底座 ───────────────────────────
class SourceType(str, Enum):
    REVIEW = "review"          # 用户评论（JML/BEES）
    COMPETITOR = "competitor"  # 竞品评论（AMI）
    TREND = "trend"            # 趋势信号
    WEB = "web"                # 网页/报告


class Evidence(BaseModel):
    """一切论断的可溯源单元。Agent 只能引用 Evidence。"""

    source_id: str
    source_type: SourceType = SourceType.REVIEW
    brand: str = "unknown"
    product: str = ""
    rating: Optional[float] = None
    text: str = ""
    date: Optional[str] = None
    url: Optional[str] = None
    helpful_votes: int = 0


# ─────────────────────────── VOC / JML / BEES ───────────────────────────
class AspectInsight(BaseModel):
    aspect: str
    mention_count: int = 0
    reach: float = Field(0.0, description="提及该 aspect 的评论占比 0-1")
    negative_rate: float = Field(0.0, description="负面提及占比 0-1")
    importance: float = Field(0.0, description="重要性 0-10 (由 reach 推导)")
    satisfaction: float = Field(0.0, description="满意度 0-10 (由正面率推导)")
    opportunity_score: float = Field(0.0, description="ODI: importance + max(importance-satisfaction,0)")
    impact_score: float = Field(0.0, description="Reach×(Severity+Value+Strategic)")
    representative_evidence_ids: List[str] = Field(default_factory=list)
    summary: str = ""


class Opportunity(BaseModel):
    id: str
    statement: str
    aspect: str = ""
    importance: float = 0.0
    satisfaction: float = 0.0
    reach: float = 0.0
    severity: float = 0.0
    opportunity_score: float = 0.0
    impact_score: float = 0.0
    origin: str = Field("voc", description="voc | competitor | trend")
    evidence_ids: List[str] = Field(default_factory=list)
    rationale: str = ""


class ExperiencePoint(BaseModel):
    """BEES 体验演化的一个时间/版本切片。"""

    aspect: str
    period: str
    mention_count: int
    negative_rate: float
    evidence_ids: List[str] = Field(default_factory=list)


# ─────────────────────────── 机会解决方案树 (OST) ───────────────────────────
class Experiment(BaseModel):
    statement: str
    assumption: str = ""
    method: str = ""


class SolutionNode(BaseModel):
    statement: str
    rationale: str = ""
    experiments: List[Experiment] = Field(default_factory=list)


class OpportunityNode(BaseModel):
    opportunity_id: str
    statement: str
    opportunity_score: float = 0.0
    solutions: List[SolutionNode] = Field(default_factory=list)


class OpportunitySolutionTree(BaseModel):
    outcome: str
    opportunities: List[OpportunityNode] = Field(default_factory=list)


class VocReport(BaseModel):
    category: str
    target_brand: str
    review_count: int = 0
    aspects: List[AspectInsight] = Field(default_factory=list)
    opportunities: List[Opportunity] = Field(default_factory=list)
    experience_trend: List[ExperiencePoint] = Field(default_factory=list)
    ost: Optional[OpportunitySolutionTree] = None


# ─────────────────────────── 竞品 / 趋势 (AMI / 超级智囊) ───────────────────────────
class CompetitorFinding(BaseModel):
    brand: str
    review_count: int = 0
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    white_space: List[str] = Field(default_factory=list, description="对手没做好 = 机会空白")
    evidence_ids: List[str] = Field(default_factory=list)


class TrendSignal(BaseModel):
    name: str
    direction: str = "up"
    summary: str = ""
    evidence_ids: List[str] = Field(default_factory=list)


class MarketIntel(BaseModel):
    competitors: List[CompetitorFinding] = Field(default_factory=list)
    trends: List[TrendSignal] = Field(default_factory=list)
    white_space_opportunities: List[Opportunity] = Field(default_factory=list)


# ─────────────────────────── 用户替身 (合成用户) ───────────────────────────
class Persona(BaseModel):
    id: str
    name: str
    segment: str
    demographics: str = ""
    ocean: Dict[str, float] = Field(default_factory=dict, description="大五人格 0-1")
    behaviors: List[str] = Field(default_factory=list)
    pains: List[str] = Field(default_factory=list)
    derived_from_evidence_ids: List[str] = Field(default_factory=list)
    summary: str = ""


class InterviewTurn(BaseModel):
    question: str
    answer: str
    sentiment: str = "neutral"  # positive | neutral | negative


class PersonaInterview(BaseModel):
    persona_id: str
    persona_name: str = ""
    segment: str = ""
    transcript: List[InterviewTurn] = Field(default_factory=list)
    verdict: str = "neutral"            # would_buy | maybe | would_not_buy
    objections: List[str] = Field(default_factory=list)
    must_fixes: List[str] = Field(default_factory=list)
    acceptance: float = Field(0.0, description="接受度 0-1")


# ─────────────────────────── 产品概念 / 提案 ───────────────────────────
class Differentiator(BaseModel):
    statement: str
    evidence_ids: List[str] = Field(default_factory=list)


class ProductConcept(BaseModel):
    id: str
    name: str
    category: str
    path: str = Field("voc_driven", description="voc_driven | tech_native")
    one_liner: str = ""
    target_segment: str = ""
    value_proposition: str = ""
    key_features: List[str] = Field(default_factory=list)
    differentiators: List[Differentiator] = Field(default_factory=list)
    tech_enablers: List[str] = Field(default_factory=list)
    addressed_opportunity_ids: List[str] = Field(default_factory=list)


class RiskItem(BaseModel):
    area: str  # technical | supply_chain | bom_cost | compliance | market
    description: str
    severity: str = "medium"  # low | medium | high
    mitigation: str = ""


class FeasibilityAssessment(BaseModel):
    technical: str = ""
    supply_chain: str = ""
    bom_cost: str = ""
    compliance: str = ""
    overall: str = Field("yellow", description="green | yellow | red")
    risks: List[RiskItem] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)


class NPSPrediction(BaseModel):
    score: float = Field(0.0, description="-100 .. 100")
    promoters: float = 0.0
    passives: float = 0.0
    detractors: float = 0.0
    rationale: str = ""
    evidence_ids: List[str] = Field(default_factory=list)


class FaqItem(BaseModel):
    question: str
    answer: str
    evidence_ids: List[str] = Field(default_factory=list)


class PRFAQ(BaseModel):
    headline: str = ""
    subheading: str = ""
    summary: str = ""
    customer_quote: str = ""
    maker_quote: str = ""
    call_to_action: str = ""
    external_faq: List[FaqItem] = Field(default_factory=list)
    internal_faq: List[FaqItem] = Field(default_factory=list)


class DecisionVerdict(str, Enum):
    GO = "GO"
    CONDITIONAL_GO = "CONDITIONAL_GO"
    NO_GO = "NO_GO"


class DecisionRecord(BaseModel):
    verdict: DecisionVerdict = DecisionVerdict.CONDITIONAL_GO
    confidence: float = 0.0
    nps_prediction: float = 0.0
    rationale: str = ""
    conditions: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    reviewer: str = "ai"  # ai | human
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ProductProposal(BaseModel):
    concept: ProductConcept
    prfaq: PRFAQ
    feasibility: FeasibilityAssessment
    nps: NPSPrediction
    addressed_opportunities: List[Opportunity] = Field(default_factory=list)
    decision: DecisionRecord
    concept_image_path: Optional[str] = None
    narration_audio_path: Optional[str] = None


# ─────────────────────────── 评测 / 对比 ───────────────────────────
class RubricScore(BaseModel):
    groundedness: float = 0.0          # 论断带引用的比例
    faithfulness: float = 0.0          # 引用与论断语义一致比例
    citation_hit_rate: float = 0.0     # 逐字命中率
    opportunity_coverage: float = 0.0  # 提案覆盖的高分机会比例
    persona_fidelity: float = 0.0      # 合成用户来自真实评论 grounding 的比例
    mean_iterations: float = 0.0
    explainability: float = 0.0
    overall: float = 0.0
    notes: List[str] = Field(default_factory=list)


class ArmMetrics(BaseModel):
    """单组（A 经验驱动 / B AI 原生）的指标。"""

    arm: str
    opportunity_coverage: float = 0.0
    evidence_citations: int = 0
    validated_assumptions: int = 0
    real_pain_hit_rate: float = 0.0
    feasibility_risks_identified: int = 0
    nps_prediction: float = 0.0
    elapsed_seconds: float = 0.0
    distinct_personas_consulted: int = 0


class ComparisonReport(BaseModel):
    category: str
    brief: str
    arm_a: ArmMetrics   # 经验驱动
    arm_b: ArmMetrics   # AI 原生
    deltas: Dict[str, float] = Field(default_factory=dict)
    narrative: str = ""


# ─────────────────────────── LLM ───────────────────────────
class LLMResponse(BaseModel):
    text: str
    model: str = ""
    provider: str = "offline"
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
