# Analysis — 用户指南

**模块：** `modules.analysis` · **版本：** `0.1.1`

**最低支持核心版本：** `>=0.5.0`

`Analysis` 是纯数学计算工具箱——给对齐好的数字列，输出分桶、相关性、回归等结构化结果。  
相关：[README.md](../README.md) · [API.md](../API.md) · [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 功能总览

- **分桶：** `Analysis.Classical.quantile_buckets` — 按因子分位切桶，看每桶胜率与 ROI
- **相关：** `Analysis.Classical.spearman_correlation` — 两列秩相关
- **回归：** `logistic_win` / `ols_weighted_roi` — 多元解释是否盈利或 ROI
- **对照：** `compare_run_summaries` — 两次 run 的 settings/capture 差分
- **ML（可选）：** `Analysis.ML.xgb_*` — 需安装 `xgboost`；无库时返回 `skipped`

战役侧读数值指标常用 `Analysis.Classical.coerce_float`（见 strategy analyzer `metrics`）。

## 配置说明

无用户 settings；样本量阈值由各 API 的 `min_samples` / `min_bucket_size` 参数控制。

## 常见使用方式

### 场景 1：因子分桶

1. 在调用方筛好等长的 `values`、`outcomes_roi`、`outcomes_is_win`
2. 调 `Analysis.Classical.quantile_buckets(..., min_bucket_size=30)`
3. 检查 `status`；为 `ok` 时消费 `buckets` 列表

### 场景 2：两列相关性

1. 准备等长浮点序列 `x`、`y`
2. 调 `Analysis.Classical.spearman_correlation(x, y)`
3. 读 `rho` 与 `p_value`

## 常见坑

- **长度不一致：** 多数 API 返回 `status: skipped`、`reason: length_mismatch`
- **样本过少：** 提高 `min_bucket_size` 或 `min_samples` 会导致 `insufficient_samples`
- **ML 未安装：** `xgboost` 缺失时 ML 入口不会抛错，检查返回的 `reason: missing_dependency`
- **勿 deep-import：** 只 `from core.modules.analysis import Analysis`，不要 import `core.classical.*`

## 与 strategy 的分工

analyzer 负责读产物、选 outcome 列、写报告句子；本模块只接收已清洗的列向量。