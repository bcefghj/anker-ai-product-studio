"""统一日志（Common 层）。一律使用 loguru。"""
from __future__ import annotations

import sys

from loguru import logger

_CONFIGURED = False


def setup_logging(level: str = "INFO") -> "logger.__class__":  # type: ignore[name-defined]
    """配置并返回 loguru logger（幂等）。"""
    global _CONFIGURED
    if not _CONFIGURED:
        logger.remove()
        logger.add(
            sys.stderr,
            level=level,
            format=(
                "<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | "
                "<cyan>{extra[node]}</cyan> | {message}"
            ),
            colorize=True,
        )
        logger.configure(extra={"node": "-"})
        _CONFIGURED = True
    return logger


# 默认导出已配置的 logger
log = setup_logging()
