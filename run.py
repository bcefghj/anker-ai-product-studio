#!/usr/bin/env python3
"""生产入口：启动 FastAPI（供 systemd 守护）。

监听 127.0.0.1:$PORT（默认 8766，对齐服务器项目二端口约定），只对 nginx 开放。
本地直接运行也可：`python run.py`。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 把 backend 加入 import 路径（无需设置 PYTHONPATH）
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))


def main() -> None:
    import uvicorn

    # 用 ANKER_HOST 而非 HOST：macOS/部分 shell 会把 HOST 设为主机名，导致绑定失败
    host = os.getenv("ANKER_HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8766"))
    uvicorn.run("anker_studio.starter.api:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
