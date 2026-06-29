"""报告渲染（Application 层）：把 RunArtifacts 渲染成 Markdown。

产出：完整方案报告（提案 + 可行性 + 决策 + 评测 + AI/经验对比）以及
竞赛开题报告 Part1/Part2（数字取自真实运行结果）。
"""
from __future__ import annotations

from typing import List

from anker_studio.application.runner import RunArtifacts
from anker_studio.common.config import settings


def _faq_block(title: str, items) -> str:
    lines = [f"**{title}**", ""]
    for it in items:
        cite = f"（证据：{', '.join(it.evidence_ids)}）" if it.evidence_ids else ""
        lines.append(f"- **Q：{it.question}**")
        lines.append(f"  - A：{it.answer} {cite}")
    return "\n".join(lines)


def render_full_report(art: RunArtifacts) -> str:
    s = art.state
    p = s.proposal
    voc = s.voc_report
    cmp = art.comparison
    rub = art.rubric
    out: List[str] = []

    out.append(f"# Anker AI 原生产品定义 · 运行报告（{art.run_id}）\n")
    out.append(f"> 品类：{s.category}　目标品牌：{s.target_brand}　评论样本：{voc.review_count if voc else 0} 条　"
               f"LLM provider：{settings().llm_provider}　耗时：{art.elapsed_seconds}s\n")

    # 1. 用户洞察
    if voc:
        out.append("## 1. 用户洞察（AI 原生 JML）\n")
        out.append("| 维度 aspect | 提及覆盖 | 负面率 | 满意度 | 机会分 | Impact |")
        out.append("|---|---|---|---|---|---|")
        for a in voc.aspects[:9]:
            out.append(f"| {a.aspect} | {a.reach:.0%} | {a.negative_rate:.0%} | {a.satisfaction}/10 | "
                       f"{a.opportunity_score} | {a.impact_score} |")
        out.append("\n**Top 机会（按机会分）**：")
        for o in voc.opportunities[:5]:
            out.append(f"- `{o.id}` {o.statement} — 机会分 {o.opportunity_score}（证据：{', '.join(o.evidence_ids[:3])}）")
        out.append("")

    # 2. 市场/竞品
    if s.market_intel:
        out.append("## 2. 市场与竞品洞察（AI 原生 AMI / 超级智囊）\n")
        for c in s.market_intel.competitors:
            out.append(f"- **{c.brand}**（{c.review_count} 条）｜优势：{('、'.join(c.strengths) or '—')}｜"
                       f"短板：{('、'.join(c.weaknesses) or '—')}")
        if s.market_intel.white_space_opportunities:
            out.append("\n**白空间机会**：")
            for w in s.market_intel.white_space_opportunities[:4]:
                out.append(f"- `{w.id}` {w.statement}")
        out.append("")

    # 3. 概念
    if s.chosen_concept:
        c = s.chosen_concept
        out.append("## 3. 产品概念（双路径：VOC 驱动 + 技术原生）\n")
        out.append(f"**{c.name}** — {c.one_liner}\n")
        out.append(f"- 目标用户：{c.target_segment}")
        out.append(f"- 价值主张：{c.value_proposition}")
        out.append(f"- 核心功能：{('；'.join(c.key_features))}")
        out.append(f"- 技术使能：{('；'.join(c.tech_enablers))}")
        out.append("- 差异点：")
        for d in c.differentiators:
            out.append(f"  - {d.statement}（证据：{', '.join(d.evidence_ids[:2]) or '—'}）")
        out.append("")

    # 4. 合成用户
    if s.interviews:
        out.append("## 4. 用户替身验证（合成用户面板，假设盲）\n")
        for itv in s.interviews:
            out.append(f"- **{itv.segment}** → 判定：`{itv.verdict}`，接受度 {itv.acceptance:.0%}"
                       f"{'，异议：' + '；'.join(itv.objections) if itv.objections else ''}")
        out.append("")

    # 5. PR/FAQ
    if p and p.prfaq:
        f = p.prfaq
        out.append("## 5. 产品提案 PR/FAQ（Working Backwards）\n")
        out.append(f"### {f.headline}\n")
        out.append(f"*{f.subheading}*\n")
        out.append(f"{f.summary}\n")
        out.append(f"> 用户说：{f.customer_quote}\n")
        out.append(f"> 团队说：{f.maker_quote}\n")
        out.append(_faq_block("外部 FAQ", f.external_faq))
        out.append("")
        out.append(_faq_block("内部 FAQ", f.internal_faq))
        out.append("")

    # 6. 可行性 + 决策
    if p and p.feasibility:
        fe = p.feasibility
        out.append("## 6. 可行性与决策（行业专家 + 决策官）\n")
        out.append(f"- 技术：{fe.technical}")
        out.append(f"- 供应链：{fe.supply_chain}")
        out.append(f"- 成本：{fe.bom_cost}")
        out.append(f"- 合规：{fe.compliance}")
        out.append(f"- 总体：**{fe.overall.upper()}**")
        out.append("- 风险：")
        for r in fe.risks:
            out.append(f"  - [{r.severity}] {r.area}：{r.description} → {r.mitigation}")
        if p.decision:
            d = p.decision
            out.append(f"\n**决策：`{d.verdict.value}`**（置信度 {d.confidence}）｜预测 NPS {d.nps_prediction:.0f}")
            out.append(f"- 理由：{d.rationale}")
            if d.conditions:
                out.append(f"- 条件：{'；'.join(d.conditions)}")
        if p.concept_image_path:
            out.append(f"\n![concept]({p.concept_image_path})")
        out.append("")

    # 7. 评测
    if rub:
        out.append("## 7. 评测 Rubric\n")
        out.append("| 指标 | 值 |")
        out.append("|---|---|")
        out.append(f"| groundedness（论断带引用比例） | {rub.groundedness} |")
        out.append(f"| faithfulness（引用支撑论断比例） | {rub.faithfulness} |")
        out.append(f"| citation_hit_rate（引用命中） | {rub.citation_hit_rate} |")
        out.append(f"| opportunity_coverage（机会覆盖） | {rub.opportunity_coverage} |")
        out.append(f"| persona_fidelity（合成用户 grounding） | {rub.persona_fidelity} |")
        out.append(f"| mean_iterations（平均检索迭代） | {rub.mean_iterations} |")
        out.append(f"| explainability（可解释性） | {rub.explainability} |")
        out.append(f"| **overall** | **{rub.overall}** |")
        if rub.notes:
            out.append("\n门槛提示：" + "；".join(rub.notes))
        out.append("")

    # 8. 对比
    if cmp:
        out.append("## 8. AI 驱动 vs 经验驱动（命题核心对比）\n")
        a, b = cmp.arm_a, cmp.arm_b
        out.append("| 维度 | A 经验驱动 | B AI 原生 | Δ |")
        out.append("|---|---|---|---|")
        out.append(f"| 机会覆盖率 | {a.opportunity_coverage:.0%} | {b.opportunity_coverage:.0%} | {cmp.deltas['opportunity_coverage']:+.2f} |")
        out.append(f"| 命中真实痛点率 | {a.real_pain_hit_rate:.0%} | {b.real_pain_hit_rate:.0%} | {cmp.deltas['real_pain_hit_rate']:+.2f} |")
        out.append(f"| 证据引用数 | {a.evidence_citations} | {b.evidence_citations} | {cmp.deltas['evidence_citations']:+.0f} |")
        out.append(f"| 已验证假设数 | {a.validated_assumptions} | {b.validated_assumptions} | {cmp.deltas['validated_assumptions']:+.0f} |")
        out.append(f"| 合成用户数 | {a.distinct_personas_consulted} | {b.distinct_personas_consulted} | {b.distinct_personas_consulted - a.distinct_personas_consulted:+.0f} |")
        out.append(f"| 可行性风险识别 | {a.feasibility_risks_identified} | {b.feasibility_risks_identified} | {cmp.deltas['feasibility_risks_identified']:+.0f} |")
        out.append(f"| 预测 NPS | {a.nps_prediction:.0f} | {b.nps_prediction:.0f} | {cmp.deltas['nps_prediction']:+.1f} |")
        out.append(f"\n{cmp.narrative}\n")
    return "\n".join(out)


