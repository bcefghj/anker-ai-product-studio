"""数据加载（Infrastructure 层）。

统一把不同来源的评论加载成 `Evidence`：
- 优先读取 `data/processed/*.jsonl`（由 amazon_reviews 下载脚本生成的真实数据）。
- 否则回退到 `data/sample/*.jsonl`（随仓库提供的可复现样本）。
品牌归类（target / competitor）由 `store`/`brand` 字段决定。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from anker_studio.common.config import settings
from anker_studio.common.logging import log
from anker_studio.common.models import Evidence, SourceType

# soundcore 为目标品牌；其余为竞品（用于 AMI 竞品拆解）
TARGET_BRAND = "soundcore"
COMPETITOR_BRANDS = ["Bose", "Sony", "Samsung", "Apple"]


def _data_root() -> Path:
    return Path(settings().data_dir)


def _read_jsonl(path: Path) -> List[dict]:
    rows: List[dict] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                log.bind(node="data").warning(f"跳过坏行 {path.name}: {exc}")
    return rows


def _row_to_evidence(row: dict) -> Evidence:
    brand = str(row.get("brand") or row.get("store") or "unknown")
    stype = row.get("source_type")
    if stype not in {s.value for s in SourceType}:
        stype = (
            SourceType.REVIEW.value
            if brand.lower() == TARGET_BRAND
            else SourceType.COMPETITOR.value
        )
    return Evidence(
        source_id=str(row.get("source_id") or row.get("id") or row.get("asin") or id(row)),
        source_type=SourceType(stype),
        brand=brand,
        product=str(row.get("product") or row.get("title") or ""),
        rating=row.get("rating"),
        text=str(row.get("text") or row.get("review") or ""),
        date=row.get("date") or row.get("timestamp"),
        url=row.get("url"),
        helpful_votes=int(row.get("helpful_votes") or row.get("helpful_vote") or 0),
    )


def load_evidence(category: str = "audio") -> List[Evidence]:
    """加载该品类的全部 Evidence（真实优先，样本兜底）。"""
    root = _data_root()
    processed = root / "processed"
    sample = root / "sample"

    files: List[Path] = []
    if processed.exists():
        files = sorted(processed.glob("*.jsonl"))
    if not files and sample.exists():
        files = sorted(sample.glob("*.jsonl"))

    evidences: List[Evidence] = []
    for f in files:
        for row in _read_jsonl(f):
            ev = _row_to_evidence(row)
            if ev.text:
                evidences.append(ev)

    src = "processed(真实)" if (processed.exists() and any(processed.glob("*.jsonl"))) else "sample(样本)"
    log.bind(node="data").info(
        f"加载 {len(evidences)} 条 Evidence（来源={src}，category={category}）"
    )
    return evidences


def split_by_brand(evidences: List[Evidence]) -> Dict[str, List[Evidence]]:
    """切分目标品牌 vs 竞品。"""
    target: List[Evidence] = []
    competitors: Dict[str, List[Evidence]] = {b: [] for b in COMPETITOR_BRANDS}
    other: List[Evidence] = []
    for e in evidences:
        if e.brand.lower() == TARGET_BRAND:
            target.append(e)
        elif e.brand in competitors:
            competitors[e.brand].append(e)
        else:
            other.append(e)
    return {"target": target, "competitors": competitors, "other": other}


def filter_evidence(evidences: List[Evidence], brand: Optional[str] = None) -> List[Evidence]:
    if brand is None:
        return evidences
    return [e for e in evidences if e.brand.lower() == brand.lower()]
