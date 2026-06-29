"""用户替身 Agent（合成用户面板）。

把真实评论按"主诉 aspect"聚成细分人群，构建 OCEAN 画像的合成用户，
对当前概念做"假设盲"访谈（不告知研究目标，避免谄媚），输出接受度/异议/必须改进项。
依据：SCOPE 社会心理画像、Grounded Simulation 假设盲、Synthetic Users 多人格。
"""
from __future__ import annotations

import hashlib
from typing import List

from anker_studio.application.agents.base import Agent
from anker_studio.application.graph.state import PipelineState
from anker_studio.common.models import (
    InterviewTurn,
    Persona,
    PersonaInterview,
    ProductConcept,
)

_OCEAN = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]


def _ocean_from(seed: str) -> dict:
    h = hashlib.sha256(seed.encode("utf-8")).digest()
    return {dim: round((h[i] % 100) / 100.0, 2) for i, dim in enumerate(_OCEAN)}


class UserProxyAgent(Agent):
    name = "用户替身"
    role = "合成用户访谈 / 痛点验证"

    def run(self, state: PipelineState) -> PipelineState:
        voc = state.voc_report
        concept = state.chosen_concept
        if voc is None or concept is None:
            return state

        state.personas = self._build_personas(state)
        state.interviews = [self._interview(p, concept) for p in state.personas]

        for itv in state.interviews:
            # persona 来自真实评论 grounding -> 记录引用
            persona = next((p for p in state.personas if p.id == itv.persona_id), None)
            if persona:
                state.add_claim(
                    f"{persona.segment} 对概念的判定：{itv.verdict}", persona.derived_from_evidence_ids
                )
        if self.tracer:
            self.tracer.emit(
                self.name, "result",
                personas=len(state.personas),
                avg_acceptance=round(
                    sum(i.acceptance for i in state.interviews) / max(1, len(state.interviews)), 2
                ),
            )
        return state

    def _build_personas(self, state: PipelineState) -> List[Persona]:
        personas: List[Persona] = []
        # 每个高机会痛点对应一个细分人群（grounded 在该 aspect 的真实负面评论）
        for i, opp in enumerate(state.voc_report.opportunities[:4]):
            seed = f"{opp.aspect}-{i}"
            personas.append(
                Persona(
                    id=f"P-{i+1}",
                    name=f"用户{i+1}",
                    segment=f"对「{opp.aspect}」高度敏感的用户",
                    demographics="18-40 岁，全球主流市场，重度耳机使用者",
                    ocean=_ocean_from(seed),
                    behaviors=["每天佩戴 >3 小时", "频繁多设备切换"],
                    pains=[opp.statement],
                    derived_from_evidence_ids=opp.evidence_ids,
                    summary=f"该人群最在意 {opp.aspect}，当前满意度 {opp.satisfaction}/10。",
                )
            )
        return personas

    def _interview(self, persona: Persona, concept: ProductConcept) -> PersonaInterview:
        # 假设盲：仅向 persona 暴露其自身画像 + 概念要点，不暴露"我们想验证什么"
        addressed = set(self._concept_aspects(concept))
        persona_aspect = persona.segment

        # 该 persona 关心的 aspect 是否被概念覆盖
        hit = any(asp in persona_aspect for asp in addressed) or any(
            asp in f for asp in addressed for f in concept.key_features
        )
        covered = [f for f in concept.key_features if any(a in f for a in addressed)]

        turns: List[InterviewTurn] = [
            InterviewTurn(
                question="你平时用耳机，最大的困扰是什么？",
                answer=persona.pains[0] if persona.pains else "整体还行，但偶有小毛病。",
                sentiment="negative",
            ),
            InterviewTurn(
                question=f"这是一款新耳机，主打：{('; '.join(concept.key_features[:3]))}。你的第一反应？",
                answer=(
                    "正好戳中我天天遇到的问题，挺心动。" if hit
                    else "看起来不错，但没解决我最在意的那个点。"
                ),
                sentiment="positive" if hit else "neutral",
            ),
            InterviewTurn(
                question="你愿意为它买单/推荐给朋友吗？",
                answer=("会，如果价格合理。" if hit else "再看看，目前不够打动我。"),
                sentiment="positive" if hit else "negative",
            ),
            InterviewTurn(
                question="还有什么是它必须改进的？",
                answer=("把承诺的体验在真实环境里做稳定。" if hit else f"先把「{persona_aspect}」做好。"),
                sentiment="neutral",
            ),
        ]
        acceptance = 0.8 if hit else 0.35
        verdict = "would_buy" if acceptance >= 0.6 else ("maybe" if acceptance >= 0.45 else "would_not_buy")
        objections = [] if hit else [f"未覆盖我最在意的「{persona_aspect}」"]
        must_fixes = ["真实环境下的稳定性"] if hit else [persona.segment.replace("对「", "").replace("」高度敏感的用户", "")]
        return PersonaInterview(
            persona_id=persona.id,
            persona_name=persona.name,
            segment=persona.segment,
            transcript=turns,
            verdict=verdict,
            objections=objections,
            must_fixes=must_fixes,
            acceptance=acceptance,
        )

    @staticmethod
    def _concept_aspects(concept: ProductConcept) -> List[str]:
        # 从特性文本里粗取 aspect 关键字
        text = " ".join(concept.key_features + [d.statement for d in concept.differentiators])
        aspects = []
        for a in ["降噪 ANC", "音质", "佩戴舒适度", "通话质量", "续航", "App 体验", "连接稳定性/多点", "价格/价值", "耐用性"]:
            if a in text or a.split(" ")[0] in text:
                aspects.append(a)
        return aspects
