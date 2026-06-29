"""MiniMax M3 客户端（OpenAI 兼容 /chat/completions）。

只负责把一次 chat 请求发给 MiniMax 并解析文本，失败时抛出 RuntimeError，由网关降级。
"""
from __future__ import annotations

import json
import time
from typing import List, Optional

from anker_studio.common.models import LLMResponse


class MiniMaxClient:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(
        self,
        system: str,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.6,
    ) -> LLMResponse:
        import requests  # 局部导入：offline 模式无需安装 requests

        url = f"{self.base_url}/chat/completions"
        messages: List[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": model or self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        start = time.time()
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=90)
        if resp.status_code != 200:
            raise RuntimeError(f"MiniMax HTTP {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"MiniMax 响应解析失败: {exc}; body={str(data)[:300]}")
        usage = data.get("usage", {}) or {}
        return LLMResponse(
            text=text or "",
            model=payload["model"],
            provider="minimax",
            tokens_in=int(usage.get("prompt_tokens", 0) or 0),
            tokens_out=int(usage.get("completion_tokens", 0) or 0),
            latency_ms=round((time.time() - start) * 1000, 1),
        )
