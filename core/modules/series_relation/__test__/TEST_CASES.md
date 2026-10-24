# 测试用例 — `modules.series_relation`

**模块：** `modules.series_relation`  
**版本：** `0.1.0`  
**本文件位置：** `__test__/`

---

## Scope

验证 Facade 契约、设定校验、序列发现与加载、归一化与变换、两两指标、产物落盘、滚动稳定性。

**不覆盖**：CLI 排版细节、BFF 路由、UI 渲染。

## 边界

**负责**

- `SeriesRelation.list_infos` / `validate` / `run` 的公开行为
- `settings` 字段约束：`max_series`、`entity`、`transform`
- 归一化、两两相关/滞后/缩放、重叠不足与弱形状的处理
- `summary.json` 等产物写入
- 滚动窗口的稳定性结论

**不负责**

- 真实行情数据质量
- 滞后口径的统计显著性（见 `docs/ARCHITECTURE.md` 已知限制）

**允许的测试类型（本目录）：** `api`、`unit`、`integration`

---

## Scenario：facade_and_settings

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_facade_exports` | `test_api.py` | `MAX_SERIES` 与三个门面方法存在 |
| `test_validate_via_facade` | `test_api.py` | 合法配置经 `validate` 返回 `ok=True` |
| `test_discover_settings` | `test_discovery.py` | 能从 data_source 目录发现候选 |
| `test_validate_ok` | `test_settings.py` | 最小合法配置通过 |
| `test_reject_max_series_in_settings_and_over_limit` | `test_settings.py` | `max_series` 不得写在 settings，且序列数不得超限 |
| `test_per_entity_requires_entity` | `test_settings.py` | 逐股模式必须给 `entity` |

## Scenario：pipeline

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_normalize_zscore_and_index` | `test_pipeline.py` | 两种归一化结果正确 |
| `test_pairwise_core_correlation_lead_and_scale` | `test_pipeline.py` | 相关、滞后、缩放字段齐全且方向正确 |
| `test_weak_shape_marks_lead_scale_untrusted` | `test_pipeline.py` | 形状不符时滞后与缩放标记不可信 |
| `test_pairwise_insufficient_overlap` | `test_pipeline.py` | 重叠不足时 `reliable=False` |
| `test_runner_writes_artifacts` | `test_pipeline.py` | 四个产物文件落盘 |
| `test_rolling_stability_answers_plainly` | `test_pipeline.py` | 滚动结论有平实文本 |

## Scenario：strategy_sim

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_validate_strategy_sim_defaults_version_and_transform` | `test_strategy_sim.py` | 回测产物来源的默认版本与变换 |
| `test_validate_strategy_alias_still_works` | `test_strategy_sim.py` | 旧别名仍可用 |
| `test_reject_portfolio_equity_with_entity_id` | `test_strategy_sim.py` | 组合净值不允许带 `entity_id` |
| `test_apply_transform_returns` | `test_strategy_sim.py` | 收益率变换正确 |
| `test_load_portfolio_equity_and_price_cum` | `test_strategy_sim.py` | 读取组合净值与价格累计 |
| `test_load_missing_layer_hard_fails` | `test_strategy_sim.py` | 缺层直接失败而非静默降级 |
| `test_runner_with_strategy_sim` | `test_strategy_sim.py` | 端到端跑通并落盘 |
