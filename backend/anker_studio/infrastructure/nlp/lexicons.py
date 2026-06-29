"""领域词典（Infrastructure 层）。

音频耳机品类的 aspect 词典 + 通用情感词典 + 否定词。
确定性 ABSA 的基础，使 VOC 洞察"有数据支撑且可复现"。
"""
from __future__ import annotations

from typing import Dict, List

# aspect -> 关键词（小写）。中英混合以兼容真实 Amazon 英文评论与中文样本。
ASPECT_LEXICON: Dict[str, List[str]] = {
    "降噪 ANC": [
        "anc", "noise cancel", "noise-cancel", "noise cancelling", "noise canceling",
        "ambient", "transparency", "降噪", "噪音", "通透",
    ],
    "音质": [
        "sound", "audio quality", "bass", "treble", "mids", "soundstage", "音质", "低音", "高音", "声音",
    ],
    "佩戴舒适度": [
        "fit", "comfort", "comfortable", "ear", "tips", "snug", "hurt", "fall out",
        "舒适", "佩戴", "耳朵", "掉", "贴合",
    ],
    "通话质量": [
        "call", "calls", "mic", "microphone", "voice", "wind", "通话", "麦克风", "语音",
    ],
    "续航": [
        "battery", "battery life", "charge", "hours", "playtime", "续航", "电池", "充电", "小时",
    ],
    "App 体验": [
        "app", "eq", "equalizer", "firmware", "update", "应用", "固件", "均衡器",
    ],
    "连接稳定性/多点": [
        "connect", "connection", "bluetooth", "pairing", "multipoint", "switch", "drop", "latency", "lag",
        "连接", "蓝牙", "配对", "多点", "切换", "断连", "延迟",
    ],
    "价格/价值": [
        "price", "expensive", "cheap", "worth", "value", "money", "价格", "贵", "便宜", "值",
    ],
    "耐用性": [
        "durable", "broke", "broken", "stopped working", "quality control", "build", "耐用", "坏", "做工",
    ],
}

POSITIVE_WORDS: List[str] = [
    "great", "good", "excellent", "amazing", "love", "best", "perfect", "comfortable",
    "clear", "impressive", "solid", "worth", "happy", "recommend", "fantastic", "crisp",
    "好", "棒", "优秀", "喜欢", "完美", "清晰", "值", "推荐", "舒适", "稳定",
]
NEGATIVE_WORDS: List[str] = [
    "bad", "poor", "terrible", "awful", "hate", "worst", "disappointing", "disappointed",
    "uncomfortable", "muffled", "weak", "drop", "drops", "broke", "broken", "expensive",
    "fail", "fails", "annoying", "laggy", "lag", "useless", "cheap", "issue", "issues", "problem",
    "差", "糟", "失望", "难受", "弱", "断", "坏", "贵", "卡", "延迟", "问题", "故障",
]
NEGATORS: List[str] = ["not", "no", "never", "hardly", "lack", "without", "n't", "不", "没", "无"]
