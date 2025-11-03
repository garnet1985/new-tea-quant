InvestmentTarget
│
├── __init__(target_type, record_of_today, stage, extra_fields)
│   ├─ 调用 _validate_stage(stage)
│   ├─ 记录 target_type
│   ├─ 从 record_of_today 获取 purchase_price 与 date
│   ├─ 初始化 tracker = {'last_updated_date': date}
│   ├─ 生成 content:
│   │   ├─ name / ratio / sell_ratio / close_invest
│   │   ├─ purchase_price / target_price
│   │   ├─ start_date / target_type / extra_fields
│   │   └─ end_date='', profit相关字段留空
│   └─ 初始化完成
│
├── create_stage(name, target_settings)
│   ├─ 从 target_settings 中读取 ratio / sell_ratio / close_invest
│   ├─ 返回标准化的 stage 字典
│   └─ 用于批量生成阶段目标
│
├── is_complete(record_of_today, remaining_investment_ratio)
│   ├─ 若 is_achieved=True → 返回 False
│   ├─ 若 remaining_investment_ratio <= 0 → 返回 False
│   ├─ 若 record_of_today.date ≤ tracker['last_updated_date'] → 返回 False
│   ├─ 否则：
│   │   ├─ 获取 close_price 与 target_price
│   │   ├─ 根据 target_type 判断：
│   │   │   ├─ TAKE_PROFIT → close_price >= target_price
│   │   │   └─ STOP_LOSS → close_price <= target_price
│   │   ├─ 若达成：
│   │   │   ├─ 计算 sell_ratio = _calc_sell_ratio(remaining_investment_ratio)
│   │   │   ├─ 调用 settle(record_of_today, sell_ratio)
│   │   │   └─ 返回 (True, remaining_investment_ratio - sell_ratio)
│   │   └─ 否则返回 (False, remaining_investment_ratio)
│
├── _calc_sell_ratio(remaining_investment_ratio)
│   ├─ 若 close_invest=True → 卖出全部剩余
│   ├─ 否则取 self.content['sell_ratio']
│   ├─ 若 sell_ratio > remaining → 截断为 remaining
│   └─ 返回最终卖出比例
│
├── is_dynamic_loss_complete(record_of_today, tracking)
│   ├─ 若已完成 → False
│   ├─ 若日期 ≤ last_updated_date → False
│   ├─ 更新 tracker['last_updated_date']
│   ├─ 若 close_price < target_price → settle() → True
│   └─ 否则 False
│
├── settle(record_of_today, safe_sell_ratio)
│   ├─ 标记 is_achieved=True
│   ├─ 记录 end_date, sell_date, sell_price
│   ├─ 写入 sell_ratio
│   ├─ 计算 profit, weighted_profit, profit_ratio
│   └─ 返回 self
│
└── to_dict()
    └─ 返回 self.content（序列化用）
