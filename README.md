# Anker AI 原生产品定义系统（AI-Native Product Definition Studio）

> 2026 AI 先锋未来人才大赛 · 安克创新命题参赛作品
>
> 命题：*"假设你要为安克设计一款创新产品，让 AI 做你的超级智囊、用户替身、行业专家——用这种新方法从头做一次产品设计与定义，比比看和靠经验拍脑袋有什么本质不同？"*

本项目不是一份 PPT 方案，而是一套**真实可运行、数据可溯源、可评测**的多智能体系统：把安克内部真实的产品方法论平台 **JML / BEES / AMI** 做成 **AI 原生版**，让 AI 扮演超级智囊 / 用户替身 / 行业专家，端到端从**真实用户评论**跑出一份产品提案（PR/FAQ），并用一个**可量化的对比实验**回答命题——AI 驱动相较经验驱动到底"本质不同"在哪。

---

## 1. 它做了什么（一次运行的产出）

输入一句 brief，系统自动完成：

1. **用户洞察（AI 原生 JML）**：对真实评论做确定性 ABSA → ODI 机会评分 → 机会解决方案树。
2. **市场/竞品（AI 原生 AMI / 超级智囊）**：对每个竞品做 ABSA，推导其短板与"白空间机会"，叠加行业趋势（Agentic RAG）。
3. **概念生成（产品经理，双路径）**：① VOC 驱动（从真实痛点反推）+ ② 第一性原理/技术原生（从端侧 AI / Thus 芯片能力正推）。
4. **用户替身（合成用户面板）**：按真实评论聚类成 OCEAN 画像人群，**假设盲**访谈挑战方案。
5. **行业专家**：技术 / BOM / 供应链 / 合规可行性 + Reflexion 批判。
6. **决策官**：NPS 预测 + GO / NO-GO + 可审计 DecisionRecord（HITL 闸口）。
7. **产出**：Working Backwards **PR/FAQ** 提案 + 可行性 + 决策 + （可选）概念图/口播。
8. **评测 & 对比**：Rubric（groundedness/faithfulness/覆盖率…）+ **AI 驱动 vs 经验驱动**量化对比表。

**样本数据下的一次真实运行结果**（`docs/generated/运行报告.md`）：

| 维度 | A 经验驱动 | B AI 原生 |
|---|---|---|
| 命中真实痛点率 | 33% | **100%** |
| 证据引用数 | 0 | **56** |
| 已验证假设数 | 0 | **4** |
| 预测 NPS | -29 | **+1**（Δ +30） |

> 经验驱动凭直觉押"音质/续航/性价比"，但真实数据显示机会分最高的痛点其实是**连接稳定性/多点、佩戴舒适度、App 体验**——这正是"拍脑袋"的系统性盲区。

---

## 2. 为什么这样设计（读懂安克）

- 安克 2023 起 **All in AI**，已建 **AIME 平台（300+ Agent，含 VOC 洞察/需求生成）**，并用 **JML / BEES / AMI** 三大平台 + **NPS** 做产品定义。本系统就是这三平台的 AI 原生版。
- CIO 龚银点出张力："产品定义每个环节都能融入 AI"，但"AI 创新很大程度是**技术原生驱动**创造新体验，而非完全基于传统用户洞察"，且企业场景需要**确定性**（不能有幻觉）。
  - → 方法论做成**双路径**（VOC 驱动 + 技术原生）。
  - → 架构做成 **确定性核心（ABSA/统计/规则产出数值）+ LLM 增强（叙述/角色扮演/批判）**，并**强制逐字引用校验**，把"大模型不确定性"关进可审计的笼子。

---

## 3. 架构（四层 + StateGraph 编排）

```
starter/         CLI、FastAPI（入口，只装配不写业务）
application/      graph 编排 / agents 五角色 / platforms(jml,bees,ami) / methodology(odi,ost,working_backwards) / evaluation / baseline
infrastructure/   llm 网关(MiniMax/offline) / data(加载/下载/连接器) / rag(BM25+TFIDF) / nlp(ABSA词典) / assets(mmx) / observability(trace)
common/           Evidence 等 Pydantic 模型 / 配置 / 日志 / 工具注册 / 引用校验
```

工作流（LangGraph 风格状态图，决策闸前 `interrupt_before`）：

```
voc → think_tank → pm → users → expert → decision ─(条件)→ output
                         ▲────────────────────────────┘ 未达 GO 且有迭代预算则回到 pm
```

---

## 4. 快速开始

### 4.1 离线确定性模式（零网络、可复现，推荐先跑）

```bash
cd anker-ai-product-studio
python3 -m pip install -r requirements.txt          # 仅需 pydantic/loguru/dotenv/fastapi/uvicorn
python3 data/make_sample.py                          # 生成样本评论数据集
PYTHONPATH=backend python3 -m anker_studio.starter.cli run
# 产物：docs/generated/运行报告.md、开题报告_自动生成.md；trace：runs/
```

### 4.2 可视化工作台（FastAPI + 浏览器）

```bash
PYTHONPATH=backend python3 -m uvicorn anker_studio.starter.api:app --port 8000
# 打开 http://localhost:8000，点"运行工作流"，实时看每个 Agent 节点点亮 + 全部产物
```

### 4.3 接入 MiniMax M3（增强叙述/可做跨模型 CR）

```bash
cp .env.example .env   # 填 MINIMAX_API_KEY，设 ANKER_LLM_PROVIDER=minimax
```

### 4.4 用真实 Amazon 评论（替换样本）

```bash
python3 -m pip install datasets
PYTHONPATH=backend python3 -m anker_studio.infrastructure.data.amazon_reviews --max-per-brand 800
# 自动按品牌(soundcore/Bose/Sony/Samsung/Apple)筛 Amazon Reviews 2023 落到 data/processed/
```

---

## 5. 工程规范（对标大厂 AIGC，"企业级 vs 玩具"的分水岭）

对标美团《用 Agent 评测思路管理 AI Coding（31 万行重构）》的 **"人人对齐 → 人机对齐"**：

- **AI Rule（always-on）**：`.cursor/rules/` 强制四层架构、Pydantic、loguru、`@tool` 读写分离、**强制引用纪律**。
- **Skill（渐进式）**：`skills/` 沉淀 VOC、Working Backwards 的 SOP。
- **Pre-PR 自查**：`python3 scripts/pre_pr_check.py`（四层架构/日志/类型/异常规范校验）。
- **跨厂商对抗 CR**：`python3 scripts/cross_model_review.py <path>`（MiniMax M3 按规范审查）。
- **可观测**：每个节点 trace 落 `runs/*.jsonl`，前端实时可视化。

---

## 6. 目录

| 路径 | 内容 |
|---|---|
| `backend/anker_studio/` | 四层架构后端（核心） |
| `frontend/` | 零依赖可视化工作台（FastAPI 托管） |
| `data/` | 样本生成 + 真实数据下载脚本 |
| `docs/` | 方法论白皮书 / 对比报告 / 开题报告 / 引用清单 / 自动生成报告 |
| `skills/` `.cursor/rules/` `scripts/` | 工程规范层 |

详见 [docs/methodology_whitepaper.md](docs/methodology_whitepaper.md) 与 [docs/references.md](docs/references.md)。