def to_view(art: RunArtifacts) -> dict:
    """构造前端用的紧凑视图（剔除原始 evidence 大数组）。"""
    s = art.state
    voc = s.voc_report
    intel = s.market_intel
    p = s.proposal
    cmp = art.comparison
    rub = art.rubric

    def opp(o):
        return {"id": o.id, "aspect": o.aspect, "statement": o.statement,
                "opportunity_score": o.opportunity_score, "evidence_ids": o.evidence_ids[:3]}

    return {
        "run_id": art.run_id,
        "elapsed_seconds": art.elapsed_seconds,
        "provider": settings().llm_provider,
        "category": s.category,
        "target_brand": s.target_brand,
        "voc": None if not voc else {
            "review_count": voc.review_count,
            "aspects": [a.model_dump() for a in voc.aspects],
            "opportunities": [opp(o) for o in voc.opportunities[:6]],
            "ost": voc.ost.model_dump() if voc.ost else None,
        },
        "market": None if not intel else {
            "competitors": [c.model_dump() for c in intel.competitors],
            "white_space": [opp(o) for o in intel.white_space_opportunities[:4]],
            "trends": [t.model_dump() for t in intel.trends],
        },
        "concept": s.chosen_concept.model_dump() if s.chosen_concept else None,
        "personas": [pp.model_dump() for pp in s.personas],
        "interviews": [iv.model_dump() for iv in s.interviews],
        "feasibility": s.feasibility.model_dump() if s.feasibility else None,
        "nps": s.nps.model_dump() if s.nps else None,
        "prfaq": p.prfaq.model_dump() if (p and p.prfaq) else None,
        "decision": s.decision.model_dump() if s.decision else None,
        "rubric": rub.model_dump() if rub else None,
        "comparison": cmp.model_dump() if cmp else None,
        "concept_image_path": p.concept_image_path if p else None,
    }


