InvestmentTarget
│
├── __init__(target_type, start_record, stage, extra_fields)
│   ├─ 调用 _validate_stage(stage)
│   ├─ 记录 target_type / is_achieved=False
│   ├─ 保存 start_record_ref
│   ├─ 初始化 tracker:
│   │   ├─ last_updated_date = start_record['date']
│   │   ├─ stage = stage
│   │   └─ extra_fields = extra_fields
│   ├─ 初始化 content:
│   │   ├─ name / target_type / sell_price=0 / sell_date=''
│   │   ├─ sell_ratio / profit / weighted_profit / profit_ratio
│   │   └─ target_price=0
│   ├─ 若 stage 中存在 ratio → 计算 target_price = start_price * (1 + ratio)
│   ├─ 若 close_invest=True → sell_ratio=1.0，否则读取 stage['sell_ratio']
│   └─ 初始化完成
│
├── _validate_stage(stage)
│   ├─ 检查 stage 必须包含 'name'
│   ├─ 必须包含 'sell_ratio' 或 'close_invest'
│   ├─ 若目标类型为 TAKE_PROFIT / STOP_LOSS → 必须包含 'ratio'
│   └─ 否则抛出 ValueError
│
├── create_stage(name, target_settings)
│   ├─ 从 target_settings 读取 ratio / sell_ratio / close_invest
│   ├─ 构建标准化 stage 字典：
│   │   { 'name': name, 'ratio': ..., 'sell_ratio': ..., 'close_invest': ... }
│   └─ 返回 stage，用于批量生成目标阶段配置
│
├── is_complete(record_of_today, remaining_investment_ratio)
│   ├─ 若 is_achieved=True → 返回 (False, remaining_investment_ratio)
│   ├─ 若 remaining_investment_ratio <= 0 → 返回 (False, remaining_investment_ratio)
│   ├─ 若 record_of_today.date ≤ tracker['last_updated_date'] → 返回 (False, remaining_investment_ratio)
│   ├─ 更新 tracker['last_updated_date'] = record_of_today['date']
│   ├─ 获取 close_price 与 target_price
│   ├─ 判断达成条件：
│   │   ├─ TAKE_PROFIT → close_price ≥ target_price
│   │   └─ STOP_LOSS → close_price ≤ target_price
│   ├─ 若未达成 → 返回 (False, remaining_investment_ratio)
│   ├─ 若达成：
│   │   ├─ 计算 sell_ratio = calc_sell_ratio(remaining_investment_ratio)
│   │   ├─ 调用 settle(record_of_today, sell_ratio)
│   │   └─ 返回 (True, remaining_investment_ratio - sell_ratio)
│
├── is_dynamic_loss_complete(record_of_today, remaining_investment_ratio)
│   ├─ 若已完成或剩余持仓<=0 → 返回 (False, remaining_investment_ratio)
│   ├─ 若日期 ≤ last_updated_date → 返回 (False, remaining_investment_ratio)
│   ├─ 更新 last_updated_date
│   ├─ 若 price_today < target_price：
│   │   ├─ 计算 sell_ratio = calc_sell_ratio(remaining_investment_ratio)
│   │   ├─ 调用 settle(record_of_today, sell_ratio)
│   │   └─ 返回 (True, remaining_investment_ratio - sell_ratio)
│   ├─ 否则：
│   │   ├─ 计算 new_target_price = price_today * (1 + stage['ratio'])
│   │   ├─ 若 new_target_price > 原 target_price → 更新 content['target_price']
│   │   └─ 返回 (False, remaining_investment_ratio)
│
├── calc_sell_ratio(remaining_investment_ratio)
│   ├─ 若 close_invest=True → 返回 remaining_investment_ratio（全部卖出）
│   ├─ 否则取 content['sell_ratio']
│   ├─ 若 sell_ratio > remaining → 截断为 remaining
│   └─ 返回最终卖出比例
│
├── settle(record_of_today, sell_ratio)
│   ├─ 若已完成 → 直接返回 self
│   ├─ 否则：
│   │   ├─ 标记 is_achieved=True
│   │   ├─ 记录 sell_price / sell_date
│   │   ├─ 写入 sell_ratio
│   │   ├─ 计算 profit = sell_price - purchase_price
│   │   ├─ weighted_profit = profit * sell_ratio
│   │   ├─ profit_ratio = profit / purchase_price
│   │   ├─ 若 target_price=0（如过期目标）→ 设为买入价
│   │   ├─ 若存在 extra_fields → 写入 content['extra_fields']
│   └─ 返回 self
│
├── has_actions()
│   └─ 若 stage 中定义了 actions 列表 → 返回 True
│
├── get_actions()
│   └─ 返回 stage['actions'] 列表（若存在）
│
├── get_start_record() / set_start_record(record)
│   └─ 获取或更新起始买入记录
│
└── to_dict()
    └─ 返回 self.content（用于保存、序列化、报告输出）
