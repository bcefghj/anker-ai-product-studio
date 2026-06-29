"""Amazon Reviews 2023 (McAuley-Lab) 下载与品牌筛选（Infrastructure 层）。

把真实评论按品牌（soundcore / Bose / Sony / Samsung / Apple）筛出，落地为
`data/processed/<brand>.jsonl`，供 loader 读取。需要可选依赖 `datasets`。

用法：
    python -m anker_studio.infrastructure.data.amazon_reviews --max-per-brand 800
未安装 datasets 时给出清晰提示，不影响系统以样本数据运行。
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List

from anker_studio.common.config import settings
from anker_studio.common.logging import log

# 品牌 -> 在 store/title 中的匹配正则
BRAND_PATTERNS: Dict[str, str] = {
    "soundcore": r"soundcore|anker",
    "Bose": r"\bbose\b",
    "Sony": r"\bsony\b",
    "Samsung": r"samsung|galaxy buds",
    "Apple": r"\bapple\b|airpods",
}
# 仅保留音频耳机相关产品
AUDIO_HINT = re.compile(r"earbud|headphone|earphone|tws|wireless ear|anc|noise cancel", re.I)


def _match_brand(text: str) -> str:
    t = (text or "").lower()
    for brand, pat in BRAND_PATTERNS.items():
        if re.search(pat, t):
            return brand
    return ""


def download_and_filter(max_per_brand: int = 800) -> None:
    try:
        from datasets import load_dataset  # type: ignore
    except Exception:  # noqa: BLE001
        log.bind(node="data").error(
            "未安装 datasets。请 `pip install datasets` 后重试；"
            "或直接使用随仓库的 data/sample 样本运行。"
        )
        return

    out_dir = Path(settings().data_dir) / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)

    log.bind(node="data").info("加载 raw_meta_Electronics（流式）以建立 asin->品牌 映射……")
    meta = load_dataset(
        "McAuley-Lab/Amazon-Reviews-2023",
        "raw_meta_Electronics",
        split="full",
        streaming=True,
        trust_remote_code=True,
    )
    asin_brand: Dict[str, str] = {}
    for i, m in enumerate(meta):
        title = str(m.get("title") or "")
        store = str(m.get("store") or "")
        if not AUDIO_HINT.search(title):
            continue
        brand = _match_brand(store) or _match_brand(title)
        if brand:
            asin_brand[str(m.get("parent_asin") or m.get("asin"))] = brand
        if i > 400000 or len(asin_brand) > 20000:
            break
    log.bind(node="data").info(f"建立映射 {len(asin_brand)} 个音频商品。")

    log.bind(node="data").info("加载 raw_review_Electronics（流式）并按品牌筛选……")
    reviews = load_dataset(
        "McAuley-Lab/Amazon-Reviews-2023",
        "raw_review_Electronics",
        split="full",
        streaming=True,
        trust_remote_code=True,
    )
    buckets: Dict[str, List[dict]] = {b: [] for b in BRAND_PATTERNS}
    for r in reviews:
        asin = str(r.get("parent_asin") or r.get("asin"))
        brand = asin_brand.get(asin)
        if not brand or len(buckets[brand]) >= max_per_brand:
            continue
        text = str(r.get("text") or "")
        if len(text) < 40:
            continue
        buckets[brand].append(
            {
                "source_id": f"{brand}-{asin}-{r.get('user_id','')[:6]}-{len(buckets[brand])}",
                "brand": brand,
                "product": str(r.get("title") or ""),
                "rating": r.get("rating"),
                "text": text,
                "date": r.get("timestamp"),
                "helpful_votes": r.get("helpful_vote") or 0,
            }
        )
        if all(len(v) >= max_per_brand for v in buckets.values()):
            break

    for brand, rows in buckets.items():
        path = out_dir / f"{brand}.jsonl"
        with path.open("w", encoding="utf-8") as fp:
            for row in rows:
                fp.write(json.dumps(row, ensure_ascii=False) + "\n")
        log.bind(node="data").info(f"写出 {len(rows)} 条 -> {path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-per-brand", type=int, default=800)
    args = ap.parse_args()
    download_and_filter(args.max_per_brand)


if __name__ == "__main__":
    main()
