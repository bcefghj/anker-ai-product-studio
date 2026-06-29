"""超级智囊 Agent（AI 原生 AMI）：竞品拆解 + 趋势洞察。"""
from __future__ import annotations

from anker_studio.application.agents.base import Agent
from anker_studio.application.graph.state import PipelineState
from anker_studio.application.platforms.ami import build_market_intel
from anker_studio.infrastructure.data.connectors import fetch_trends
from anker_studio.infrastructure.nlp.lexicons import ASPECT_LEXICON


def _aspect_query(aspect: str) -> str:
    """把中文 aspect 名映射为英文检索词（语料为英文评论）。"""
    kws = [k for k in ASPECT_LEXICON.get(aspect, []) if k.isascii()]
    return " ".join(kws[:4]) or aspect


class SuperThinkTankAgent(Agent):
    name = "超级智囊"
    role = "行业研究 / 竞品分析 / 趋势洞察"

    def run(self, state: PipelineState) -> PipelineState:
        trends, trend_ev = fetch_trends(
            keywords=["earbuds anc", "on-device ai audio", "hearing personalization"]
        )
        state.trend_evidences.extend(trend_ev)

        intel = build_market_intel(state.competitor_evidences, trends)

        # Agentic RAG：为每个白空间机会检索补充证据（可溯源），并累计检索迭代数
        if self.rag is not None:
            for opp in intel.white_space_opportunities:
                evs, meta = self.rag.agentic_search(_aspect_query(opp.aspect), top_k=5, min_hits=2)
                state.retrieval_iters += int(meta.get("iterations", 1))
                extra_ids = [e.source_id for e in evs][:3]
                opp.evidence_ids = self.dedup(list(opp.evidence_ids) + extra_ids)

        state.market_intel = intel

        # 记录可溯源论断（供评测）
        for f in intel.competitors:
            for w in f.weaknesses:
                state.add_claim(f"{f.brand} 的短板：{w}", f.evidence_ids)
        for opp in intel.white_space_opportunities:
            state.add_claim(opp.statement, opp.evidence_ids)
        for t in trends:
            state.add_claim(f"趋势：{t.name} — {t.summary}", t.evidence_ids)

        if self.tracer:
            self.tracer.emit(
                self.name,
                "result",
                competitors=len(intel.competitors),
                white_space=len(intel.white_space_opportunities),
                trends=len(trends),
            )
        return state
