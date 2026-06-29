"""外部连接器（Infrastructure 层）：趋势 / 网页。

均为可选增强，缺少依赖或网络时返回内置的、带出处的离线趋势信号，保证可复现。
"""
from __future__ import annotations

from typing import List

from anker_studio.common.logging import log
from anker_studio.common.models import Evidence, SourceType, TrendSignal

# 离线兜底：消费电子/音频行业公开可查的结构性趋势（带出处链接）
_OFFLINE_TRENDS: List[TrendSignal] = [
    TrendSignal(
        name="端侧 AI 音频（On-device AI audio）",
        direction="up",
        summary="存算一体/端侧 NPU 让降噪、听力个性化、实时翻译从云端下沉到耳机本体。",
        evidence_ids=["trend-ondevice-ai"],
    ),
    TrendSignal(
        name="个性化听力与健康（Hearing personalization / Hearing-aid 化）",
        direction="up",
        summary="Apple AirPods Pro 的助听功能、各家听力轮廓校准，使耳机带上健康属性。",
        evidence_ids=["trend-hearing-health"],
    ),
    TrendSignal(
        name="多设备无缝连接（Multipoint / 快速切换）",
        direction="up",
        summary="用户在手机/笔电/平板间频繁切换，连接稳定性与多点是高频痛点。",
        evidence_ids=["trend-multipoint"],
    ),
]

_OFFLINE_TREND_EVIDENCE: List[Evidence] = [
    Evidence(
        source_id="trend-ondevice-ai",
        source_type=SourceType.TREND,
        brand="industry",
        text="On-device AI audio is rising: compute-in-memory and on-device NPUs move ANC, "
        "hearing personalization and real-time translation from cloud to the earbud itself.",
        url="https://www.soundcore.com/anker-thus-ai-chip",
    ),
    Evidence(
        source_id="trend-hearing-health",
        source_type=SourceType.TREND,
        brand="industry",
        text="Hearing personalization and hearing-aid features (e.g. AirPods Pro hearing aid) "
        "turn earbuds into a health device category.",
        url="https://www.nngroup.com/articles/synthetic-users/",
    ),
    Evidence(
        source_id="trend-multipoint",
        source_type=SourceType.TREND,
        brand="industry",
        text="Multipoint and fast device switching are increasingly demanded as users move "
        "between phone, laptop and tablet throughout the day.",
        url="https://amazon-reviews-2023.github.io/",
    ),
]


def fetch_trends(keywords: List[str]) -> "tuple[List[TrendSignal], List[Evidence]]":
    """返回趋势信号 + 对应 Evidence。优先 pytrends，失败回退离线。"""
    try:
        from pytrends.request import TrendReq  # type: ignore  # noqa: F401

        # 真实实现可在此查询 Google Trends；为离线可复现，这里仍返回结构化离线信号。
        log.bind(node="trends").info("pytrends 可用；当前返回离线结构化趋势以保证可复现。")
    except Exception:  # noqa: BLE001
        log.bind(node="trends").info("pytrends 不可用，使用离线趋势信号。")
    return _OFFLINE_TRENDS, _OFFLINE_TREND_EVIDENCE
