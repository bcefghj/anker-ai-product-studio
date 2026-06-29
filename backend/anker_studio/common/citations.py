"""引用校验（Common 层）—— 本项目反幻觉的命门。

提供两类确定性校验（不依赖 LLM 自证）：
1. verify_quote：引用的片段必须在某条 Evidence 文本中逐字出现。
2. claim_supported：论断与其引用的 Evidence 必须有足够的词面重叠。
并据此计算 groundedness / faithfulness / citation_hit_rate。
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Sequence, Tuple

from anker_studio.common.models import Evidence

_WORD_RE = re.compile(r"[a-zA-Z]+|[\u4e00-\u9fff]")
_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "is", "are", "for", "with",
    "this", "that", "it", "in", "on", "i", "you", "my", "very", "too", "but",
    "了", "的", "是", "和", "也", "在", "我", "你", "它", "很", "太",
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _tokens(text: str) -> List[str]:
    return [t for t in _WORD_RE.findall((text or "").lower()) if t not in _STOP]


def build_index(evidences: Sequence[Evidence]) -> Dict[str, Evidence]:
    return {e.source_id: e for e in evidences}


def verify_quote(quote: str, evidence_text: str) -> bool:
    """引用片段是否在 evidence 文本中逐字（忽略空白/大小写）出现。"""
    q = _norm(quote)
    if not q:
        return False
    return q in _norm(evidence_text)


def claim_supported(
    claim: str,
    evidence_ids: Sequence[str],
    index: Dict[str, Evidence],
    min_overlap: int = 2,
    aspect_terms: "Dict[str, Sequence[str]] | None" = None,
) -> bool:
    """论断是否被其引用的 Evidence 支撑。

    两条通路（任一成立即支撑）：
    1. 词面重叠 >= min_overlap（同语言）。
    2. 跨语言 aspect 桥接：claim 提到某 aspect（中文名），且 evidence 文本含该 aspect 的
       任一关键词（英文）。解决"中文论断 + 英文评论"的对齐问题。
    """
    ids = [i for i in evidence_ids if i in index]
    if not ids:
        return False

    # 通路 2：aspect 桥接
    if aspect_terms:
        claim_low = (claim or "").lower()
        for aspect, terms in aspect_terms.items():
            if aspect in claim or aspect.lower() in claim_low:
                for sid in ids:
                    ev_low = index[sid].text.lower()
                    if any(str(t).lower() in ev_low for t in terms):
                        return True

    # 通路 1：词面重叠
    claim_tokens = set(_tokens(claim))
    if not claim_tokens:
        return bool(ids)
    for sid in ids:
        ev_tokens = set(_tokens(index[sid].text))
        if len(claim_tokens & ev_tokens) >= min_overlap:
            return True
    return False


def evaluate_citations(
    claims: Iterable[Tuple[str, Sequence[str]]],
    evidences: Sequence[Evidence],
    aspect_terms: "Dict[str, Sequence[str]] | None" = None,
) -> Dict[str, float]:
    """对 (claim, evidence_ids) 列表统计 groundedness / faithfulness / hit_rate。

    - groundedness：带 >=1 个有效引用的论断比例。
    - faithfulness：引用确实支撑论断的比例（词面重叠）。
    - citation_hit_rate：引用的 evidence_id 真实存在的比例。
    """
    index = build_index(evidences)
    claims = list(claims)
    total = len(claims)
    if total == 0:
        return {"groundedness": 0.0, "faithfulness": 0.0, "citation_hit_rate": 0.0}

    grounded = 0
    faithful = 0
    total_refs = 0
    valid_refs = 0
    for claim, ids in claims:
        ids = list(ids or [])
        valid = [i for i in ids if i in index]
        total_refs += len(ids)
        valid_refs += len(valid)
        if valid:
            grounded += 1
            if claim_supported(claim, valid, index, aspect_terms=aspect_terms):
                faithful += 1

    return {
        "groundedness": round(grounded / total, 4),
        "faithfulness": round(faithful / total, 4),
        "citation_hit_rate": round((valid_refs / total_refs) if total_refs else 0.0, 4),
    }
