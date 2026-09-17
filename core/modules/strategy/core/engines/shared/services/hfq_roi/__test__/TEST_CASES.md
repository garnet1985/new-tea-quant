# 测试用例 — `engines.shared.services.hfq_roi`

**包：** `core.engines.shared.services.hfq_roi`  
**版本：** `0.9.0`  
**本文件位置：** `core/engines/shared/services/hfq_roi/__test__/`

---

## Scope

验证后复权 ROI 与同股市值：入场分母非法、缺现价、送转后因子已折进 hfq。

## 边界

**负责**

- `HfqRoi.ratio` / `HfqRoi.is_target_hit` / `HfqRoi.cash_profit` / `HfqRoi.mark_value`

**不负责**

- K 线装载、手续费、决策者时钟

**允许的测试类型（本目录）：** `unit`

---

## Scenario：100→120

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_hfq_roi_is_current_over_entry_minus_one` | `test_hfq_roi.py` | 12/10 − 1 = 20% |
| `test_hfq_roi_rejects_non_positive_or_bad_prices` | `test_hfq_roi.py` | 分母或现价不合法 → 0 |
| `test_split_leaves_hfq_roi_flat_when_factor_absorbs_it` | `test_hfq_roi.py` | 因子吸收送转后 ROI 为 0 |
| `test_cash_profit_and_mark_value_follow_roi` | `test_hfq_roi.py` | 钱 = 股数 × raw × ROI |
| `test_hfq_target_hit_uses_price_not_floaty_roi` | `test_hfq_roi.py` | 触发用价格比较；`ratio>0` 向上、`ratio<=0` 向下（含回落到成本） |
