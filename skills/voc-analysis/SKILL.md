---
name: voc-analysis
description: 把真实用户评论转成可溯源的痛点/机会洞察（AI 原生 JML）。当需要做 VOC / 用户洞察 / ABSA / 机会评分 / 构建机会解决方案树时使用。
---

# Skill: VOC 用户洞察分析（AI 原生 JML）

## 何时用
- 拿到一批真实评论（目标品牌 + 竞品），需要产出"用户真正的痛点与未满足机会"。

## 标准流程（SOP）
1. **归一 Evidence**：每条评论转成 `Evidence{source_id, brand, rating, text, date}`。
2. **ABSA（确定性核心）**：用领域 aspect 词典 + 情感词典扫描，得到每个 aspect 的提及量(Reach)、负面率(Severity)、代表性引用。
   - 音频域 aspect：降噪ANC / 音质 / 佩戴舒适度 / 通话质量 / 续航 / App体验 / 连接稳定性(多点) / 价格价值 / 耐用性。
3. **机会评分（ODI 风格）**：`opportunity = importance + max(importance - satisfaction, 0)`；并算 `Impact = Reach × (Severity + Value + Strategic)`。
4. **BEES 体验演化**：按时间/版本切片，观察某 aspect 负面率随时间变化（发现"做没做好/退步"）。
5. **机会解决方案树 OST**：结果(提升某品类 NPS) → 机会(高分痛点) → 候选方案 → 实验。
6. **引用校验**：每条机会必须挂 `evidence_ids`，逐字命中校验。

## 输出
`VocReport{ aspects: [AspectInsight], opportunities: [Opportunity], experience_trend: [...], ost: OpportunitySolutionTree }`，全部可溯源。

## 约束
- 数值（提及量/负面率/机会分）必须由确定性算法产出，LLM 只做归纳叙述。
- 禁止杜撰评论；引用必须来自真实 Evidence。
