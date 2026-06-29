"""CLI 入口（Starter 层）。

用法：
    python -m anker_studio.starter.cli run                # 跑完整 AI 原生工作流并写报告
    python -m anker_studio.starter.cli run --brief "..."  # 自定义 brief
    python -m anker_studio.starter.cli resume             # HITL 暂停后恢复
"""
from __future__ import annotations

import argparse
from pathlib import Path

from anker_studio.application.reporting import render_full_report, render_opening_report
from anker_studio.application.runner import DEFAULT_BRIEF, resume_studio, run_studio
from anker_studio.common.config import settings
from anker_studio.common.logging import log


def _write_reports(art) -> None:
    out_dir = Path(settings().project_root) / "docs" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "运行报告.md").write_text(render_full_report(art), encoding="utf-8")
    (out_dir / "开题报告_自动生成.md").write_text(render_opening_report(art), encoding="utf-8")
    log.bind(node="cli").info(f"报告已写入 {out_dir}")


def _print_summary(art) -> None:
    s = art.state
    cmp = art.comparison
    rub = art.rubric
    print("\n" + "=" * 64)
    print("AI 原生产品定义 · 运行摘要")
    print("=" * 64)
    if s.voc_report:
        print(f"评论样本：{s.voc_report.review_count}　Top机会：" +
              "、".join(o.aspect for o in s.voc_report.opportunities[:3]))
    if s.chosen_concept:
        print(f"概念：{s.chosen_concept.name} — {s.chosen_concept.one_liner}")
    if s.decision:
        print(f"决策：{s.decision.verdict.value}　预测NPS：{s.decision.nps_prediction:.0f}")
    if rub:
        print(f"评测 overall：{rub.overall}（groundedness={rub.groundedness}, "
              f"citation_hit={rub.citation_hit_rate}, coverage={rub.opportunity_coverage}）")
    if cmp:
        print(f"对比：命中真实痛点 经验{cmp.arm_a.real_pain_hit_rate:.0%} vs AI {cmp.arm_b.real_pain_hit_rate:.0%}"
              f"｜证据引用 {cmp.arm_a.evidence_citations} vs {cmp.arm_b.evidence_citations}"
              f"｜ΔNPS {cmp.deltas['nps_prediction']:+.1f}")
    print("=" * 64 + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Anker AI 原生产品定义系统")
    sub = ap.add_subparsers(dest="cmd", required=True)
    run_p = sub.add_parser("run", help="运行完整工作流")
    run_p.add_argument("--brief", default=DEFAULT_BRIEF)
    run_p.add_argument("--category", default="audio")
    run_p.add_argument("--hitl", action="store_true", help="决策闸人工确认")
    run_p.add_argument("--thread", default="cli")
    res_p = sub.add_parser("resume", help="HITL 恢复")
    res_p.add_argument("--thread", default="cli")
    args = ap.parse_args()

    if args.cmd == "run":
        art = run_studio(category=args.category, brief=args.brief, hitl=args.hitl, thread_id=args.thread)
        if art.awaiting_human:
            print(f"[HITL] 已在决策闸暂停。确认后运行：python -m anker_studio.starter.cli resume --thread {args.thread}")
            return 0
        _print_summary(art)
        _write_reports(art)
        return 0

    if args.cmd == "resume":
        art = resume_studio(thread_id=args.thread)
        _print_summary(art)
        _write_reports(art)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
