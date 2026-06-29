"""统一 LLM 网关（Infrastructure 层）。

设计要点（呼应安克"确定性 vs 不确定性"）：
- 确定性核心由各分析模块产出结构化数值；网关主要负责"叙述/归纳/角色扮演/批判"。
- 两种 provider：
    offline —— 不联网，确定性：narrate() 直接返回传入文本，complete() 做抽取式摘要。
    minimax —— 调用 MiniMax M3 增强。
- 任何远程失败都自动降级到 offline，不中断流程（错误即信息）。
"""
from __future__ import annotations

import time
from typing import Optional

from anker_studio.common.config import Settings
from anker_studio.common.logging import log
from anker_studio.common.models import LLMResponse


class LLMGateway:
    def __init__(
        self,
        provider: str = "offline",
        minimax_client=None,
        default_model: str = "offline-deterministic",
    ):
        self.provider = provider
        self._minimax = minimax_client
        self.default_model = default_model

    @classmethod
    def from_settings(cls, settings: Settings) -> "LLMGateway":
        if settings.llm_provider == "minimax" and settings.minimax_api_key:
            from anker_studio.infrastructure.llm.minimax import MiniMaxClient

            client = MiniMaxClient(
                api_key=settings.minimax_api_key,
                base_url=settings.minimax_base_url,
                model=settings.minimax_model,
            )
            log.bind(node="llm").info(f"LLM provider=minimax model={settings.minimax_model}")
            return cls(provider="minimax", minimax_client=client, default_model=settings.minimax_model)
        log.bind(node="llm").info("LLM provider=offline（确定性模式，无网络）")
        return cls(provider="offline")

    @property
    def has_remote(self) -> bool:
        return self.provider == "minimax" and self._minimax is not None

    # ── 主接口 ──────────────────────────────────────────────
    def complete(
        self,
        system: str,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.6,
        task: str = "",
    ) -> LLMResponse:
        if self.has_remote:
            try:
                return self._minimax.chat(system, prompt, model, max_tokens, temperature)
            except Exception as exc:  # noqa: BLE001 - 远程失败降级
                log.bind(node="llm").warning(f"MiniMax 调用失败，降级 offline：{exc}")
        return self._offline_complete(system, prompt, task)

    def narrate(self, default_text: str, instruction: str, context: str = "", task: str = "") -> str:
        """把确定性结果包装成更顺畅的叙述。

        offline：直接返回 default_text（已是可读的确定性文本）。
        minimax：在 default_text 基础上做润色/扩写，但不得引入新事实。
        """
        if not self.has_remote:
            return default_text
        system = (
            "你是安克的资深产品负责人。只能基于给定事实进行润色与归纳，"
            "禁止引入任何未提供的新数据或新事实。输出简洁、专业、中文。"
        )
        prompt = (
            f"任务：{instruction}\n\n"
            f"事实与上下文（不得超出）：\n{context}\n\n"
            f"待润色的草稿：\n{default_text}\n\n请输出润色后的版本："
        )
        try:
            resp = self._minimax.chat(system, prompt, max_tokens=900, temperature=0.5)
            return resp.text.strip() or default_text
        except Exception as exc:  # noqa: BLE001
            log.bind(node="llm").warning(f"narrate 降级：{exc}")
            return default_text

    # ── offline 确定性实现 ────────────────────────────────────
    @staticmethod
    def _offline_complete(system: str, prompt: str, task: str) -> LLMResponse:
        start = time.time()
        # 抽取式摘要：取 prompt 的前若干句作为"回答"，保证零网络可运行且可复现。
        text = prompt.strip()
        sentences = [s.strip() for s in text.replace("\n", " ").split("。") if s.strip()]
        summary = "。".join(sentences[:3])
        out = summary or text[:400]
        return LLMResponse(
            text=out,
            model="offline-deterministic",
            provider="offline",
            tokens_in=len(prompt),
            tokens_out=len(out),
            latency_ms=round((time.time() - start) * 1000, 2),
        )
