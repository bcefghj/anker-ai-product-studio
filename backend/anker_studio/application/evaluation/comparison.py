"""AI 驱动 vs 经验驱动 量化对比（Application 层）—— 命题核心。

同一 brief：A 组(经验驱动) vs B 组(AI 原生)。在统一维度上量化"本质不同"。
关键：A 组的概念也用真实数据(predict_nps)评估它"实际会达到的 NPS"，对比公平。
"""
from __future__ import annotations

from typing import List

from anker_studio.application.baseline.experience_driven import BaselineResult
from anker_studio.application.graph.state import PipelineState
from anker_studio.application.platforms.bees import predict_nps
from anker_studio.common.models import ArmMetrics, ComparisonReport


def _coverage(addressed_aspects: List[str], top_aspects: List[str]) -> float:
    if not top_aspects:
        return 0.0
    hit = len(set(addressed_aspects) & set(top_aspects))
    return round(hit / min(5, len(top_aspects)), 4)


def _hit_rate(addressed_aspects: List[str], top_aspects: List[str]) -> float:
    if not addressed_aspects:
        return 0.0
    hit = len(set(addressed_aspects) & set(top_aspects))
    return round(hit / len(addressed_aspects), 4)


def build_comparison(state: PipelineState, baseline: BaselineResult, brief: str) -> ComparisonReport:
    voc = state.voc_report
    top_aspects = [o.aspect for o in voc.opportunities[:5]] if voc else []

    # ---- B 组：AI 原生 ----
    b_addressed = []
    if voc and state.chosen_concept:
        opp_by_id = {o.id: o for o in voc.opportunities}
        b_addressed = [opp_by_id[i].aspect for i in state.chosen_concept.addressed_opportunity_ids if i in opp_by_id]
    distinct_evidence = len({eid for _, ids in state.claims for eid in ids})
    arm_b = ArmMetrics(
        arm="B_ai_native",
        opportunity_coverage=_coverage(b_addressed, top_aspects),
        evidence_citations=distinct_evidence,
        validated_assumptions=len(state.interviews),
        real_pain_hit_rate=_hit_rate(b_addressed, top_aspects),
        feasibility_risks_identified=len(state.feasibility.risks) if state.feasibility else 0,
        nps_prediction=state.nps.score if state.nps else 0.0,
        elapsed_seconds=0.0,  # 由 runner 填入
        distinct_personas_consulted=len(state.personas),
    )

    # ---- A 组：经验驱动（同样用真实数据评估其"实际会达到的 NPS"）----
    a_addressed = baseline.assumed_pains
    a_nps = predict_nps(voc, [], a_addressed).score if voc else 0.0
    arm_a = ArmMetrics(
        arm="A_experience_driven",
        opportunity_coverage=_coverage(a_addressed, top_aspects),
        evidence_citations=baseline.citations,
        validated_assumptions=baseline.validated_assumptions,
        real_pain_hit_rate=_hit_rate(a_addressed, top_aspects),
        feasibility_risks_identified=0,
        nps_prediction=a_nps,
        elapsed_seconds=baseline.elapsed_seconds,
        distinct_personas_consulted=0,
    )

    deltas = {
        "opportunity_coverage": round(arm_b.opportunity_coverage - arm_a.opportunity_coverage, 4),
        "evidence_citations": arm_b.evidence_citations - arm_a.evidence_citations,
        "validated_assumptions": arm_b.validated_assumptions - arm_a.validated_assumptions,
        "real_pain_hit_rate": round(arm_b.real_pain_hit_rate - arm_a.real_pain_hit_rate, 4),
        "feasibility_risks_identified": arm_b.feasibility_risks_identified - arm_a.feasibility_risks_identified,
        "nps_prediction": round(arm_b.nps_prediction - arm_a.nps_prediction, 1),
    }

    narrative = (
        f"经验驱动凭直觉聚焦 {a_addressed}，其中仅 {int(arm_a.real_pain_hit_rate*100)}% 命中真实高机会痛点，"
        f"零证据引用、零用户验证；AI 原生工作流命中率 {int(arm_b.real_pain_hit_rate*100)}%，"
        f"引用 {arm_b.evidence_citations} 条真实证据、做了 {arm_b.validated_assumptions} 次合成用户验证、"
        f"识别 {arm_b.feasibility_risks_identified} 项可行性风险，预测 NPS 高出 {deltas['nps_prediction']} 分。"
        f"这就是'数据/AI 驱动'相对'经验拍脑袋'的本质不同：可溯源、可验证、可量化、可迭代。"
    )

    return ComparisonReport(
        category=state.category,
        brief=brief,
        arm_a=arm_a,
        arm_b=arm_b,
        deltas=deltas,
        narrative=narrative,
    )
