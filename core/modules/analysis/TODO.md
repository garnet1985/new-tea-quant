# analysis — TODO（统计/ML 工具箱）

**角色：** 无业务、无 I/O、不读 `simulations/`、不知道 enum/price/portfolio。  
**消费者：** `strategy/engines/analyzer` 的 AttributionPipeline stages。

旧设计里「独立 Facade 读产物」**不再采用**；`Analysis` 类暂保留占位，行为 API 以 **namespace 函数** 或 **`Analysis.Stats`** 形式从本模块导出（第二步定名）。

---

## 实施四步（与 analyzer 对齐）

| 步 | 本模块工作 | 状态 |
|----|------------|------|
| **1** | 本文档 + API 草案 | 进行中 |
| **2** | `core/` 下 **空函数/stub**，签名固定，返回 `{status: "stub"}` | 未开始 |
| **3** | **实现** classical 统计（univariate 优先） | 未开始 |
| **4** | （analyzer 侧 report 文案；本模块不加业务句子） | — |

---

## 模块边界

| 负责 | 不负责 |
|------|--------|
| 分桶、相关、回归、（后期）XGBoost/SHAP | 读 CSV / `source.json` |
| 纯数据结构 in/out | step 选哪列 outcome |
| 可单测的数学原语 | `scope_note` / UI 文案 |
| 供 factor 等 **未来** 复用同一套数学 | 全市场 IC、滚动验证 |

**依赖原则：** 尽量不依赖 `modules.strategy`。若需 numpy/scipy/sklearn/xgboost，在 **第三步** 按 `requirements` 引入，第二步 stub 不 import 重库。

---

## 规划目录

```text
analysis/
  TODO.md                 # 本文件
  analysis.py             # Facade（占位 → 逐步挂 Stats API）
  contracts.py            # 公开类型（第二步起）
  core/
    __init__.py
    classical/
      univariate.py       # quantile_buckets, spearman
      multivariate.py       # logistic_win, ols_roi（stub）
      run_comparison.py   # compare_numeric_summaries（stub）
    ml/
      xgb_regressor.py    # stub，后期
  __test__/
    test_univariate.py
    ...
```

---

## 公开 API 草案（第二步先 stub）

### classical · univariate

```python
def quantile_buckets(
    values: Sequence[float],
    outcomes_roi: Sequence[float],
    outcomes_is_win: Sequence[bool],
    *,
    n_buckets: int = 5,
    min_bucket_size: int = 30,
) -> Dict[str, Any]:
    """
    返回:
      status: ok | skipped
      reason: str | None
      buckets: [{bucket_id, range, count, win_rate, mean_roi, median_roi}, ...]
    """


def spearman_correlation(
    x: Sequence[float],
    y: Sequence[float],
) -> Dict[str, Any]:
    """
    返回:
      status: ok | skipped
      rho: float | None
      p_value: float | None   # 第三步可选 scipy；stub 可 None
      n: int
    """
```

### classical · multivariate（第三步，第二步 stub）

```python
def logistic_win(
    feature_matrix: Sequence[Sequence[float]],
    feature_names: Sequence[str],
    is_win: Sequence[bool],
    *,
    min_samples: int = 200,
) -> Dict[str, Any]: ...


def ols_weighted_roi(
    feature_matrix: Sequence[Sequence[float]],
    feature_names: Sequence[str],
    roi: Sequence[float],
    *,
    min_samples: int = 200,
) -> Dict[str, Any]: ...
```

### classical · run_comparison（第三步，第二步 stub）

```python
def compare_run_summaries(
    current: Dict[str, Any],
    baseline: Dict[str, Any],
) -> Dict[str, Any]: ...
```

### ml（后期，第二步 stub）

```python
def xgb_feature_importance(
    feature_matrix: Sequence[Sequence[float]],
    feature_names: Sequence[str],
    target: Sequence[float],
    *,
    min_samples: int = 500,
) -> Dict[str, Any]: ...
```

---

## 输入约定（analyzer 组装后传入）

analyzer 从 `source.json` 抽出 **对齐长度的列向量**，不传 `InvestmentRow` 等业务类型。

| 列 | 来源 |
|----|------|
| `values` | `investment.capture[key]` → float |
| `outcomes_roi` | step 配置：`engine.weighted_roi` / `engine.roi` |
| `outcomes_is_win` | `result in ("win", ...)` 由 analyzer 统一映射 |

缺失/非数值：在 **analyzer** 层过滤；`analysis` 函数假定已清洗或收到等长序列。

---

## 第三步实现顺序

1. [ ] `quantile_buckets` — 纯 Python 或 numpy 分位；桶 `< min_bucket_size` 合并或 skip
2. [ ] `spearman_correlation` — 可手写秩相关或 scipy.stats.spearmanr
3. [ ] `logistic_win` / `ols_weighted_roi` — sklearn/statsmodels，门槛：`N/features >= 10`
4. [ ] `compare_run_summaries` — 对比两次 univariate 摘要 / declared diff
5. [ ] `xgb_feature_importance` + SHAP — 第四轨，依赖可选

---

## 测试

- 全在 `analysis/__test__/`，**不读盘**
- 固定小数组断言 buckets 边界、空输入 skipped、常数列 skipped
- analyzer 集成测只验证「调用了 API + report 形状」，不重测数学

---

## 与旧文档的关系

- [README.md](./README.md) / [docs/DESIGN.md](./docs/DESIGN.md) 中「独立 Facade 读产物」「Strategy.analyze 已删除」等表述 **过时**。
- **以本文 + `strategy/engines/analyzer/TODO.md` 为准**；有空再同步 ARCHITECTURE/DESIGN（非第一步阻塞项）。
