## 🧩 Investment 类逻辑流程图（文字版）

```
[创建阶段]
 └── __init__()
     ├── 初始化基本变量（start_record_ref, settings, strategy_class 等）
     ├── 调用 _create(settings)
     │    ├── _set_up_content()
     │    │   └── 初始化基础内容，如 purchase_price、start_date 等
     │    ├── _set_up_amplitude_tracking()
     │    │   └── 初始化最高/最低价追踪
     │    └── _set_up_targets(settings)
     │        ├── 初始化 take_profit 目标 (非自定义)
     │        ├── 初始化 stop_loss 目标 (非自定义)
     │        └── 初始化 expiration（如果启用）

[运行阶段]
 └── is_completed(record_of_today)
     ├── _update_amplitude_tracking()
     │   └── 更新最高/最低价与幅度
     ├── _check_targets()
     │   ├── 检查 take_profit 目标是否达成
     │   │   └── 达成则更新 remaining_ratio、触发 action
     │   ├── 检查 stop_loss 目标（含 protect_loss / dynamic_loss）
     │   └── 所有目标完成时 → return True 并触发 settle()
     ├── 检查 expiration 是否到期
     │   └── 到期则调用 settle_by_expiration()
     └── 若均未完成 → return False

[目标触发阶段]
 └── _trigger_actions()
     ├── 若目标带 action = set_protect_loss → _enable_protect_loss()
     │   └── 创建 protect_loss target 并激活
     ├── 若目标带 action = set_dynamic_loss → _enable_dynamic_loss()
     │   └── 创建 dynamic_loss target 并激活

[结算阶段]
 ├── settle(record_of_today, is_open=False)
 │   ├── 计算每个完成目标的 weighted_profit
 │   ├── 汇总 overall_profit & ROI
 │   ├── 判断结果 (WIN / LOSS / OPEN)
 │   ├── 计算持续时间 duration_in_days
 │   └── 打印日志信息
 └── settle_by_expiration()
     ├── 创建 EXPIRED target
     ├── 归零 remaining_ratio
     └── 调用 settle()