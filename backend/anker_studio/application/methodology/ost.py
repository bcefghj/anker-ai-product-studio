"""机会解决方案树（Application 层）：Teresa Torres OST。

结果(outcome) → 机会(opportunity) → 方案(solution) → 实验(experiment)。
方案候选用确定性模板按 aspect 生成（结合安克技术原生能力），每个方案附实验。
"""
from __future__ import annotations

from typing import Dict, List

from anker_studio.common.models import (
    Experiment,
    Opportunity,
    OpportunityNode,
    OpportunitySolutionTree,
    SolutionNode,
)

# 按 aspect 给出"技术/模式/流程"三类候选方案模板（体现区别于常规方案）
SOLUTION_TEMPLATES: Dict[str, List[str]] = {
    "降噪 ANC": [
        "端侧自适应降噪：基于 Thus 类存算一体芯片做场景识别 + 个性化 ANC 曲线（技术原生）",
        "降噪强度随环境噪声实时无级调节，并对人声选择性透传（流程创新）",
    ],
    "通话质量": [
        "多麦克风 + 骨传导融合的端侧人声分离，强风/嘈杂环境保持清晰（技术）",
        "通话前自动环境检测并提示最佳麦克风模式（流程）",
    ],
    "连接稳定性/多点": [
        "多点连接 + 基于使用习惯的智能优先级切换（模式创新）",
        "连接异常自愈：断连自动重连并在 App 给出诊断（流程）",
    ],
    "续航": [
        "端侧 AI 按使用场景动态调度功耗，标称续航与真实续航对齐（技术）",
        "电量预测与「今天够不够用」提醒（模式）",
    ],
    "音质": [
        "听力轮廓个性化 EQ，开箱 60 秒完成校准（技术）",
        "基于内容类型(播客/音乐/游戏)自动切换音画策略（流程）",
    ],
    "佩戴舒适度": [
        "AI 入耳贴合检测 + 多尺寸耳塞推荐，降低长时间佩戴疲劳（流程）",
    ],
    "App 体验": [
        "App 内嵌 AI 助手，用自然语言调音与排障（模式）",
    ],
    "价格/价值": [
        "把高价值的端侧 AI 能力下放到中端价位，重塑性价比心智（模式）",
    ],
    "耐用性": [
        "关键部件可靠性前置验证 + 质保流程透明化（流程）",
    ],
}


def _solutions_for(aspect: str) -> List[SolutionNode]:
    nodes: List[SolutionNode] = []
    for tmpl in SOLUTION_TEMPLATES.get(aspect, [f"针对「{aspect}」的差异化方案"]):
        nodes.append(
            SolutionNode(
                statement=tmpl,
                rationale=f"直接回应「{aspect}」的高机会分痛点。",
                experiments=[
                    Experiment(
                        statement=f"对「{aspect}」改进做 A/B 偏好测试",
                        assumption="目标用户愿意为该改进支付溢价/给更高 NPS",
                        method="合成用户面板 + 真实小样本盲测",
                    )
                ],
            )
        )
    return nodes


def build_ost(outcome: str, opportunities: List[Opportunity], top_n: int = 5) -> OpportunitySolutionTree:
    nodes: List[OpportunityNode] = []
    for opp in sorted(opportunities, key=lambda o: o.opportunity_score, reverse=True)[:top_n]:
        nodes.append(
            OpportunityNode(
                opportunity_id=opp.id,
                statement=opp.statement,
                opportunity_score=opp.opportunity_score,
                solutions=_solutions_for(opp.aspect),
            )
        )
    return OpportunitySolutionTree(outcome=outcome, opportunities=nodes)
