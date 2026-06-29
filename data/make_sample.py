#!/usr/bin/env python3
"""生成可复现的样本评论数据集（soundcore + 竞品）。

样本是"合成但贴近真实"的英文评论，用于在没有下载 Amazon Reviews 2023 时也能
端到端跑通、并让 ABSA 产出有意义的差异。真实运行请用
`python -m anker_studio.infrastructure.data.amazon_reviews` 下载真实数据。
"""
from __future__ import annotations

import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "sample"
OUT.mkdir(parents=True, exist_ok=True)

YEARS = ["2021", "2022", "2023", "2024", "2025"]

# 每个 aspect 的正/负面句子模板（英文，贴合真实 Amazon 评论与词典）
PHRASES = {
    "anc": {
        "pos": ["The noise cancelling is excellent and blocks out the subway completely.",
                "ANC is amazing, great for flights."],
        "neg": ["The noise cancellation is weak and barely blocks any noise.",
                "ANC is disappointing compared to what they advertise."],
    },
    "sound": {
        "pos": ["Sound quality is great, the bass is clear and punchy.",
                "Amazing audio quality, the soundstage is impressive."],
        "neg": ["The sound is muffled and the bass is weak.",
                "Audio quality is poor and treble sounds harsh."],
    },
    "fit": {
        "pos": ["Very comfortable fit, I can wear them for hours.",
                "The ear tips are comfortable and they never fall out."],
        "neg": ["Uncomfortable fit, they hurt my ears after an hour.",
                "They keep falling out of my ears during workouts."],
    },
    "call": {
        "pos": ["Call quality is clear and the mic picks up my voice well.",
                "People say my voice is crisp on calls."],
        "neg": ["Call quality is terrible, callers say I sound muffled in wind.",
                "The microphone is poor on calls, lots of background noise."],
    },
    "battery": {
        "pos": ["Battery life is great, easily lasts all day.",
                "Impressive playtime, I charge them once a week."],
        "neg": ["Battery life is disappointing and drains fast.",
                "The battery degraded quickly after a few months."],
    },
    "app": {
        "pos": ["The app is good and the EQ is easy to use.",
                "Firmware updates through the app are smooth."],
        "neg": ["The app is buggy and the EQ settings keep resetting.",
                "Firmware update bricked the connection, the app is awful."],
    },
    "connect": {
        "pos": ["Bluetooth connection is stable and pairing is fast.",
                "Multipoint works great switching between phone and laptop."],
        "neg": ["The connection keeps dropping and multipoint switching fails.",
                "Bluetooth pairing is unreliable and there is annoying latency."],
    },
    "price": {
        "pos": ["Great value for the money, worth every penny.",
                "Cheap compared to the big brands and works well."],
        "neg": ["Way too expensive for what you get.",
                "Not worth the price, overpriced for the features."],
    },
    "durable": {
        "pos": ["Solid build quality, feels durable.",
                "Well built, no issues after a year."],
        "neg": ["One earbud stopped working after two months, poor quality control.",
                "The hinge broke quickly, bad build quality."],
    },
}

# 各品牌在各 aspect 上的"负面概率"（刻画差异，贴近公开认知，仅用于样本）
BRAND_NEG = {
    "soundcore": {"anc": 0.35, "sound": 0.25, "fit": 0.3, "call": 0.6, "battery": 0.3,
                  "app": 0.55, "connect": 0.6, "price": 0.15, "durable": 0.4},
    "Bose":      {"anc": 0.1, "sound": 0.2, "fit": 0.25, "call": 0.4, "battery": 0.45,
                  "app": 0.4, "connect": 0.45, "price": 0.7, "durable": 0.35},
    "Sony":      {"anc": 0.15, "sound": 0.15, "fit": 0.35, "call": 0.5, "battery": 0.3,
                  "app": 0.55, "connect": 0.4, "price": 0.55, "durable": 0.3},
    "Samsung":   {"anc": 0.5, "sound": 0.35, "fit": 0.3, "call": 0.45, "battery": 0.35,
                  "app": 0.4, "connect": 0.35, "price": 0.4, "durable": 0.4},
    "Apple":     {"anc": 0.25, "sound": 0.25, "fit": 0.55, "call": 0.3, "battery": 0.4,
                  "app": 0.2, "connect": 0.2, "price": 0.75, "durable": 0.35},
}
PRODUCTS = {
    "soundcore": "soundcore Liberty 4 NC", "Bose": "Bose QuietComfort Ultra Earbuds",
    "Sony": "Sony WF-1000XM5", "Samsung": "Samsung Galaxy Buds3 Pro", "Apple": "Apple AirPods Pro 2",
}


def gen_brand(brand: str, n: int, rng: random.Random):
    rows = []
    aspects = list(PHRASES.keys())
    for i in range(n):
        k = rng.choice([1, 2, 2, 3])
        chosen = rng.sample(aspects, k)
        texts, neg_any = [], False
        for asp in chosen:
            is_neg = rng.random() < BRAND_NEG[brand][asp]
            neg_any = neg_any or is_neg
            texts.append(rng.choice(PHRASES[asp]["neg" if is_neg else "pos"]))
        rating = rng.choice([1, 2, 3]) if neg_any else rng.choice([4, 5, 5])
        rows.append({
            "source_id": f"{brand}-{i:04d}",
            "brand": brand,
            "product": PRODUCTS[brand],
            "rating": rating,
            "text": " ".join(texts),
            "date": rng.choice(YEARS),
            "helpful_votes": rng.randint(0, 40),
        })
    return rows


def main() -> None:
    rng = random.Random(42)
    counts = {"soundcore": 120, "Bose": 70, "Sony": 70, "Samsung": 60, "Apple": 70}
    for brand, n in counts.items():
        rows = gen_brand(brand, n, rng)
        path = OUT / f"{brand}.jsonl"
        with path.open("w", encoding="utf-8") as fp:
            for r in rows:
                fp.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"wrote {len(rows)} -> {path}")


if __name__ == "__main__":
    main()
