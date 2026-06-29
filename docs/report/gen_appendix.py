#!/usr/bin/env python3
"""生成 LaTeX 源码附录（appendix_code.tex）：把真实源码逐文件以 lstinputlisting 收录。

在 docs/report/ 下运行：python3 gen_appendix.py
路径相对 docs/report/（用 ../../ 指回项目根，避开中文绝对路径）。
"""
from __future__ import annotations

from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parent
ROOT = REPORT_DIR.parents[1]

# 按逻辑顺序收录的文件（相对项目根）。注释/中文 docstring 已验证可编译。
GROUPS = [
    ("Common 层（领域模型 / 配置 / 工具 / 引用校验）", [
        "backend/anker_studio/common/models.py",
        "backend/anker_studio/common/config.py",
        "backend/anker_studio/common/logging.py",
        "backend/anker_studio/common/tools.py",
        "backend/anker_studio/common/citations.py",
    ]),
    ("Infrastructure 层（LLM 网关 / 数据 / RAG / NLP / 媒体 / 观测）", [
        "backend/anker_studio/infrastructure/llm/gateway.py",
        "backend/anker_studio/infrastructure/llm/minimax.py",
        "backend/anker_studio/infrastructure/data/loader.py",
        "backend/anker_studio/infrastructure/data/amazon_reviews.py",
        "backend/anker_studio/infrastructure/data/connectors.py",
        "backend/anker_studio/infrastructure/nlp/lexicons.py",
        "backend/anker_studio/infrastructure/nlp/absa.py",
        "backend/anker_studio/infrastructure/rag/retrieval.py",
        "backend/anker_studio/infrastructure/assets/media.py",
        "backend/anker_studio/infrastructure/observability/trace.py",
    ]),
    ("Application 层 · 方法论（ODI / OST / Working Backwards）", [
        "backend/anker_studio/application/methodology/odi.py",
        "backend/anker_studio/application/methodology/ost.py",
        "backend/anker_studio/application/methodology/working_backwards.py",
    ]),
    ("Application 层 · 安克三平台（JML / AMI / BEES）", [
        "backend/anker_studio/application/platforms/jml.py",
        "backend/anker_studio/application/platforms/ami.py",
        "backend/anker_studio/application/platforms/bees.py",
    ]),
    ("Application 层 · 五个 Agent", [
        "backend/anker_studio/application/agents/base.py",
        "backend/anker_studio/application/agents/super_think_tank.py",
        "backend/anker_studio/application/agents/product_manager.py",
        "backend/anker_studio/application/agents/user_proxy.py",
        "backend/anker_studio/application/agents/industry_expert.py",
        "backend/anker_studio/application/agents/decision_officer.py",
    ]),
    ("Application 层 · 编排 / 评测 / 对照 / 报告", [
        "backend/anker_studio/application/graph/state.py",
        "backend/anker_studio/application/graph/engine.py",
        "backend/anker_studio/application/graph/checkpoint.py",
        "backend/anker_studio/application/graph/pipeline.py",
        "backend/anker_studio/application/baseline/experience_driven.py",
        "backend/anker_studio/application/evaluation/rubric.py",
        "backend/anker_studio/application/evaluation/comparison.py",
        "backend/anker_studio/application/runner.py",
        "backend/anker_studio/application/reporting.py",
    ]),
    ("Starter 层（CLI / FastAPI）与入口", [
        "backend/anker_studio/starter/cli.py",
        "backend/anker_studio/starter/api.py",
        "run.py",
    ]),
    ("前端工作台（零依赖可视化）", [
        "frontend/index.html",
        "frontend/app.js",
        "frontend/styles.css",
    ]),
    ("宣传 Landing 页", [
        "web/landing/index.html",
    ]),
    ("工程规范与运维脚本", [
        ".cursor/rules/00-engineering-baseline.mdc",
        ".cursor/rules/10-agent-conventions.mdc",
        "scripts/pre_pr_check.py",
        "scripts/cross_model_review.py",
        "scripts/deploy.py",
        "scripts/server_exec.py",
        "scripts/update_hub.py",
        "data/make_sample.py",
        "backend/tests/test_smoke.py",
    ]),
]

# 注意：listings 无内置 JavaScript 语言，留空以纯文本列出，避免编译报错
LANG = {
    ".py": "Python", ".js": "", ".html": "HTML", ".css": "",
    ".md": "", ".mdc": "", ".txt": "", ".json": "",
}


def esc(s: str) -> str:
    return s.replace("_", r"\_").replace("&", r"\&").replace("%", r"\%").replace("#", r"\#")


def main() -> None:
    out = ["% 自动生成：源码附录。请用 gen_appendix.py 重新生成。", ""]
    for title, files in GROUPS:
        out.append(f"\\section{{{title}}}")
        for rel in files:
            p = ROOT / rel
            if not p.exists():
                out.append(f"\\subsection*{{(缺失) \\texttt{{{esc(rel)}}}}}")
                continue
            lang = LANG.get(p.suffix, "")
            nlines = sum(1 for _ in p.open("r", encoding="utf-8", errors="ignore"))
            out.append(f"\\subsection*{{\\texttt{{{esc(rel)}}} \\hfill \\normalfont\\small ({nlines} 行)}}")
            opt = f"[language={lang}]" if lang else "[]"
            out.append(f"\\lstinputlisting{opt}{{../../{rel}}}")
            out.append("")
    (REPORT_DIR / "appendix_code.tex").write_text("\n".join(out), encoding="utf-8")
    print(f"已生成 appendix_code.tex（{len(GROUPS)} 组）")


if __name__ == "__main__":
    main()
