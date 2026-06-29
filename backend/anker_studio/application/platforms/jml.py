"""AI 原生 JML（Application 层）：用户洞察平台。

对标安克 JML（Joint Maker Lab）：把真实用户评论转化为可溯源的痛点与机会。
确定性 ABSA → ODI 机会评分 → 机会解决方案树。
"""
from __future__ import annotations

from typing import List

from anker_studio.common.models import Evidence, VocReport
from anker_studio.application.methodology.odi import aspect_to_insight, insights_to_opportunities
from anker_studio.application.methodology.ost import build_ost
from anker_studio.infrastructure.nlp.absa import analyze


def build_voc_report(category: str, target_brand: str, evidences: List[Evidence]) -> VocReport:
    total = len(evidences)
    stats = analyze(evidences)
    insights = [aspect_to_insight(s, total) for s in stats.values() if s.mentions > 0]
    insights.sort(key=lambda a: a.opportunity_score, reverse=True)
    opportunities = insights_to_opportunities(insights)
    ost = build_ost(
        outcome=f"提升 {target_brand} {category} 品类的 NPS 与复购",
        opportunities=opportunities,
    )
    return VocReport(
        category=category,
        target_brand=target_brand,
        review_count=total,
        aspects=insights,
        opportunities=opportunities,
        ost=ost,
    )
