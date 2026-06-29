"""AI 原生 BEES（Application 层）：体验评估 + NPS 预测。

对标安克 BEES（Best Experience Enhancement System）：
- 按时间切片观察 aspect 负面率演化（体验是变好还是退步）。
- 综合目标品牌满意度 + 合成用户接受度，预测 NPS（核心指标）。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from anker_studio.common.models import (
    Evidence,
    ExperiencePoint,
    NPSPrediction,
    PersonaInterview,
    VocReport,
)
from anker_studio.infrastructure.nlp.absa import analyze


def _period_of(date: Optional[str]) -> str:
    if not date:
        return "unknown"
    s = str(date)
    # 兼容 "2021-...", 时间戳毫秒等
    if len(s) >= 4 and s[:4].isdigit():
        return s[:4]
    try:
        import datetime as _dt

        ts = int(s)
        if ts > 10_000_000_000:
            ts //= 1000
        return _dt.datetime.utcfromtimestamp(ts).strftime("%Y")
    except (ValueError, OverflowError, OSError):
        return "unknown"


def experience_trend(evidences: List[Evidence], focus_aspects: List[str]) -> List[ExperiencePoint]:
    by_period: Dict[str, List[Evidence]] = defaultdict(list)
    for ev in evidences:
        by_period[_period_of(ev.date)].append(ev)

    points: List[ExperiencePoint] = []
    for period in sorted(by_period):
        if period == "unknown":
            continue
        stats = analyze(by_period[period])
        for aspect in focus_aspects:
            st = stats.get(aspect)
            if st and st.mentions > 0:
                points.append(
                    ExperiencePoint(
                        aspect=aspect,
                        period=period,
                        mention_count=st.mentions,
                        negative_rate=st.negative_rate,
                        evidence_ids=st.negative_evidence_ids[:2],
                    )
                )
    return points


def predict_nps(
    voc: VocReport,
    interviews: List[PersonaInterview],
    concept_addresses: List[str],
) -> NPSPrediction:
    """简化但可解释的 NPS 预测：

    base 来自目标品牌当前满意度；提案若命中高机会痛点则加分；
    合成用户接受度作为修正项。
    """
    # 当前满意度（加权平均，权重为 reach）
    weighted, wsum = 0.0, 0.0
    for a in voc.aspects:
        weighted += a.satisfaction * max(a.reach, 0.001)
        wsum += max(a.reach, 0.001)
    base_sat = (weighted / wsum) if wsum else 5.0  # 0-10

    # 命中高机会痛点的覆盖加成
    high_opps = {o.aspect for o in voc.opportunities[:5]}
    hit = len([a for a in concept_addresses if a in high_opps])
    coverage_bonus = min(hit, 3) * 6.0  # 每命中一个 +6 分 NPS

    # 合成用户接受度
    if interviews:
        acceptance = sum(i.acceptance for i in interviews) / len(interviews)
    else:
        acceptance = 0.5

    # 映射到 NPS：满意度->基线，acceptance 修正
    base_nps = (base_sat - 7.0) * 20.0  # sat 7 -> 0, sat 9 -> +40, sat 5 -> -40
    accept_adj = (acceptance - 0.5) * 60.0
    score = max(-100.0, min(100.0, base_nps + coverage_bonus + accept_adj))

    promoters = max(0.0, min(100.0, 50 + score / 2))
    detractors = max(0.0, min(100.0, 50 - score / 2))
    passives = max(0.0, 100 - promoters - detractors)

    ev_ids = [eid for o in voc.opportunities[:3] for eid in o.evidence_ids][:4]
    return NPSPrediction(
        score=round(score, 1),
        promoters=round(promoters, 1),
        passives=round(passives, 1),
        detractors=round(detractors, 1),
        rationale=(
            f"当前满意度基线 {base_sat:.1f}/10；提案命中 {hit} 个高机会痛点（+{coverage_bonus:.0f}）；"
            f"合成用户平均接受度 {acceptance:.0%}。"
        ),
        evidence_ids=ev_ids,
    )
