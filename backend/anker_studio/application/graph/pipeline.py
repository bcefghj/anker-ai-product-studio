"""AI 原生工作流的图装配（Application 层）。

节点顺序：
  voc → think_tank → pm → users → expert → decision →(条件)→ output / 回到 pm
决策闸前设 interrupt_before（HITL）。
"""
from __future__ import annotations

from typing import Optional

from anker_studio.application.agents.decision_officer import DecisionOfficerAgent
from anker_studio.application.agents.industry_expert import IndustryExpertAgent
from anker_studio.application.agents.product_manager import ProductManagerAgent
from anker_studio.application.agents.super_think_tank import SuperThinkTankAgent
from anker_studio.application.agents.user_proxy import UserProxyAgent
from anker_studio.application.graph.engine import END, StateGraph
from anker_studio.application.graph.state import PipelineState
from anker_studio.application.methodology.working_backwards import build_prfaq
from anker_studio.application.platforms.bees import experience_trend
from anker_studio.application.platforms.jml import build_voc_report
from anker_studio.common.models import DecisionVerdict, ProductProposal
from anker_studio.infrastructure.assets.media import generate_concept_image, synthesize_narration
from anker_studio.infrastructure.llm.gateway import LLMGateway
from anker_studio.infrastructure.observability.trace import Tracer


def build_studio_graph(
    gateway: LLMGateway,
    rag,
    tracer: Tracer,
    hitl: bool = False,
) -> StateGraph:
    think_tank = SuperThinkTankAgent(gateway, rag, tracer)
    pm = ProductManagerAgent(gateway, rag, tracer)
    users = UserProxyAgent(gateway, rag, tracer)
    expert = IndustryExpertAgent(gateway, rag, tracer)
    decision = DecisionOfficerAgent(gateway, rag, tracer)

    def voc_node(state: PipelineState) -> PipelineState:
        report = build_voc_report(state.category, state.target_brand, state.target_evidences)
        state.voc_report = report
        focus = [o.aspect for o in report.opportunities[:3]]
        state.experience_trend = experience_trend(state.target_evidences, focus)
        for o in report.opportunities[:5]:
            state.add_claim(o.statement, o.evidence_ids)
        return state

    def output_node(state: PipelineState) -> PipelineState:
        concept = state.chosen_concept
        voc = state.voc_report
        if concept is None or voc is None or state.decision is None:
            return state
        prfaq = build_prfaq(
            concept=concept,
            opportunities=voc.opportunities,
            feasibility=state.feasibility,
            nps=state.nps,
            competitors=state.market_intel.competitors if state.market_intel else [],
        )
        # 可选 LLM 润色（不引入新事实）
        prfaq.summary = gateway.narrate(
            prfaq.summary, "润色产品新闻稿摘要，专业简洁", context=concept.value_proposition
        )
        state.prfaq = prfaq

        addressed = [o for o in voc.opportunities if o.id in concept.addressed_opportunity_ids]
        image_path = generate_concept_image(
            f"Premium {state.category} product concept: {concept.name}, {concept.one_liner}, "
            f"clean studio render, soundcore brand aesthetic"
        )
        narration = synthesize_narration(prfaq.summary)
        state.proposal = ProductProposal(
            concept=concept,
            prfaq=prfaq,
            feasibility=state.feasibility,
            nps=state.nps,
            addressed_opportunities=addressed,
            decision=state.decision,
            concept_image_path=image_path,
            narration_audio_path=narration,
        )
        return state

    def route_after_decision(state: PipelineState) -> str:
        d = state.decision
        if d is None:
            return "output"
        if d.verdict == DecisionVerdict.GO or state.pm_iteration >= state.max_pm_iterations:
            return "output"
        return "pm"  # 未达 GO 且仍有迭代预算 -> 回到产品经理修订

    g = StateGraph(tracer=tracer, hitl=hitl)
    g.add_node("voc", voc_node)
    g.add_node("think_tank", think_tank.run)
    g.add_node("pm", pm.run)
    g.add_node("users", users.run)
    g.add_node("expert", expert.run)
    g.add_node("decision", decision.run)
    g.add_node("output", output_node)

    g.set_entry("voc")
    g.add_edge("voc", "think_tank")
    g.add_edge("think_tank", "pm")
    g.add_edge("pm", "users")
    g.add_edge("users", "expert")
    g.add_edge("expert", "decision")
    g.add_conditional("decision", route_after_decision)
    g.add_edge("output", END)
    g.set_interrupt_before(["decision"])
    return g
