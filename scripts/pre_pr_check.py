#!/usr/bin/env python3
"""Pre-PR 自查（对标美团 Pre-PR 机制）。

提交前强制运行：在不依赖外部服务的前提下做基础规范校验，过滤掉 AI 编码常见的
低级问题，让人工/跨模型 CR 只聚焦业务语义。

校验项（确定性、零依赖）：
  1. 后端模块是否落在四层架构目录内（layering）。
  2. Python 文件是否使用了 `print(` / 标准库 `logging`（应使用 loguru）。
  3. Python 模块是否声明 `from __future__ import annotations`。
  4. 是否存在裸 `except:`（吞异常）。

退出码非 0 表示未通过，应阻止提交。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend" / "anker_studio"
ALLOWED_LAYERS = {"common", "infrastructure", "application", "starter"}


def _py_files(base: Path):
    return [p for p in base.rglob("*.py") if "__pycache__" not in p.parts]


def check_layering(violations: list[str]) -> None:
    if not BACKEND.exists():
        return
    for p in _py_files(BACKEND):
        rel = p.relative_to(BACKEND)
        if rel.name == "__init__.py" and len(rel.parts) == 1:
            continue
        top = rel.parts[0]
        if top not in ALLOWED_LAYERS:
            violations.append(f"[layering] {rel} 不在四层架构目录内 {sorted(ALLOWED_LAYERS)}")


def check_style(violations: list[str]) -> None:
    if not BACKEND.exists():
        return
    print_re = re.compile(r"(^|\s)print\(")
    logging_re = re.compile(r"^\s*import logging|^\s*from logging\b")
    bare_except_re = re.compile(r"^\s*except\s*:\s*$")
    for p in _py_files(BACKEND):
        text = p.read_text(encoding="utf-8")
        rel = p.relative_to(ROOT)
        lines = text.splitlines()
        if "from __future__ import annotations" not in text:
            violations.append(f"[future] {rel} 缺少 `from __future__ import annotations`")
        # starter 层是程序入口，stdout 即产品输出，允许 print（不算违规）
        is_starter = "starter" in p.relative_to(BACKEND).parts
        for i, line in enumerate(lines, 1):
            if print_re.search(line) and "noqa" not in line and not is_starter:
                violations.append(f"[no-print] {rel}:{i} 使用了 print()（应用 loguru）")
            if logging_re.search(line):
                violations.append(f"[no-logging] {rel}:{i} 使用了标准库 logging（应用 loguru）")
            if bare_except_re.match(line):
                violations.append(f"[bare-except] {rel}:{i} 裸 except（应捕获具体异常）")


def main() -> int:
    violations: list[str] = []
    check_layering(violations)
    check_style(violations)
    if violations:
        print("Pre-PR 未通过，请修复以下问题：")
        for v in violations:
            print("  - " + v)
        return 1
    print("Pre-PR 通过：四层架构 / 日志 / 类型注解 / 异常处理 规范校验 OK。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
