"""AI 原生 AMI（Application 层）：市场/竞品洞察平台（超级智囊底座）。

对标安克 AMI（Anker Market Insights）：对每个竞品做 ABSA，推导其优势/短板，
短板即"白空间机会"；叠加行业趋势信号，产出 MarketIntel。
"""
from __future__ import annotations

from typing import Dict, List

from anker_studio.common.models import (
    CompetitorFinding,
    Evidence,
    MarketIntel,
    Opportunity,
    TrendSignal,
)
from anker_studio.application.methodology.odi import aspect_to_insight
from anker_studio.infrastructure.nlp.absa import analyze


def _competitor_finding(brand: str, evidences: List[Evidence]) -> CompetitorFinding:
    total = len(evidences)
    stats = analyze(evidences)
    insights = [aspect_to_insight(s, total) for s in stats.values() if s.mentions > 0]
    strengths, weaknesses, white_space, ev_ids = [], [], [], []
    for ins in sorted(insights, key=lambda a: a.reach, reverse=True):
        if ins.negative_rate >= 0.45 and ins.reach >= 0.05:
            weaknesses.append(f"{ins.aspect}（负面率 {ins.negative_rate:.0%}）")
            white_space.append(ins.aspect)
            ev_ids.extend(ins.representative_evidence_ids)
        elif ins.satisfaction >= 6.0 and ins.reach >= 0.08:
            strengths.append(f"{ins.aspect}（满意度 {ins.satisfaction}/10）")
    return CompetitorFinding(
        brand=brand,
        review_count=total,
        strengths=strengths[:4],
        weaknesses=weaknesses[:4],
        white_space=white_space[:4],
        evidence_ids=ev_ids[:6],
    )


def build_market_intel(
    competitor_evidences: Dict[str, List[Evidence]],
    trends: List[TrendSignal],
) -> MarketIntel:
    findings: List[CompetitorFinding] = []
    for brand, evs in competitor_evidences.items():
        if evs:
            findings.append(_competitor_finding(brand, evs))

    # 白空间机会：多个竞品共同的短板 = 强机会
    aspect_gap: Dict[str, List[str]] = {}
    for f in findings:
        for ws in f.white_space:
            aspect_gap.setdefault(ws, []).extend(f.evidence_ids)

    white_space_opps: List[Opportunity] = []
    for i, (aspect, ev_ids) in enumerate(
        sorted(aspect_gap.items(), key=lambda kv: len(kv[1]), reverse=True)
    ):
        white_space_opps.append(
            Opportunity(
                id=f"WS-{i+1}",
                statement=f"竞品在「{aspect}」上普遍未满足，存在差异化空白",
                aspect=aspect,
                origin="competitor",
                opportunity_score=round(6.0 + len(ev_ids) * 0.3, 2),
                evidence_ids=ev_ids[:4],
                rationale=f"{len([f for f in findings if aspect in f.white_space])} 个竞品在此 aspect 上负面突出。",
            )
        )
    return MarketIntel(competitors=findings, trends=trends, white_space_opportunities=white_space_opps)
