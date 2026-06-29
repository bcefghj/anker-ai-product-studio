"""冒烟测试：可用 pytest 运行，也可 `python backend/tests/test_smoke.py` 直接运行。

验证 AI 原生工作流端到端跑通并满足关键不变量（offline 确定性模式）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _run():
    from anker_studio.application.runner import run_studio
    return run_studio(thread_id="test")


def test_pipeline_end_to_end():
    art = _run()
    assert not art.awaiting_human
    assert art.state.voc_report is not None
    assert art.state.voc_report.review_count > 0
    assert art.state.chosen_concept is not None
    assert art.state.decision is not None
    assert len(art.state.personas) >= 1


def test_grounding_and_comparison():
    art = _run()
    rub = art.rubric
    assert rub is not None
    # 所有论断都应带引用
    assert rub.groundedness >= 0.9
    assert rub.citation_hit_rate >= 0.9
    # AI 原生应优于经验驱动
    cmp = art.comparison
    assert cmp is not None
    assert cmp.arm_b.evidence_citations > cmp.arm_a.evidence_citations
    assert cmp.arm_b.real_pain_hit_rate >= cmp.arm_a.real_pain_hit_rate


if __name__ == "__main__":
    test_pipeline_end_to_end()
    test_grounding_and_comparison()
    print("OK: smoke tests passed")
