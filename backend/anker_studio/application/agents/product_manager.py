"""产品经理 Agent（编排）：双路径概念生成 + 迭代收敛。

- 路径①（VOC 驱动）：从机会分最高的真实痛点反推方案。
- 路径②（第一性原理 / 技术原生）：从能力跃迁（端侧 AI / Thus 芯片）正推新体验。
迭代时吸收用户替身的 must_fixes 与行业专家的风险，对方案做修订。
"""
from __future__ import annotations

from typing import List

from anker_studio.application.agents.base import Agent
from anker_studio.application.graph.state import PipelineState
from anker_studio.common.models import Differentiator, ProductConcept

# 安克技术原生使能器（来自公司调研：Thus 芯片 / eufy Edge / 端侧 AI）
TECH_ENABLERS = [
    "Thus™ 存算一体(CIM)端侧 AI 芯片（算力较上代 +150x）",
    "多麦克风 + 骨传导端侧人声分离",
    "端侧听力轮廓个性化",
]


class ProductManagerAgent(Agent):
    name = "产品经理"
    role = "需求拆解 / 概念生成 / 编排收敛"

    def run(self, state: PipelineState) -> PipelineState:
        state.pm_iteration += 1
        voc = state.voc_report
        intel = state.market_intel
        if voc is None:
            return state

        top_opps = voc.opportunities[:3]
        white_space = intel.white_space_opportunities if intel else []

        # 首轮：生成两条路径的概念候选；后续轮：在 chosen 上修订
        if state.chosen_concept is None:
            voc_concept = self._voc_driven(state, top_opps)
            tech_concept = self._tech_native(state, top_opps)
            state.concepts = [voc_concept, tech_concept]
            # 选择：优先覆盖最高机会 + 含技术原生差异点的融合概念
            state.chosen_concept = self._fuse(state, voc_concept, tech_concept, white_space)
        else:
            state.chosen_concept = self._revise(state, state.chosen_concept)

        c = state.chosen_concept
        for d in c.differentiators:
            state.add_claim(f"差异点：{d.statement}", d.evidence_ids)

        if self.tracer:
            self.tracer.emit(
                self.name, "result",
                iteration=state.pm_iteration,
                concept=c.name,
                features=len(c.key_features),
            )
        return state

    def _voc_driven(self, state: PipelineState, opps) -> ProductConcept:
        feats = [f"针对「{o.aspect}」的体验改进" for o in opps]
        diffs = [
            Differentiator(statement=f"以数据验证的方式解决「{o.aspect}」", evidence_ids=o.evidence_ids)
            for o in opps
        ]
        return ProductConcept(
            id="C-VOC",
            name="soundcore（VOC 驱动概念）",
            category=state.category,
            path="voc_driven",
            one_liner="把用户反复抱怨却没被解决的痛点，一次性做到位。",
            target_segment="对音频体验敏感的高频通勤/通话用户",
            value_proposition="基于真实评论统计，集中解决机会分最高的 2–3 个痛点。",
            key_features=feats,
            differentiators=diffs,
            tech_enablers=[TECH_ENABLERS[0]],
            addressed_opportunity_ids=[o.id for o in opps],
        )

    def _tech_native(self, state: PipelineState, opps) -> ProductConcept:
        trend_names = [t.name for t in (state.market_intel.trends if state.market_intel else [])]
        return ProductConcept(
            id="C-TECH",
            name="soundcore（技术原生概念）",
            category=state.category,
            path="tech_native",
            one_liner="用端侧 AI 创造过去做不到的新体验。",
            target_segment="尝鲜的科技爱好者 + 有听力个性化需求的用户",
            value_proposition="把云端能力下沉到耳机本体：实时、私密、个性化。",
            key_features=[f"端侧 AI：{t}" for t in trend_names[:3]],
            differentiators=[
                Differentiator(
                    statement="端侧实时运行降噪/听力个性化，不依赖云、低延迟、保护隐私",
                    evidence_ids=[t.evidence_ids[0] for t in (state.market_intel.trends if state.market_intel else []) if t.evidence_ids][:3],
                )
            ],
            tech_enablers=TECH_ENABLERS,
            addressed_opportunity_ids=[o.id for o in opps[:1]],
        )

    def _fuse(self, state, voc_c: ProductConcept, tech_c: ProductConcept, white_space) -> ProductConcept:
        diffs = voc_c.differentiators + tech_c.differentiators
        for ws in white_space[:2]:
            diffs.append(Differentiator(statement=f"补齐竞品空白：{ws.aspect}", evidence_ids=ws.evidence_ids))
        feats = self.dedup(voc_c.key_features + tech_c.key_features)
        return ProductConcept(
            id="C-FUSED",
            name="soundcore Liberty AI（融合概念）",
            category=state.category,
            path="voc_driven",
            one_liner="既解决真实痛点，又用端侧 AI 拉开代差。",
            target_segment=voc_c.target_segment,
            value_proposition="VOC 验证的确定性改进 + 技术原生的差异化体验，双轮驱动。",
            key_features=feats,
            differentiators=diffs,
            tech_enablers=TECH_ENABLERS,
            addressed_opportunity_ids=self.dedup(
                voc_c.addressed_opportunity_ids + tech_c.addressed_opportunity_ids
                + [ws.id for ws in white_space[:2]]
            ),
        )

    def _revise(self, state: PipelineState, concept: ProductConcept) -> ProductConcept:
        must_fixes: List[str] = self.dedup(
            [mf for itv in state.interviews for mf in itv.must_fixes]
        )
        risks = [r.description for r in (state.feasibility.risks if state.feasibility else [])]
        added = [f"按用户反馈补强：{mf}" for mf in must_fixes[:2]]
        added += [f"针对风险做收敛：{r}" for r in risks[:1]]
        concept.key_features = self.dedup(concept.key_features + added)
        concept.one_liner += "（已根据合成用户与可行性反馈迭代）"
        return concept
