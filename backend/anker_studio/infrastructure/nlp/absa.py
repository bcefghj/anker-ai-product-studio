"""确定性 Aspect-Based Sentiment Analysis（Infrastructure 层）。

输入一批 Evidence（评论），按 aspect 统计提及量、负面率、代表性引用。
情感判定：子句级关键词 + 否定翻转 + 评分(rating)兜底。
全程不调用 LLM，保证可复现、可溯源。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Sequence

from anker_studio.common.models import Evidence
from anker_studio.infrastructure.nlp.lexicons import (
    ASPECT_LEXICON,
    NEGATIVE_WORDS,
    NEGATORS,
    POSITIVE_WORDS,
)

_CLAUSE_SPLIT = re.compile(r"[.!?;,\n。！？；，]")


@dataclass
class AspectStat:
    aspect: str
    mentions: int = 0
    negative: int = 0
    positive: int = 0
    evidence_ids: List[str] = field(default_factory=list)
    negative_evidence_ids: List[str] = field(default_factory=list)

    @property
    def negative_rate(self) -> float:
        return round(self.negative / self.mentions, 4) if self.mentions else 0.0

    @property
    def positive_rate(self) -> float:
        return round(self.positive / self.mentions, 4) if self.mentions else 0.0


def _clause_sentiment(clause: str, rating) -> str:
    """返回 'pos' | 'neg' | 'neu'。"""
    words = re.findall(r"[a-zA-Z']+|[\u4e00-\u9fff]", clause.lower())
    score = 0
    for i, w in enumerate(words):
        polarity = 0
        if w in POSITIVE_WORDS:
            polarity = 1
        elif w in NEGATIVE_WORDS:
            polarity = -1
        if polarity != 0:
            window = words[max(0, i - 3): i]
            if any(neg in window or w.endswith("n't") for neg in NEGATORS):
                polarity = -polarity
            score += polarity
    if score > 0:
        return "pos"
    if score < 0:
        return "neg"
    # 中性子句用整体评分兜底
    if rating is not None:
        try:
            r = float(rating)
            if r <= 2:
                return "neg"
            if r >= 4:
                return "pos"
        except (TypeError, ValueError):
            return "neu"
    return "neu"


def _match_aspects(clause: str) -> List[str]:
    c = clause.lower()
    hit = []
    for aspect, kws in ASPECT_LEXICON.items():
        if any(kw in c for kw in kws):
            hit.append(aspect)
    return hit


def analyze(evidences: Sequence[Evidence]) -> Dict[str, AspectStat]:
    """对评论做 ABSA，返回 {aspect: AspectStat}。"""
    stats: Dict[str, AspectStat] = {a: AspectStat(aspect=a) for a in ASPECT_LEXICON}
    for ev in evidences:
        seen_aspects_this_review: Dict[str, str] = {}
        for clause in _CLAUSE_SPLIT.split(ev.text):
            clause = clause.strip()
            if len(clause) < 3:
                continue
            for aspect in _match_aspects(clause):
                sent = _clause_sentiment(clause, ev.rating)
                # 每条评论对同一 aspect 取"最负面"的判定，避免重复计数夸大
                prev = seen_aspects_this_review.get(aspect)
                if prev is None or (sent == "neg" and prev != "neg"):
                    seen_aspects_this_review[aspect] = sent
        for aspect, sent in seen_aspects_this_review.items():
            st = stats[aspect]
            st.mentions += 1
            if ev.source_id not in st.evidence_ids:
                st.evidence_ids.append(ev.source_id)
            if sent == "neg":
                st.negative += 1
                st.negative_evidence_ids.append(ev.source_id)
            elif sent == "pos":
                st.positive += 1
    return stats
