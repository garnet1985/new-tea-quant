Investment
│
├── __init__(start_record, opportunity, settings, strategy_class)
│   ├─ 初始化状态标识 is_settled=False
│   ├─ 记录 start_record_ref, opportunity_ref, settings, strategy_class
│   ├─ 初始化 tracker={'last_check_date':'', 'targets_tracking':{}}
│   ├─ 调用 _create(settings)
│
├── _create(settings)
│   ├─ 调用 _set_up_content()
│   ├─ 调用 _set_up_amplitude_tracking()
│   └─ 调用 _set_up_targets(settings)
│
├── _set_up_content()
│   ├─ 从 start_record_ref 获取 purchase_price, purchase_date
│   ├─ 初始化 content:
│   │   ├─ result / roi / overall_profit / duration_in_days 等为空
│   │   ├─ purchase_price / start_date / end_date=None
│   │   ├─ completed_targets = []
│   │   └─ amplitude_tracking = {}
│
├── _set_up_amplitude_tracking()
│   └─ 初始化振幅追踪信息：
│       ├─ max_close_reached: 当前价格、日期、ratio=0
│       └─ min_close_reached: 当前价格、日期、ratio=0
│
├── _set_up_targets(settings)
│   ├─ 初始化 tracker['targets_tracking']:
│   │   ├─ remaining_investment_ratio = 1.0
│   │   ├─ completed = []
│   │   ├─ take_profit = {is_customized, targets[]}
│   │   ├─ stop_loss = {is_customized, targets[], protect_loss{}, dynamic_loss{}}
│   │   └─ expiration = {is_enabled, fixed_period, is_trading_period, time_elapsed, term}
│   │
│   ├─ 若 take_profit.is_customized=False：
│   │   └─ 为每个 stage 创建 InvestmentTarget(TargetType.TAKE_PROFIT)
│   │
│   ├─ 若 stop_loss.is_customized=False：
│   │   └─ 为每个 stage 创建 InvestmentTarget(TargetType.STOP_LOSS)
│   │
│   └─ 若 expiration.fixed_period > 0：
│       ├─ 启用 expiration
│       ├─ 设置 fixed_period / is_trading_period / term / time_elapsed
│       └─ 用于自然期或交易期的到期平仓检测
│
├── is_completed(record_of_today) → (bool, Dict)
│   ├─ 调用 _update_amplitude_tracking(record_of_today)
│   ├─ 调用 _check_targets(record_of_today)
│   │   └─ 若所有目标完成 → settle(record_of_today) → 返回 True, content
│   ├─ 否则检查 expiration：
│   │   └─ 若到期 → settle_by_expiration(record_of_today) → 返回 True, content
│   └─ 否则返回 False, None
│
├── _update_amplitude_tracking(record_of_today)
│   ├─ 若 date <= last_check_date → return
│   ├─ 更新 tracker['last_check_date']
│   ├─ 若 close_price > max_close_reached.price → 更新最高点记录
│   └─ 若 close_price < min_close_reached.price → 更新最低点记录
│
├── _check_targets(record_of_today)
│   ├─ 若投资已完成（_is_investment_complete=True）→ Warning + 返回 False
│   ├─ 检查止盈目标 (take_profit.targets)
│   │   ├─ 遍历 targets:
│   │   │   ├─ 若 target 未达成 → 调用 target.is_complete()
│   │   │   ├─ 若达成：
│   │   │   │   ├─ 更新 remaining_investment_ratio
│   │   │   │   ├─ 添加 completed_targets
│   │   │   │   └─ 触发 _trigger_actions()
│   │   └─ 若 remaining_investment_ratio<=0 → 返回 True
│   │
│   ├─ 检查止损目标 (stop_loss.targets)
│   │   ├─ 调用 _check_stop_loss_targets(record_of_today)
│   │   └─ 若 remaining_investment_ratio<=0 → 返回 True
│   │
│   └─ 否则返回 False
│
├── _check_stop_loss_targets(record_of_today)
│   ├─ 调用 _check_protect_loss()
│   ├─ 调用 _check_dynamic_loss()
│   └─ 调用 _check_normal_stop_loss_targets()
│
├── _check_protect_loss(record_of_today)
│   ├─ 若 protect_loss.is_enabled 且 target 未完成：
│   │   ├─ 调用 target.is_complete()
│   │   ├─ 若完成 → 更新 remaining_investment_ratio 与 completed_targets
│
├── _check_dynamic_loss(record_of_today)
│   ├─ 若 dynamic_loss.is_enabled 且 target 未完成：
│   │   ├─ 调用 target.is_dynamic_loss_complete()
│   │   ├─ 若完成 → 更新 remaining_investment_ratio 与 completed_targets
│
├── _check_normal_stop_loss_targets(record_of_today)
│   ├─ 遍历普通 stop_loss.targets
│   │   ├─ 若 target 未完成 → 调用 target.is_complete()
│   │   ├─ 若完成 → 更新 remaining_investment_ratio、completed_targets、并触发 _trigger_actions()
│
├── _check_expiration(record_of_today)
│   ├─ 若 expiration.is_enabled=False → 返回 False
│   ├─ 若 is_trading_period=True：
│   │   ├─ time_elapsed += 1
│   │   ├─ 若 >= fixed_period → 返回 True
│   └─ 否则：
│       ├─ 根据自然周期计算 elapsed_natural_period
│       └─ 若 >= fixed_period → 返回 True
│
├── _trigger_actions(target, record_of_today)
│   ├─ 若 target 无 actions → return
│   ├─ 遍历 actions:
│   │   ├─ 若 action=SET_PROTECT_LOSS → _enable_protect_loss()
│   │   └─ 若 action=SET_DYNAMIC_LOSS → _enable_dynamic_loss()
│
├── _enable_protect_loss(just_completed_target)
│   ├─ 设置 protect_loss.is_enabled=True
│   ├─ 从 settings.goal.protect_loss 读取配置
│   ├─ 创建新的 InvestmentTarget(TargetType.STOP_LOSS)
│   ├─ extra_fields:
│   │   ├─ triggered_by_target
│   │   └─ triggered_by_action
│   └─ 写入 tracker.stop_loss.protect_loss.target
│
├── _enable_dynamic_loss(record_of_today, just_completed_target)
│   ├─ 设置 dynamic_loss.is_enabled=True
│   ├─ 从 settings.goal.dynamic_loss 读取配置
│   ├─ 创建新的 InvestmentTarget(TargetType.STOP_LOSS)
│   ├─ 设置 start_record 为 just_completed_target 的起始记录
│   └─ 写入 tracker.stop_loss.dynamic_loss.target
│
├── settle_by_expiration(record_of_today)
│   ├─ 生成 extra_fields: expired_term, counting_by, elapsed_time 等
│   ├─ 创建 InvestmentTarget(TargetType.EXPIRED)
│   ├─ 调用 expire_target.settle()
│   ├─ 更新 completed_targets 与 remaining_investment_ratio=0
│   └─ 调用 settle(record_of_today)
│
├── settle(record_of_today, is_open=False)
│   ├─ 若已 is_settled=True → Warning + return
│   ├─ 标记 is_settled=True
│   ├─ 写入 end_date
│   ├─ 若 is_open=True：
│   │   ├─ 创建 OPEN target（卖出剩余持仓）
│   │   └─ 调用 settle 并添加至 completed_targets
│   ├─ 计算 overall_profit（累积 weighted_profit）
│   ├─ 计算 roi = overall_profit / purchase_price
│   ├─ 判断结果类型：
│   │   ├─ ROI>0 → WIN
│   │   ├─ ROI<=0 → LOSS
│   │   └─ is_open=True → OPEN
│   ├─ 计算持续时间 duration_in_days
│   └─ 输出日志（含 icon 与 ROI%）
│
├── to_dict()
│   └─ 返回 self.content
│
└── _is_investment_complete()
    └─ 判断 remaining_investment_ratio <= 0
