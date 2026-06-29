"""FastAPI 入口（Starter 层）：暴露工作流运行 + 流式 trace + 报告，并托管前端工作台。

运行：
    PYTHONPATH=backend uvicorn anker_studio.starter.api:app --reload --port 8000
然后浏览器打开 http://localhost:8000
"""
from __future__ import annotations

import json
import queue
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from anker_studio.application.reporting import (
    render_full_report,
    render_opening_report,
    to_view,
)
from anker_studio.application.runner import DEFAULT_BRIEF, run_studio
from anker_studio.common.config import settings
from anker_studio.infrastructure.observability.trace import Tracer

app = FastAPI(title="Anker AI 原生产品定义系统", version="0.1.0")

FRONTEND_DIR = Path(settings().project_root) / "frontend"
ASSETS_DIR = Path(settings().project_root) / "assets"

# 缓存最近一次运行，供报告接口使用
_LAST: Dict[str, Any] = {}


class RunRequest(BaseModel):
    brief: Optional[str] = None


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "provider": settings().llm_provider}


@app.post("/api/run")
def run(req: RunRequest = RunRequest()) -> JSONResponse:
    brief = req.brief or DEFAULT_BRIEF
    art = run_studio(brief=brief, thread_id="api")
    _LAST["art"] = art
    return JSONResponse(to_view(art))


@app.get("/api/stream")
def stream(brief: str = DEFAULT_BRIEF) -> StreamingResponse:
    """SSE：边跑边推送 trace 事件，结束推送最终视图。"""
    q: "queue.Queue[dict]" = queue.Queue()
    tracer = Tracer()
    tracer.subscribe(lambda ev: q.put({"type": "trace", "event": ev}))

    def worker() -> None:
        try:
            art = run_studio(brief=brief, thread_id="api", tracer=tracer)
            _LAST["art"] = art
            q.put({"type": "result", "view": to_view(art)})
        except Exception as exc:  # noqa: BLE001 - 把错误也推给前端
            q.put({"type": "error", "message": str(exc)})
        finally:
            q.put({"type": "done"})

    threading.Thread(target=worker, daemon=True).start()

    def gen():
        while True:
            item = q.get()
            yield f"data: {json.dumps(item, ensure_ascii=False, default=str)}\n\n"
            if item.get("type") == "done":
                break

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/report")
def report(kind: str = "full") -> JSONResponse:
    art = _LAST.get("art")
    if art is None:
        return JSONResponse({"error": "尚未运行，请先 POST /api/run 或 /api/stream"}, status_code=400)
    md = render_opening_report(art) if kind == "opening" else render_full_report(art)
    return JSONResponse({"markdown": md})


if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(FRONTEND_DIR / "index.html"))


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
