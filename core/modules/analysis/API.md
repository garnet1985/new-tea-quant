# Analysis API 文档

**模块：** `modules.analysis` · **版本：** `0.1.1`

**最低支持核心版本：** `>=0.5.0`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。

术语见 [glossary.yaml](./glossary.yaml)。概念见 [CONCEPTS.md](./docs/CONCEPTS.md)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。未决选型见 [DECISIONS.md](./docs/DECISIONS.md)。

**公开约定：** 包根仅导出 `Analysis`。统计/ML 原语经 `Analysis.Classical` / `Analysis.ML` namespace 调用。跨模块类型从 [`contracts.py`](./contracts.py) 导入（当前无符号）。实现位于 `core/`，禁止 deep-import。

---

## Analysis

**描述：** 无 I/O 的统计/ML 工具箱门面；业务读盘与报告文案在 `modules.strategy` analyzer。

### Classical

**描述：** 经典统计原语（列画像、分桶、相关、多元回归、两次 run 摘要对照）。

#### summarize_column

`Analysis.Classical.summarize_column(values: Sequence[Any]) -> dict[str, Any]`

- **类型：** `classmethod`（经 `ColumnProfiler.summarize`）
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 判断列是空/常量/变长及数值或文本概要
- **参数：** `values` — 已对齐长度的原始值序列
- **返回值：** `dict` — `role`、`dtype`、`count` 等

#### coerce_float

`Analysis.Classical.coerce_float(value: Any) -> float | None`

- **类型：** `staticmethod`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 把标量安全转为 `float`；无法转换返回 `None`
- **参数：** `value` — 任意标量
- **返回值：** `float | None`

#### quantile_buckets

`Analysis.Classical.quantile_buckets(values, outcomes_roi, outcomes_is_win, *, n_buckets=5, min_bucket_size=30) -> dict[str, Any]`

- **类型：** `staticmethod`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 按因子分位数分桶并汇总每桶 win_rate / ROI
- **参数：** 等长三列序列；`n_buckets`、`min_bucket_size` 控制分桶
- **返回值：** `dict` — `status`（`ok` | `skipped`）、`buckets` 等

#### spearman_correlation

`Analysis.Classical.spearman_correlation(x: Sequence[float], y: Sequence[float]) -> dict[str, Any]`

- **类型：** `staticmethod`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** Spearman 秩相关及近似 p 值
- **返回值：** `dict` — `status`、`rho`、`p_value`、`n`

#### logistic_win

`Analysis.Classical.logistic_win(feature_matrix, feature_names, is_win, *, min_samples=200) -> dict[str, Any]`

- **类型：** `staticmethod`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 无正则逻辑回归：特征对是否盈利的系数与伪 R²
- **返回值：** `dict` — `status`、`coefficients` 等

#### ols_weighted_roi

`Analysis.Classical.ols_weighted_roi(feature_matrix, feature_names, roi, *, min_samples=200) -> dict[str, Any]`

- **类型：** `staticmethod`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** OLS：特征对 ROI 的系数与显著性
- **返回值：** `dict` — `status`、`coefficients`、`r_squared` 等

#### compare_run_summaries

`Analysis.Classical.compare_run_summaries(current: dict, baseline: dict) -> dict[str, Any]`

- **类型：** `staticmethod`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 对比两次归因 run 的 decision_space / coverage 摘要差分
- **返回值：** `dict` — `settings_diff`、`capture_diff`、`has_meaningful_diff` 等

### ML

**描述：** 可选依赖（`xgboost`、`shap`）的梯度提升原语；缺库时返回 `skipped`。

#### xgb_feature_importance

`Analysis.ML.xgb_feature_importance(feature_matrix, feature_names, target, *, min_samples=500) -> dict[str, Any]`

- **类型：** `staticmethod`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** XGBoost 回归 + gain 重要性；可选 SHAP 摘要
- **返回值：** `dict` — `status`、`feature_importance` 等

#### xgb_win_classifier

`Analysis.ML.xgb_win_classifier(feature_matrix, feature_names, is_win, *, min_samples=80, ...) -> dict[str, Any]`

- **类型：** `staticmethod`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** XGBoost 二分类（是否盈利）+ 可选 SHAP / ROC
- **返回值：** `dict` — `status`、`metrics`、`shap_summary` 等

---

## contracts

本版本无公开符号。