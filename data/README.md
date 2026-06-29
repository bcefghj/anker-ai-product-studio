# 数据说明

系统加载顺序：**优先 `data/processed/*.jsonl`（真实）→ 否则 `data/sample/*.jsonl`（样本）**。
品牌归类：`soundcore` 为目标品牌；`Bose / Sony / Samsung / Apple` 为竞品（AMI 竞品拆解）。

## 1. 样本数据（随仓库，零网络可复现）

```bash
python3 data/make_sample.py     # 生成 data/sample/{soundcore,Bose,Sony,Samsung,Apple}.jsonl
```

样本是"合成但贴近真实"的英文评论，刻意设置了各品牌在不同 aspect 上的差异（如 soundcore
在连接/多点、App、通话上较弱），用于让 ABSA 产出有意义的机会与竞品白空间。**仅用于演示/复现**。

## 2. 真实数据（Amazon Reviews 2023, McAuley Lab）

```bash
pip install datasets
PYTHONPATH=../backend python3 -m anker_studio.infrastructure.data.amazon_reviews --max-per-brand 800
# 流式读取 raw_meta_Electronics 建立 asin->品牌 映射，再从 raw_review_Electronics 按品牌筛选
# 输出 data/processed/{soundcore,Bose,Sony,Samsung,Apple}.jsonl
```

## 3. 数据字段（统一 Evidence）

每行 JSON：

```json
{"source_id":"soundcore-0001","brand":"soundcore","product":"...","rating":2,
 "text":"The connection keeps dropping ...","date":"2024","helpful_votes":12}
```

加载后归一为 `common/models.py:Evidence`，所有 Agent 只能引用 `source_id`，保证可溯源。
