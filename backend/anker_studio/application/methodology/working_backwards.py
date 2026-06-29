"""Working Backwards PR/FAQ 生成（Application 层）。

把产品概念 + 机会 + 可行性 + NPS 组装成 PR/FAQ。确定性产出可读文档；
可选由 LLM 网关 narrate() 润色（不引入新事实）。每个差异点回链 evidence_ids。
"""
from __future__ import annotations

from typing import List

from anker_studio.common.models import (
    CompetitorFinding,
    FaqItem,
    FeasibilityAssessment,
    NPSPrediction,
    Opportunity,
    PRFAQ,
    ProductConcept,
)


def build_prfaq(
    concept: ProductConcept,
    opportunities: List[Opportunity],
    feasibility: FeasibilityAssessment,
    nps: NPSPrediction,
    competitors: List[CompetitorFinding],
) -> PRFAQ:
    top_opps = opportunities[:3]
    addressed = "、".join(o.aspect for o in top_opps) or "核心体验"
    comp_names = "、".join(c.brand for c in competitors) or "主流竞品"

    headline = f"{concept.name}：用端侧 AI 重新定义{concept.category}的{addressed}"
    subheading = (
        f"面向{concept.target_segment}。{concept.value_proposition}"
    )
    summary = (
        f"（深圳）安克 soundcore 今日发布 {concept.name}。它针对真实用户在"
        f"{addressed}上的长期痛点，通过{('、'.join(concept.tech_enablers) or '端侧 AI 能力')}，"
        f"把过去靠经验拍脑袋才能发现的需求，变成由数据与 AI 验证过的确定性改进。"
    )
    customer_quote = (
        "「我换过好几副耳机，最大的问题终于被认真解决了——而且它真的懂我怎么用。」"
        "——来自真实评论聚类的目标用户"
    )
    maker_quote = (
        "「这不是又一次拍脑袋。每一个功能点都能追溯到一条真实用户证据和一项可行性结论。」"
        "——产品负责人"
    )
    cta = f"了解 {concept.name} 如何用 AI 原生方法从洞察走到定义。"

    external: List[FaqItem] = [
        FaqItem(
            question="它和 " + comp_names + " 有什么不同？",
            answer=(
                "竞品在部分维度领先，但在"
                + "、".join(
                    w for c in competitors for w in c.white_space
                )[:120]
                + " 等空白上仍未满足；本品正是冲着这些空白设计。"
            ),
            evidence_ids=[eid for c in competitors for eid in c.evidence_ids][:4],
        ),
        FaqItem(
            question="为什么用户会买单？",
            answer=(
                f"它直接解决了机会分最高的痛点（{addressed}），这些痛点来自真实评论统计而非主观判断。"
            ),
            evidence_ids=[eid for o in top_opps for eid in o.evidence_ids][:4],
        ),
        FaqItem(
            question="主要限制是什么？",
            answer="端侧 AI 受功耗与成本约束，首发聚焦最高价值的 2–3 个能力，其余通过 OTA 迭代。",
            evidence_ids=[],
        ),
    ]
    internal: List[FaqItem] = [
        FaqItem(
            question="技术可行性如何？",
            answer=feasibility.technical or "依托端侧 AI 芯片能力，核心能力可在端侧实时运行。",
            evidence_ids=feasibility.evidence_ids[:3],
        ),
        FaqItem(
            question="成本与供应链风险？",
            answer=(feasibility.bom_cost or "") + " " + (feasibility.supply_chain or ""),
            evidence_ids=[],
        ),
        FaqItem(
            question="成功指标？",
            answer=f"预测 NPS {nps.score:.0f}；首发关注高机会痛点的满意度提升与复购。",
            evidence_ids=nps.evidence_ids[:3],
        ),
        FaqItem(
            question="主要风险？",
            answer="；".join(f"{r.area}:{r.description}" for r in feasibility.risks[:3]),
            evidence_ids=[],
        ),
    ]
    return PRFAQ(
        headline=headline,
        subheading=subheading,
        summary=summary,
        customer_quote=customer_quote,
        maker_quote=maker_quote,
        call_to_action=cta,
        external_faq=external,
        internal_faq=internal,
    )
