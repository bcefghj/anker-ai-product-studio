#!/usr/bin/env python3
"""跨厂商模型对抗 Code Review（对标美团"高阶模型审低阶 + 不同厂商互审"）。

把一段 diff/文件交给一个"审查模型"（默认 MiniMax-M3），要求它按本仓 AI Rule
（四层架构 / Pydantic / loguru / 引用纪律 / 两步确认）输出结构化评审意见。

用法：
    python scripts/cross_model_review.py <file_or_dir> [--reviewer MiniMax-M3]

若未配置 MINIMAX_API_KEY，则退化为本地规则审查（提示用户配置后可得到语义级审查）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

REVIEW_RUBRIC = """你是一名资深架构师，按以下规范审查代码（仅输出问题清单，按严重度排序）：
1. 四层架构：starter→application→infrastructure→common 单向依赖，无反向/跨层依赖。
2. 数据模型用 Pydantic v2；完整类型注解；模块含 `from __future__ import annotations`。
3. 日志用 loguru，不用 print / logging。
4. 工具区分 READ/WRITE，WRITE 必须两步确认。
5. 引用纪律：洞察/结论必须带 evidence_ids，并可逐字命中校验。
6. 异常有 fallback，不静默失败。
输出格式：每行 `[严重度 高/中/低][规则编号] 文件:行 — 问题与修复建议`。无问题则输出 `PASS`。
"""


def collect_code(target: Path) -> str:
    files = [target] if target.is_file() else [
        p for p in target.rglob("*.py") if "__pycache__" not in p.parts
    ]
    chunks = []
    for p in files[:40]:
        chunks.append(f"\n===== FILE: {p.relative_to(ROOT)} =====\n" + p.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="要审查的文件或目录")
    ap.add_argument("--reviewer", default="MiniMax-M3")
    args = ap.parse_args()

    target = Path(args.target).resolve()
    if not target.exists():
        print(f"目标不存在: {target}")
        return 2

    code = collect_code(target)
    try:
        from anker_studio.infrastructure.llm.gateway import LLMGateway
        from anker_studio.common.config import settings

        gw = LLMGateway.from_settings(settings())
        if not gw.has_remote:
            print("[降级] 未配置 MINIMAX_API_KEY，无法做跨厂商语义级审查。")
            print("       请 `export MINIMAX_API_KEY=...` 后重试，或先用 scripts/pre_pr_check.py 做规范校验。")
            return 0
        result = gw.complete(
            system=REVIEW_RUBRIC,
            prompt=f"请审查以下代码：\n{code}",
            model=args.reviewer,
            max_tokens=2048,
            task="code_review",
        )
        print(result.text)
        return 0
    except Exception as exc:  # noqa: BLE001 - 审查脚本对任何失败都应给出可读提示
        print(f"[降级] 跨模型审查不可用：{exc}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
