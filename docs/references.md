# 参考资料与引用清单

> 本项目的方法论与工程实践均有出处。分为：方法论、AI 工程/多智能体、合成用户、数据、安克企业资料、工程规范。

## 一、产品方法论
- Amazon **Working Backwards / PR-FAQ**：先写新闻稿与 FAQ 的产品定义法。allthingsdistributed.com；《Working Backwards》(Colin Bryar & Bill Carr)。
- Teresa Torres，**Opportunity Solution Tree** / Continuous Discovery Habits（producttalk.org）。
- Anthony Ulwick，**Outcome-Driven Innovation (ODI)** / Jobs-to-be-Done，《What Customers Want》。
- VOC / **Aspect-Based Sentiment Analysis** 与机会优先级 `Impact = Reach×(Severity+Value+Strategic)`（getthematic、pelin.ai 等）。

## 二、AI 工程 / 多智能体
- **LangGraph**：2026 企业级生产标准（StateGraph / checkpoint / interrupt / 审计）。本项目自研最小引擎对齐其语义。
- **Agentic RAG**：检索→打分→重写→再检索环，确定性脚本校验引用逐字命中（Self-RAG / CRAG 思路）。
- 多智能体 PM 参考：lumen-product-management（18-agent）、muster-ai、ai-product-loop（GitHub）。
- 评测与可观测：LangSmith / Langfuse / Phoenix；任务成功率 + 安全/幻觉率 + 轨迹质量 + 成本四维。

## 三、合成用户 / 用户替身
- **SCOPE**：社会心理 Persona 框架（arXiv 2601.07110），证明仅人口统计 Persona 解释力极低。
- **Grounded Simulation**：基于人格/认知架构 + **假设盲**反谄媚的合成 UX 研究架构。
- **Persona Policies / Persona Generators**（arXiv 2605.12894 / 2602.03545）：演化生成多样、人类相似的合成用户。
- **Synthetic Users** / Listen Labs：多模型 + OCEAN + RAG grounding 的商用合成用户访谈。
- NN/g：合成用户应作为发现协同工具，不替代真实用户终验。

## 四、数据
- **Amazon Reviews 2023**（McAuley Lab, UCSD）：`raw_review_Electronics` + `raw_meta_Electronics`，HuggingFace `McAuley-Lab/Amazon-Reviews-2023`。本项目按 `store` 字段筛 soundcore 与竞品。
- 可选连接器：Google Trends（pytrends）、Web 搜索。
- 离线样本：`data/sample/*.jsonl`（`data/make_sample.py` 可复现生成）。

## 五、安克企业资料（读懂出题意图）
- 安克 2025 年报（深交所 300866）：营收 305.14 亿；三大产品线；研发投入 28.93 亿；JML/BEES/AMI、NPS。
- CIO 龚银专访（InfoQ）：All in AI、AIME 平台（300+ Agent，含 VOC 洞察/需求生成）、"确定性 vs 不确定性"、"AI 平台过时即重构"。
- CEO 阳萌访谈：第三类公司、浅海→深海、看十年想三年做一年。
- 技术原生：**Thus™ 芯片**（NOR Flash 存算一体 CIM，算力 +150x）、soundcore Liberty 5 Pro、eufy Edge Agent。
- 竞品 AI 音频策略：Bose CustomTune、Sony Precise Voice Pickup、Samsung AI Live Translate、Apple AirPods 助听。

## 六、工程规范（对标大厂 AIGC）
- 美团技术团队《用 Agent 评测思路管理 AI Coding —— 31 万行代码 AI 重构的实践》（tech.meituan.com, 2026-05-07）：
  "人人对齐 → 人机对齐"、AI Rule（always 加载）、渐进式 Skill、四层架构（Starter/Application/Infrastructure/Common）、
  Pre-PR 自查、高阶模型审低阶 + 跨厂商模型对抗 CR、Human-in-the-loop 测试 SOP。
- 美团代码风格：Pydantic + loguru + 完整类型注解 + `@is_tool(READ/WRITE)` 读写分离 + 写操作两步确认。

> 说明：样本数据为"合成但贴近真实"的可复现演示数据；真实运行请用上文 Amazon Reviews 2023 下载脚本。所有由系统输出的量化结论均可追溯到具体 `evidence_id`。
