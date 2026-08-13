# 测试用例 — `modules.backtest_engine`

**模块：** `modules.backtest_engine`  
**覆盖版本：** `0.4.0`

## Scope

验证门面 `BacktestEngine` 与 contracts 公开逻辑（对齐 `API.md`）。

| 文件 | 说明 |
|------|------|
| `test_api.py` | 公开 API 契约（`force_run`）：Mode、`run` / `entity_based` / `slice_based`、Timeline、`RunCallbacks` |

内部 planner / executor / probe 等实现测仍放在同目录其它 `test_*.py`，**不纳入本公开索引**（以各 `test_*.py` 为准）。
