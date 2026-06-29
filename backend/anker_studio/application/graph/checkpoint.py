"""Checkpointer（Application 层）：JSON 持久化，支持长流程续跑 / HITL 恢复。

语义对齐 LangGraph 的 checkpointer：按 thread_id 保存 (state, next_node)。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Tuple

from anker_studio.common.config import settings
from anker_studio.application.graph.state import PipelineState


class JsonCheckpointer:
    def __init__(self, directory: Optional[str] = None):
        self.dir = Path(directory) if directory else (settings().trace_path / "checkpoints")
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, thread_id: str) -> Path:
        return self.dir / f"{thread_id}.json"

    def save(self, thread_id: str, state: PipelineState, next_node: str) -> None:
        payload = {"next_node": next_node, "state": state.model_dump(mode="json")}
        self._path(thread_id).write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

    def load(self, thread_id: str) -> Optional[Tuple[PipelineState, str]]:
        p = self._path(thread_id)
        if not p.exists():
            return None
        payload = json.loads(p.read_text(encoding="utf-8"))
        return PipelineState.model_validate(payload["state"]), payload["next_node"]
