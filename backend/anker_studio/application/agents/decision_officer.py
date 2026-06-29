"""决策官 Agent：NPS 预测 + GO / NO-GO 决策 + DecisionRecord。"""
from __future__ import annotations

from typing import List

from anker_studio.application.agents.base import Agent
from anker_studio.application.graph.state import PipelineState
from anker_studio.application.platforms.bees import predict_nps
from anker_studio.common.models import DecisionRecord, DecisionVerdict


class DecisionOfficerAgent(Agent):
    name = "决策官"
    role = "NPS 预测 / GO-NO-GO / 审计记录"

    def run(self, state: PipelineState) -> PipelineState:
        voc = state.voc_report
        concept = state.chosen_concept
        if voc is None or concept is None:
            return state

        addressed_aspects = self._addressed_aspects(state)
        nps = predict_nps(voc, state.interviews, addressed_aspects)
        state.nps = nps

        feas = state.feasibility
        avg_acc = (
            sum(i.acceptance for i in state.interviews) / len(state.interviews)
            if state.interviews else 0.5
        )

        verdict, conditions, confidence = self._decide(nps.score, feas, avg_acc)

        record = DecisionRecord(
            verdict=verdict,
            confidence=round(confidence, 2),
            nps_prediction=nps.score,
            rationale=(
                f"NPS 预测 {nps.score:.0f}；可行性 {feas.overall if feas else 'n/a'}；"
                f"合成用户平均接受度 {avg_acc:.0%}。"
            ),
            conditions=conditions,
            evidence_ids=nps.evidence_ids,
            reviewer="ai",
        )
        state.decision = record
        state.add_claim(f"决策：{verdict.value}，预测 NPS {nps.score:.0f}", nps.evidence_ids)

        if self.tracer:
            self.tracer.emit(
                self.name, "result",
                verdict=verdict.value, nps=nps.score, confidence=record.confidence,
            )
        return state

    @staticmethod
    def _addressed_aspects(state: PipelineState) -> List[str]:
        aspects = []
        opp_by_id = {o.id: o for o in (state.voc_report.opportunities if state.voc_report else [])}
        for oid in (state.chosen_concept.addressed_opportunity_ids if state.chosen_concept else []):
            o = opp_by_id.get(oid)
            if o:
                aspects.append(o.aspect)
        return aspects

    @staticmethod
    def _decide(nps: float, feas, avg_acc: float):
        conditions: List[str] = []
        overall = feas.overall if feas else "yellow"
        confidence = 0.5 + min(0.3, avg_acc * 0.3) + (0.1 if nps > 0 else -0.1)

        if overall == "red":
            conditions = [r.mitigation for r in (feas.risks if feas else []) if r.severity == "high"]
            return DecisionVerdict.CONDITIONAL_GO, conditions, confidence - 0.1
        if nps >= 20 and avg_acc >= 0.6 and overall in {"green", "yellow"}:
            return DecisionVerdict.GO, conditions, confidence + 0.1
        if nps <= -10 or avg_acc < 0.4:
            return DecisionVerdict.NO_GO, ["机会命中不足，需重做概念"], confidence
        conditions = [r.mitigation for r in (feas.risks if feas else []) if r.severity in {"high", "medium"}][:2]
        return DecisionVerdict.CONDITIONAL_GO, conditions, confidence
