Investment
│
├── __init__(record_of_today, opportunity, settings, strategy_class)
│     ├── 初始化基本参数与追踪器 self.tracker
│     ├── 调用 _create() 构建投资实例
│     │
│     └── 结构：
│          ├── _set_up_content()             → 初始化基础信息（股票、日期、买入价）
│          ├── _set_up_amplitude_tracking()  → 记录初始最大/最小收盘价
│          └── _set_up_targets()             → 生成止盈 / 止损目标（InvestmentTarget）
│
│
├── is_completed(record_of_today)
│     ├── 更新振幅追踪信息 → _update_amplitude_tracking()
│     ├── 检查止盈/止损目标 → _check_targets()
│     │     ├── 止盈逻辑：
│     │     │     ├── 若自定义 → strategy_class.should_take_profit()
│     │     │     └── 否则循环遍历 take_profit_targets 调用 target.is_complete()
│     │     │
│     │     ├── 止损逻辑：
│     │     │     ├── 若自定义 → strategy_class.should_stop_loss()
│     │     │     └── 否则调用 _check_stop_loss_targets()
│     │     │           ├── _check_protected_loss()  → 检查保护性止损
│     │     │           ├── _check_dynamic_loss()    → 检查动态止损
│     │     │           └── _check_normal_stop_loss_targets() → 检查普通止损目标
│     │     │
│     │     └── 若任何目标完成 → 立即 settle()
│     │
│     ├── 若所有目标未完成 → 检查到期逻辑 _check_expiration()
│     │     ├── 若到期 → settle()
│     │     └── 否则 → 继续持有
│     │
│     └── 返回结果：(is_completed: bool, settled_content: dict | None)
│
│
├── _update_amplitude_tracking(record_of_today)
│     ├── 更新最高价 / 最低价及日期
│     └── 计算当前涨跌幅比率（相对买入价）
│
│
├── _check_stop_loss_targets(record_of_today)
│     ├── _check_protected_loss() → 检查保护性止损是否触发
│     ├── _check_dynamic_loss()   → 检查动态止损（随最高价变动）
│     └── _check_normal_stop_loss_targets() → 检查普通止损目标并执行动作
│
│
├── _trigger_actions(target, record_of_today, settings)
│     ├── 执行目标中定义的动作 actions
│     │     ├── set_stop_loss = 'protected' → 启用保护性止损
│     │     └── set_stop_loss = 'dynamic'   → 启用动态止损
│     └── （后续可扩展更多 action 类型）
│
│
├── _check_expiration(record_of_today)
│     ├── 若开启过期追踪：
│     │     ├── 交易日模式：检查 elapsed_trading_days ≥ fixed_days
│     │     └── 自然日模式：计算日期差 ≥ fixed_days
│     └── 返回是否已到期
│
│
├── settle(record_of_today, is_open=False)
│     ├── 标记已结算 self.is_settled = True
│     ├── 计算：
│     │     ├── 总收益 overall_profit
│     │     ├── ROI (收益 / 买入价)
│     │     ├── 投资结果 result (WIN / LOSS / OPEN)
│     │     └── 持仓天数 duration_in_days
│     └── 写入 content 并记录日志
│
│
├── to_dict()
│     └── 返回当前 content 作为字典（供外部系统或回测存档使用）
│
│
└── 工具函数
      ├── _is_investment_complete() → 判断仓位是否已清空
      ├── _get_sell_ratio(target)   → 计算目标卖出比例
      └── _target_has_actions(target) → 判断目标是否有后续动作