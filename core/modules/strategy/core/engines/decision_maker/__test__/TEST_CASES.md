# 测试用例 — `engines.decision_maker`

**包：** `core.engines.decision_maker`  
**版本：** `0.9.0`  
**本文件位置：** `core/engines/decision_maker/__test__/`

---

## Scope

验证决策者会话引擎：时钟在事件日暂停（机会或仓位变化）、人选股数过资金层硬尺、as-of 不含未来、存档续开、REPL 短命令。

## 边界

**负责**

- `DecisionEngine` / `DecisionStore` / `DecisionTimeline` / `DecisionBroker` / `DecisionRepl` 包内行为

**不负责**

- `Strategy` 公开 Facade（见模块根 `__test__/test_api.py`）
- CLI 缩写解析（见 `core/modules/cli/user/__test__`）
- 连 DuckDB 的现场 K 线 / 名称查找

**允许的测试类型（本目录）：** `unit`

---

## Scenario：会话时钟与成交

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_pauses_on_first_buy_date` | `test_decision_maker.py` | 开局停在第一笔买入日 |
| `test_asof_stats_exclude_future_exits` | `test_decision_maker.py` | as-of 胜率不含未到期机会 |
| `test_asof_stats_ticker_completed_before_decision_day` | `test_decision_maker.py` | D 日该标的胜率只统计 exit_date < D 的已完成枚举 |
| `test_asof_stats_skip_open_lifecycle` | `test_decision_maker.py` | 持仓未归零的枚举行不计 as-of 胜率 |
| `test_opportunity_list_uses_per_ticker_asof` | `test_decision_maker.py` | 机会列表胜率按标的 as-of，不是全策略同一数字 |
| `test_pick_done_reset_and_lot_error` | `test_decision_maker.py` | 手数校验、覆盖草稿、done/reset |
| `test_set_pick_cash_floors_to_lot` | `test_decision_maker.py` | 填金额按手数折成可买股数 |
| `test_next_requires_done_empty_means_skip` | `test_decision_maker.py` | 空仓 next 跳过买入；未持有的出场不停钟 |
| `test_buy_then_exit_log_then_next_decision` | `test_decision_maker.py` | 买入后先停在出场日，再 `next` 到下一机会 |
| `test_same_day_settles_exits_before_new_buys` | `test_decision_maker.py` | 同日先卖后展示新机会 |
| `test_max_portfolio_size` | `test_decision_maker.py` | 组合上限在 pick 时拒绝 |
| `test_cash_rejected_at_pick` | `test_decision_maker.py` | 现金不足在 pick 时拒绝 |
| `test_draft_reserves_cash_across_picks` | `test_decision_maker.py` | 当天多笔草稿合计占用现金，后一笔超出则拒 |
| `test_next_cash_failure_returns_to_picking` | `test_decision_maker.py` | next 现金失败后回到 picking，草稿保留 |
| `test_complete_writes_report_without_overwriting_id` | `test_decision_maker.py` | 出场日停钟后再走完，写报告且不复用 dm_id |
| `test_attach_ambiguous_unfinished` | `test_decision_maker.py` | 多局未完成须指定 session |
| `test_store_remembers_last_session` | `test_decision_maker.py` | meta 记下上次打开的局；删掉后改指剩余最新 |
| `test_same_entity_one_opportunity_per_day` | `test_decision_maker.py` | 同标的同日两笔买入只出示一条 |
| `test_skips_buy_day_when_already_holding_same_entity` | `test_decision_maker.py` | 持仓中跳过同标的第二笔买入日，仍在出场日停钟 |
| `test_holdings_show_declared_goals_not_future_date` | `test_decision_maker.py` | holdings 目标不含未来日 |
| `test_holdings_trading_day_span_matches_expiration_unit` | `test_decision_maker.py` | 持有时长与到期同为交易日 |
| `test_holdings_roi_uses_hfq_not_qfq_over_raw` | `test_decision_maker.py` | 持仓 % 走 hfq ROI，不用前复权收盘 / 不复权买价 |
| `test_partial_take_profit_marks_stage_and_labels_event` | `test_decision_maker.py` | 分档止盈日志写档名；剩余仓位该档标已完成 |
| `test_calendar_journal_records_opps_and_fills` | `test_decision_maker.py` | 日历记机会数与已成交买卖；买入带笔记、卖出不带 |
| `test_buy_note_stays_on_draft_then_trade_and_holdings` | `test_decision_maker.py` | 草稿笔记覆盖/清空后随买入成交和持仓 |
| `test_info_arg_parse` | `test_decision_maker.py` | info 参数解析 |
| `test_repl_pick_and_quit` | `test_decision_maker.py` | REPL 选股并 quit 存档 |
| `test_broker_rejects_non_lot` | `test_decision_maker.py` | broker 拒绝非整手买入 |
| `test_broker_sell_floors_to_lot_until_last` | `test_decision_maker.py` | 中间卖出整手，最后一笔清零股 |
