"""工具注册与读写分离（Common 层）。

对齐美团 `@is_tool(ToolType.READ/WRITE)` 范式：
- READ：无副作用、可并发。
- WRITE：有副作用，必须两步确认（preview -> 人工/HITL 确认 -> execute）。
工具失败返回结构化错误字符串而非抛异常（"错误即信息"）。
"""
from __future__ import annotations

from enum import Enum
from typing import Callable, Dict, List


class ToolType(str, Enum):
    READ = "read"
    WRITE = "write"


_REGISTRY: Dict[str, "RegisteredTool"] = {}


class RegisteredTool:
    def __init__(self, fn: Callable, tool_type: ToolType, name: str, doc: str):
        self.fn = fn
        self.tool_type = tool_type
        self.name = name
        self.doc = doc
        self.requires_confirmation = tool_type == ToolType.WRITE

    def __call__(self, *args, **kwargs):
        try:
            return self.fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - 错误即信息
            return f"[TOOL_ERROR] {self.name}: {exc}"


def tool(tool_type: ToolType) -> Callable:
    """注册一个工具。WRITE 工具会被标记为需要两步确认。"""

    def deco(fn: Callable) -> RegisteredTool:
        rt = RegisteredTool(
            fn=fn,
            tool_type=tool_type,
            name=fn.__name__,
            doc=(fn.__doc__ or "").strip(),
        )
        _REGISTRY[fn.__name__] = rt
        return rt

    return deco


def list_tools() -> List[str]:
    return sorted(_REGISTRY.keys())


def get_tool(name: str) -> RegisteredTool:
    return _REGISTRY[name]
