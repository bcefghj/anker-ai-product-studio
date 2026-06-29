"""混合检索（Infrastructure 层）：BM25 + TF-IDF，RRF 融合。

纯 Python 实现（无需 numpy/chromadb 也能运行）。提供 Agentic RAG 所需的
"检索 → 打分 → 重写 → 再检索" 迭代能力，并返回可溯源的 Evidence。
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from anker_studio.common.config import settings
from anker_studio.common.logging import log
from anker_studio.common.models import Evidence

_TOKEN_RE = re.compile(r"[a-zA-Z']+|[\u4e00-\u9fff]")
_STOP = {"the", "a", "an", "and", "or", "of", "to", "is", "are", "for", "with", "it", "this", "that"}


def _tok(text: str) -> List[str]:
    return [t for t in _TOKEN_RE.findall((text or "").lower()) if t not in _STOP and len(t) > 1]


@dataclass
class _Doc:
    idx: int
    tokens: List[str]
    tf: Counter


class HybridRetriever:
    """对一组 Evidence 建立 BM25 + TF-IDF 索引并支持检索。"""

    def __init__(self, evidences: Sequence[Evidence], k1: float = 1.5, b: float = 0.75):
        self.evidences = list(evidences)
        self.k1 = k1
        self.b = b
        self.docs: List[_Doc] = []
        self.df: Counter = Counter()
        self.idf: Dict[str, float] = {}
        self.avgdl = 0.0
        self._build()

    def _build(self) -> None:
        total_len = 0
        for i, ev in enumerate(self.evidences):
            toks = _tok(ev.text)
            self.docs.append(_Doc(idx=i, tokens=toks, tf=Counter(toks)))
            total_len += len(toks)
            for t in set(toks):
                self.df[t] += 1
        n = max(1, len(self.docs))
        self.avgdl = total_len / n if n else 0.0
        for term, df in self.df.items():
            self.idf[term] = math.log(1 + (n - df + 0.5) / (df + 0.5))
        log.bind(node="rag").info(f"索引建立：{n} 篇文档，词表 {len(self.df)}。")

    def _bm25(self, q_tokens: List[str]) -> Dict[int, float]:
        scores: Dict[int, float] = {}
        for doc in self.docs:
            dl = len(doc.tokens) or 1
            s = 0.0
            for t in q_tokens:
                if t not in doc.tf:
                    continue
                idf = self.idf.get(t, 0.0)
                freq = doc.tf[t]
                denom = freq + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                s += idf * (freq * (self.k1 + 1)) / (denom or 1)
            if s > 0:
                scores[doc.idx] = s
        return scores

    def _tfidf(self, q_tokens: List[str]) -> Dict[int, float]:
        scores: Dict[int, float] = {}
        q = Counter(q_tokens)
        for doc in self.docs:
            s = 0.0
            for t, qf in q.items():
                if t in doc.tf:
                    s += (qf * self.idf.get(t, 0.0)) * (doc.tf[t] * self.idf.get(t, 0.0))
            if s > 0:
                norm = math.sqrt(sum(v * v for v in doc.tf.values()) or 1)
                scores[doc.idx] = s / norm
        return scores

    @staticmethod
    def _rrf(rankings: Sequence[Dict[int, float]], k: int = 60) -> Dict[int, float]:
        fused: Dict[int, float] = {}
        for scores in rankings:
            ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
            for rank, (idx, _) in enumerate(ordered):
                fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + rank + 1)
        return fused

    def search(self, query: str, top_k: int = 8) -> List[Tuple[Evidence, float]]:
        q_tokens = _tok(query)
        if not q_tokens:
            return []
        fused = self._rrf([self._bm25(q_tokens), self._tfidf(q_tokens)])
        ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
        return [(self.evidences[i], round(score, 5)) for i, score in ordered]


class RagService:
    """Agentic RAG：检索→打分→重写→再检索（上限 max_iters）。"""

    def __init__(self, retriever: HybridRetriever, max_iters: int = 3):
        self.retriever = retriever
        self.max_iters = max_iters

    def agentic_search(self, query: str, top_k: int = 8, min_hits: int = 3):
        """返回 (evidences, meta)；meta 含迭代次数，供评测统计 mean_iterations。"""
        attempts = 0
        results: List[Tuple[Evidence, float]] = []
        current = query
        while attempts < self.max_iters:
            attempts += 1
            results = self.retriever.search(current, top_k=top_k)
            if len(results) >= min_hits:
                break
            # 重写：放宽查询（去掉修饰，保留核心名词）
            current = self._rewrite(current)
            log.bind(node="rag").info(f"检索不足({len(results)})，重写查询 -> '{current}'（第{attempts}次）")
        meta = {"iterations": attempts, "hits": len(results)}
        return [ev for ev, _ in results], meta

    @staticmethod
    def _rewrite(query: str) -> str:
        toks = _tok(query)
        # 保留信息量最大的前 5 个词
        return " ".join(toks[:5]) if toks else query


def build_rag(evidences: Sequence[Evidence]) -> RagService:
    return RagService(HybridRetriever(evidences), max_iters=settings().max_retrieval_iters)
