"""集中配置（Common 层）。从环境变量/.env 读取，全程只读。"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

# 项目根目录：.../anker-ai-product-studio
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _load_dotenv() -> None:
    """尽力加载 .env（缺少 python-dotenv 也不报错）。"""
    try:
        from dotenv import load_dotenv

        load_dotenv(PROJECT_ROOT / ".env")
    except Exception:  # noqa: BLE001 - 配置加载失败不应中断程序
        pass


class Settings(BaseModel):
    """运行配置。"""

    # LLM
    llm_provider: str = Field(default="offline", description="offline | minimax")
    minimax_api_key: str = Field(default="")
    minimax_base_url: str = Field(default="https://api.minimax.io/v1")
    minimax_model: str = Field(default="MiniMax-M3")

    # 媒体
    enable_media: bool = Field(default=False)

    # 运行
    max_retrieval_iters: int = Field(default=3)
    hitl: bool = Field(default=False, description="决策闸是否人工确认")
    trace_dir: str = Field(default="runs")

    # 路径
    project_root: str = Field(default=str(PROJECT_ROOT))
    data_dir: str = Field(default=str(PROJECT_ROOT / "data"))

    @property
    def trace_path(self) -> Path:
        p = PROJECT_ROOT / self.trace_dir
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache(maxsize=1)
def settings() -> Settings:
    _load_dotenv()

    def _bool(name: str, default: bool) -> bool:
        return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}

    return Settings(
        llm_provider=os.getenv("ANKER_LLM_PROVIDER", "offline").strip().lower(),
        minimax_api_key=os.getenv("MINIMAX_API_KEY", "").strip(),
        minimax_base_url=os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1").strip(),
        minimax_model=os.getenv("MINIMAX_MODEL", "MiniMax-M3").strip(),
        enable_media=_bool("ANKER_ENABLE_MEDIA", False),
        max_retrieval_iters=int(os.getenv("ANKER_MAX_RETRIEVAL_ITERS", "3")),
        hitl=_bool("ANKER_HITL", False),
        trace_dir=os.getenv("ANKER_TRACE_DIR", "runs").strip(),
    )
