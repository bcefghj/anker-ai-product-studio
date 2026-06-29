"""行业专家 Agent：技术/供应链/BOM/合规可行性 + Reflexion 批判。"""
from __future__ import annotations

from typing import List

from anker_studio.application.agents.base import Agent
from anker_studio.application.graph.state import PipelineState
from anker_studio.common.models import FeasibilityAssessment, ProductConcept, RiskItem


class IndustryExpertAgent(Agent):
    name = "行业专家"
    role = "可行性评估 / 规格定义 / Reflexion 批判"

    def run(self, state: PipelineState) -> PipelineState:
        concept = state.chosen_concept
        if concept is None:
            return state

        risks = self._assess_risks(concept)
        overall = self._overall(risks)
        ev_ids = [t.evidence_ids[0] for t in (state.market_intel.trends if state.market_intel else []) if t.evidence_ids][:2]

        assessment = FeasibilityAssessment(
            technical=(
                "核心降噪/听力个性化可在 Thus 类端侧 AI 芯片上实时运行；"
                "实时翻译类重负载建议端云协同，首发可裁剪。"
            ),
            supply_chain="端侧 AI 芯片与多麦克风方案需锁定产能；建议双供应商。",
            bom_cost="端侧 AI 模组抬高 BOM，首发聚焦 2–3 个高价值能力以控成本。",
            compliance="助听类功能在部分市场受医疗器械法规约束，需分区合规。",
            overall=overall,
            risks=risks,
            evidence_ids=ev_ids,
        )
        state.feasibility = assessment

        for r in risks:
            state.add_claim(f"可行性风险（{r.area}）：{r.description}", ev_ids)
        if self.tracer:
            self.tracer.emit(self.name, "result", overall=overall, risks=len(risks))
        return state

    def _assess_risks(self, concept: ProductConcept) -> List[RiskItem]:
        risks: List[RiskItem] = [
            RiskItem(
                area="bom_cost",
                description="端侧 AI 芯片+多麦克风抬高物料成本，可能挤压中端价位毛利。",
                severity="high",
                mitigation="首发只上最高价值能力，其余 OTA；规模化后降本。",
            ),
            RiskItem(
                area="technical",
                description="端侧实时性能/功耗与体验承诺之间存在权衡。",
                severity="medium",
                mitigation="按场景动态调度算力，设保守标称值。",
            ),
        ]
        text = " ".join(concept.key_features).lower()
        if "翻译" in text or "translate" in text:
            risks.append(
                RiskItem(
                    area="technical",
                    description="实时翻译重负载难全端侧，体验受限。",
                    severity="high",
                    mitigation="端云协同；首发降级为离线常用语种。",
                )
            )
        diff_text = " ".join(d.statement for d in concept.differentiators)
        if any("听力" in f for f in concept.key_features) or "听力" in diff_text:
            risks.append(
                RiskItem(
                    area="compliance",
                    description="听力个性化/助听在欧美受医疗法规约束。",
                    severity="medium",
                    mitigation="分区合规，必要时定位为辅助而非医疗。",
                )
            )
        return risks

    @staticmethod
    def _overall(risks: List[RiskItem]) -> str:
        highs = sum(1 for r in risks if r.severity == "high")
        if highs >= 2:
            return "red"
        if highs == 1:
            return "yellow"
        return "green"
