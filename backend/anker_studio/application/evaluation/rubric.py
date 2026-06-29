"""评测 Rubric（Application 层），对标 VitaBench 风格的可解释成功率定义。

维度：groundedness / faithfulness / citation_hit_rate / opportunity_coverage /
persona_fidelity / mean_iterations / explainability。设质量门槛。
"""
from __future__ import annotations

from anker_studio.application.graph.state import PipelineState
from anker_studio.common.citations import evaluate_citations
from anker_studio.common.models import RubricScore
from anker_studio.infrastructure.nlp.lexicons import ASPECT_LEXICON

# 质量门槛（不达标应触发重试/降级或人工复核）
GATES = {"groundedness": 0.6, "faithfulness": 0.5, "citation_hit_rate": 0.8}


def evaluate(state: PipelineState) -> RubricScore:
    cites = evaluate_citations(state.claims, state.all_evidences(), aspect_terms=ASPECT_LEXICON)

    voc = state.voc_report
    concept = state.chosen_concept
    if voc and concept and voc.opportunities:
        top_ids = {o.id for o in voc.opportunities[:5]}
        addressed = set(concept.addressed_opportunity_ids)
        coverage = round(len(top_ids & addressed) / min(5, len(voc.opportunities)), 4)
    else:
        coverage = 0.0

    if state.personas:
        grounded_personas = sum(1 for p in state.personas if p.derived_from_evidence_ids)
        persona_fidelity = round(grounded_personas / len(state.personas), 4)
    else:
        persona_fidelity = 0.0

    # 平均检索迭代：think_tank 累计 / 白空间机会数（近似）
    ws = len(state.market_intel.white_space_opportunities) if state.market_intel else 0
    mean_iter = round(state.retrieval_iters / ws, 2) if ws else float(state.retrieval_iters)

    # 可解释性：是否产出了 DecisionRecord（含 rationale + conditions）
    explainability = 1.0 if (state.decision and state.decision.rationale) else 0.0

    overall = round(
        0.25 * cites["groundedness"]
        + 0.2 * cites["faithfulness"]
        + 0.15 * cites["citation_hit_rate"]
        + 0.2 * coverage
        + 0.1 * persona_fidelity
        + 0.1 * explainability,
        4,
    )

    notes = []
    for k, threshold in GATES.items():
        if cites.get(k, 0.0) < threshold:
            notes.append(f"未过门槛：{k}={cites.get(k,0.0)} < {threshold}")

    return RubricScore(
        groundedness=cites["groundedness"],
        faithfulness=cites["faithfulness"],
        citation_hit_rate=cites["citation_hit_rate"],
        opportunity_coverage=coverage,
        persona_fidelity=persona_fidelity,
        mean_iterations=mean_iter,
        explainability=explainability,
        overall=overall,
        notes=notes,
    )
