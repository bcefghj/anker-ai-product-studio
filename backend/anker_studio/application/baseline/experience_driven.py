"""经验驱动对照组（Application 层）—— 对比实验 A 组。

模拟传统 PM "拍脑袋"：不接数据管线，仅凭一次性直觉从 brief 产出概念。
用于和 AI 原生工作流（B 组）做可量化对比，回答命题"本质不同"。
"""
from __future__ import annotations

import time
from typing import List

from pydantic import BaseModel, Field

from anker_studio.common.models import ProductConcept
from anker_studio.infrastructure.llm.gateway import LLMGateway

# 行业"常识/直觉"里最常被拍的几个点（无数据支撑，可能与真实高机会痛点错位）
GUT_PAINS = ["音质", "续航", "价格/价值"]


class BaselineResult(BaseModel):
    concept: ProductConcept
    assumed_pains: List[str] = Field(default_factory=list)
    elapsed_seconds: float = 0.0
    citations: int = 0
    validated_assumptions: int = 0


def run_experience_driven(category: str, brief: str, gateway: LLMGateway) -> BaselineResult:
    start = time.time()
    concept = ProductConcept(
        id="A-GUT",
        name="soundcore（经验驱动概念）",
        category=category,
        path="voc_driven",
        one_liner="凭经验判断：做更好的音质、更长续航、更高性价比。",
        target_segment="大众消费者",
        value_proposition="在大家都关心的常规维度上做到更好。",
        key_features=[f"提升「{p}」" for p in GUT_PAINS],
        differentiators=[],          # 无证据支撑
        tech_enablers=[],
        addressed_opportunity_ids=[],
    )
    # 经验驱动通常不做证据检索、不做合成用户验证
    return BaselineResult(
        concept=concept,
        assumed_pains=GUT_PAINS,
        elapsed_seconds=round(time.time() - start, 4),
        citations=0,
        validated_assumptions=0,
    )
