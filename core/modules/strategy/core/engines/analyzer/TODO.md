# analyzer — TODO

回测闭环最后一环：**解释这一次 version、这一层 step** 的 inputs 与 outputs 如何共变。  
编排与产物在 **本包**；统计/ML **原语** 在 `modules.analysis`（无业务、无 I/O）。

对外入口：`Strategy.analyze` / `Strategy.maybe_analyze_after_simulate` / CLI `sa`。

---

## 实施四步（按顺序，勿跳）

| 步 | 内容 | 状态 |
|----|------|------|
| **1** | **文档与 TODO**（本文 + `modules/analysis/TODO.md`） | 完成 |
| **2** | **AttributionPipeline + stages**；需 `analysis` 的 stage 先接 **空函数/占位** | 完成 |
| **3** | **填充 `modules.analysis`** — univariate + multivariate 完成；run_comparison / ml 仍 stub | 完成 |
| **4** | **Report 组装**（`scope_note` / `hints_for_ui`、副作用说明；BFF 展示另说） | 完成 |

---

## 已拍板架构

```text
simulate 成功
    → AnalyzerPipeline.run(store)          # strategy · analyzer
         ├─ Collector → source.json       # 已完成
         ├─ DecisionSpaceStage             # 已完成（report.py 前半）
         └─ AttributionPipeline           # 第二步起
              ├─ UnivariateStage          → analysis.quantile_buckets / spearman
              ├─ MultivariateStage       → analysis.logistic / ols（占位）
              ├─ RunComparisonStage      → analysis.compare_runs（占位）
              └─ MLStage                   → analysis.xgb + shap（占位，后期）

modules/analysis/                         # 无 version 路径、不读 ArtifactStore
    纯函数：table in → 统计 struct out
```

| 层 | 位置 | 负责 |
|----|------|------|
| 业务 Pipeline | `strategy/engines/analyzer/` | 读产物、step 配置、门槛、写 `report.json` |
| 统计/ML 原语 | `modules/analysis/core/` | 分桶、相关、回归、XGBoost（后期） |
| 因子研究 | 未来 `factor` 模块 | IC / 滚动 / 全市场 — **不是本 Pipeline** |

**双轨归因（大方向）**

- **classical**：分桶 → 多元回归 → run 对照
- **ml**：XGBoost + SHAP（后期，同 `analysis` 模块）

先做 **classical · univariate**（enum）。

---

## 归因的产品意义（固定文案来源）

> 对 **这一次 run、这一层 step**，说明已落盘 inputs（capture + 声明 + 引擎 outcome）与结果 **如何共变**，帮助用户决定 **改哪个旋钮、是否重跑**。

**不是：** 因果证明、未来预测、重复 overall 胜率/净值、全市场因子 IC。

**情境绑定（in-sample）** 是设计如此：特殊行情下「解释当前 run」仍有效，但不能当 universal 规律 — **第四步 report** 再写 `scope_note` / `hints_for_ui` 防误导。

---

## 当前进度（collect 阶段）

- [x] `ArtifactStore` 读表
- [x] `AttributionInputCollector` → `source.json`
- [x] `decision_space` → `report.json`（manifest + constant/varying）
- [x] `settings.analysis.enabled` + 自动跑（CLI / BFF）
- [x] 测试基线：`rsi_v1_baseline` + capture
- [x] `AttributionPipeline` + stages（第二步）
- [x] `modules.analysis` univariate 统计（第三步）
- [x] `modules.analysis` multivariate 统计（第三步）
- [x] `modules.analysis` run_comparison
- [x] `modules.analysis` ml（XGBoost + SHAP）
- [x] `attribution.classical.*` 写入 report + 用户向说明（第四步）
- [ ] portfolio per-trade join（collect 补全，不挡 enum 算法）
- [ ] BFF 读 analysis 展示（最后做）

---

## 第二步：AttributionPipeline（待实现）

### 目标文件（规划）

```text
analyzer/
  attribution_pipeline.py    # 串联 stages，写 report.attribution
  stages/
    __init__.py
    base.py                  # Stage 协议：run(ctx) -> dict | skipped
    univariate.py            # 调 analysis 占位
    multivariate.py          # 占位 skipped
    run_comparison.py        # 占位 skipped
    ml.py                    # 占位 skipped
  step_config.py             # enum / price / portfolio outcome 字段
```

### Stage 协议（草案）

```python
class AttributionStage(Protocol):
    name: str

    def run(self, ctx: AttributionContext) -> Dict[str, Any]:
        """返回要 merge 进 report 的片段，或 {status: skipped, reason: ...}"""
```

`AttributionContext` 含：`source` dict、`step` str、`decision_space` dict、可选 `baseline_source`。

### 编排顺序

1. `UnivariateStage` — 对所有 `decision_space.capture` 中 `role=varying` 且 numeric 的 key
2. `MultivariateStage` — precondition：`varying_numeric_count >= 2` 且 `N >= 200`（可调）
3. `RunComparisonStage` — precondition：调用方传入 `baseline_version_id`
4. `MLStage` — precondition：后期 + 显式开关

### Step 配置差异（`step_config.py`）

| step | outcome.roi | outcome.win | 额外 |
|------|-------------|-------------|------|
| `enum` | `engine.weighted_roi` | `engine.result` | — |
| `price` | `engine.roi` | `engine.result` | `engine.skip_reason` 汇总 stage（后期） |
| `portfolio` | TBD | TBD | 待 per-trade join |

第二步实现时：**UnivariateStage 调用 `analysis` 空函数**，返回 `{status: "stub"}` 亦可，结构必须先落盘。

---

## 第三步：依赖 `modules/analysis` 的函数

见 [`modules/analysis/TODO.md`](../../../../analysis/TODO.md)。

analyzer 只 import `modules.analysis` 公开 API，不 deep-import `core/`。

---

## 第四步：Report 目标结构（概要）

在现有 `report.json` 上 **追加**（不破坏 `decision_space`）：

```json
{
  "manifest": { "...": "已有" },
  "decision_space": { "...": "已有" },
  "attribution": {
    "classical": {
      "status": "ok | partial | skipped",
      "scope_note": "第四步填写",
      "univariate": { "<capture_key>": { "buckets": [], "correlation": {} } },
      "multivariate": { "status": "skipped", "reason": "..." },
      "run_comparison": { "status": "not_requested" }
    },
    "ml": { "status": "skipped", "reason": "..." }
  },
  "hints_for_ui": []
}
```

第四步再补：`scope_note`、`hints_for_ui`、常量旋钮 → run_comparison 提示。

---

## 验收（第一期 · enum · rsi_v1）

- [ ] `sa --strategy rsi_v1 --step enum` 后 `report.json` 含 `attribution.classical.univariate.rsi`
- [ ] `rsi_length` / `rsi_oversold_threshold` 只在 `decision_space`，不进 univariate
- [ ] 不重复 `overall_report.json` 的总胜率/总 ROI
- [ ] 无 varying capture 的策略（如 bb_v4）→ `attribution.classical.status=skipped` + 明确 reason
- [ ] 单测：`modules/analysis` 分桶/Spearman；`analyzer/stages` 集成测

---

## 明确不做

- 搬 `report_manager` 进 analyzer
- 删 `modules.analysis` 模块
- 在 `ArtifactStore` 里做 join/归因
- IC / 滚动 / 因子挖掘
- 第一期上 XGBoost
