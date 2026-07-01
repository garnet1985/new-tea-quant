# slice_based 流程
#
# resolver/calendar.py → 解析 open_dates / backtest_calendar
# resolver/jobs.py     → 构建 bulk job
# pipeline.py          → BacktestEngine.slice_based 调度
# worker.py            → 子进程入口（校验 job 字段）
# compute.py           → on_calendar_asof → holdings → scan
# state/holdings.py    → 单股持仓：force_exit / max_holding
# context/data.py      → DataContext 组装
# context/runtime.py   → 模式 runtime 视图
# context/status.py    → 运行状态
#
# ## session_state（跨开市日策略状态）
#
# 一次 enumerate run 内，由 engine 维护、通过 ctx.calendar["session_state"]
# 传给 on_calendar_asof，策略读写后通过 CalendarAsOfResult.session_state 回传。
#
# 典型键：
#   - period_selected       本 rebalance 周期选中的股票
#   - force_exit_open_date  周期末强制平仓日
#
# ## reader vs compute
#
# 当前：单进程 compute.py（数据加载 + 策略计算）。
# 未来 B3 双进程时再拆 reader.py（按 slice 预加载 → 队列）。
