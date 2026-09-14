# 测试用例 — `engines.decision_maker`

**包：** `core.engines.decision_maker`  
**版本：** `0.9.0`  
**本文件位置：** `core/engines/decision_maker/__test__/`

---

## Scope

验证决策者会话引擎：时钟只在买入日暂停、人选股数过资金层硬尺、as-of 不含未来、存档续开、REPL 短命令。

## 边界

**负责**

- `DecisionEngine` / `DecisionStore` / `DecisionTimeline` / `DecisionBroker` / `DecisionRepl` 包内行为

**不负责**

- `Strategy` 公开 Facade（见模块根 `__test__/test_api.py`）
- CLI 缩写解析（见 `core/infra/cli/user/__test__`）
- 连 DuckDB 的现场 K 线 / 名称查找

**允许的测试类型（本目录）：** `unit`

---

## Scenario：会话时钟与成交

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_pauses_on_first_buy_date` | `test_decision_maker.py` | 开局停在第一笔买入日 |
| `test_asof_stats_exclude_future_exits` | `test_decision_maker.py` | as-of 胜率不含未到期机会 |
| `test_opportunity_list_uses_per_ticker_asof` | `test_decision_maker.py` | 机会列表胜率按标的 as-of，不是全策略同一数字 |
| `test_pick_done_reset_and_lot_error` | `test_decision_maker.py` | 手数校验、覆盖草稿、done/reset |
| `test_next_requires_done_empty_means_skip` | `test_decision_maker.py` | 空仓 next 跳过买入、结算出场 |
| `test_buy_then_exit_log_then_next_decision` | `test_decision_maker.py` | 买入后下一抉择日前打出场日志 |
| `test_same_day_settles_exits_before_new_buys` | `test_decision_maker.py` | 同日先卖后展示新机会 |
| `test_max_portfolio_size` | `test_decision_maker.py` | 组合上限在 pick 时拒绝 |
| `test_cash_rejected_at_pick` | `test_decision_maker.py` | 现金不足在 pick 时拒绝 |
| `test_complete_writes_report_without_overwriting_id` | `test_decision_maker.py` | 走完写报告且不复用 dm_id |
| `test_attach_ambiguous_unfinished` | `test_decision_maker.py` | 多局未完成须指定 session |
| `test_resume_same_id_after_quit` | `test_decision_maker.py` | 同 id 续开草稿 |
| `test_holdings_show_declared_goals_not_future_date` | `test_decision_maker.py` | holdings 目标不含未来日 |
| `test_info_arg_parse` | `test_decision_maker.py` | info 参数解析 |
| `test_repl_pick_and_quit` | `test_decision_maker.py` | REPL 选股并 quit 存档 |
| `test_broker_rejects_non_lot` | `test_decision_maker.py` | broker 拒绝非整手 |