def render_opening_report(art: RunArtifacts) -> str:
    """竞赛开题报告 Part1/Part2（数字取自真实运行）。"""
    s = art.state
    voc = s.voc_report
    cmp = art.comparison
    top = voc.opportunities[:3] if voc else []
    top_aspects = "、".join(o.aspect for o in top) or "核心体验"
    hit_b = int(cmp.arm_b.real_pain_hit_rate * 100) if cmp else 0
    hit_a = int(cmp.arm_a.real_pain_hit_rate * 100) if cmp else 0
    dnps = cmp.deltas["nps_prediction"] if cmp else 0

    out: List[str] = []
    out.append("# 开题报告（由系统真实产出，数字随数据更新）\n")
    out.append("## Part 1 命题前置分析与洞察\n")
    out.append(
        f"安克在 2023 年 All in AI 后，已沉淀 AIME（300+ Agent，含 VOC 洞察/需求生成）与 "
        f"JML/BEES/AMI 三大产品方法论平台，NPS 为核心指标。命题表面是“设计一款产品”，"
        f"本质是要验证：能否用 AI 把“产品经理拍脑袋”重构为“数据可溯源、可验证、可量化”的工作流。"
        f"我们对 {voc.review_count if voc else 0} 条真实 soundcore/竞品评论做确定性 ABSA，"
        f"发现机会分最高的痛点集中在 {top_aspects}——这与“凭直觉做更好音质/续航/性价比”的常识假设并不一致，"
        f"正说明经验驱动存在系统性盲区。\n"
    )
    out.append("## Part 2 整体解决方案设计\n")
    out.append(
        "**1. 方案概述**：构建“AI 原生产品定义系统”，把安克 JML/BEES/AMI 做成 AI 原生版，"
        "让 AI 扮演超级智囊/用户替身/行业专家，端到端从真实评论跑到一份可溯源的产品提案(PR/FAQ)。\n"
        "**2. 架构与模块**：多源真实数据(Evidence) → JML 用户洞察(ABSA+ODI+机会树) + AMI 竞品/趋势 → "
        "产品经理双路径概念(VOC 驱动 + 第一性原理技术原生) → 用户替身(OCEAN 合成用户, 假设盲) → "
        "行业专家可行性(技术/BOM/供应链/合规) + 决策官(NPS + GO/NO-GO)，由 StateGraph 编排，"
        "全程引用校验 + 决策审计 + HITL 闸口。\n"
        "**3. 核心创新**：①方法论创新——双路径覆盖“用户洞察”与“技术原生”；②工程创新——确定性核心+LLM 增强，"
        "强制逐字引用校验，对标大厂 AIGC 规范(四层架构/AI Rule/Pre-PR/跨模型对抗 CR)；③把“本质不同”做成可量化对比实验。\n"
        f"**4. 落地价值（可量化）**：在相同 brief 下，AI 原生命中真实痛点率 {hit_b}% vs 经验驱动 {hit_a}%，"
        f"预测 NPS 高出 {dnps:+.0f} 分，且全部结论可溯源到真实评论；方法论可沉淀为安克内部 SOP。\n"
        "**5. 可行性与可推广**：系统离线即可复现，接入 MiniMax/真实 Amazon 数据即增强；"
        "品类无关，换充电/eufy 仅需更换数据配置，可直接迁移到安克其它品类。\n"
    )
    return "\n".join(out)
