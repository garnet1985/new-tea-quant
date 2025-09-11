# HistoricLow 策略配置指南

## 📋 配置文件说明

策略配置位于 `strategy_settings.py` 文件中，包含所有可配置的参数。

## ⚙️ 核心配置参数

### 1. 基础配置
```python
"strategy_name": "HistoricLow",        # 策略名称
"version": "1.0.0",                   # 策略版本
"description": "历史低点策略",          # 策略描述
```

### 2. 数据要求配置
```python
"daily_data_requirements": {
    "min_required_daily_records": 1000,  # 最少需要1000天的数据
    "min_required_years": 3,             # 最少需要3年的数据
}
```

### 3. 历史低点配置
```python
"low_points_ref_years": [1, 3, 5, 8],  # 参考年份：1年、3年、5年、8年
```

**说明**: 策略会基于这些年份的历史数据识别关键低点，用于投资决策。

### 4. 投资范围配置
```python
"invest_range": {
    "upper_bound": 0.10,  # 历史低点上方10%
    "lower_bound": 0.05,  # 历史低点下方5%
}
```

**说明**: 只有在历史低点上方10%和下方5%的范围内才会考虑投资。

### 5. 冻结期配置
```python
"freeze_period": {
    "days": 30,              # 冻结期30天
    "max_touch_times": 1,    # 最多接触1次
}
```

**说明**: 在冻结期内，同一低点最多只能接触1次，避免重复投资。

### 6. 振幅过滤配置
```python
"amplitude_filter": {
    "enabled": True,           # 是否启用振幅过滤
    "min_amplitude": 0.10,     # 最小振幅10%
    "description": "过滤振幅过小的投资机会"
}
```

**说明**: 过滤掉振幅过小的投资机会，提高投资质量。

### 7. 波浪过滤配置
```python
"wave_filter": {
    "enabled": True,           # 是否启用波浪过滤
    "min_wave_days": 30,       # 最小波浪天数
    "description": "确保历史低点后有完整的波浪"
}
```

**说明**: 确保历史低点后有完整的波浪结构，提高投资可靠性。

### 8. 斜率过滤配置
```python
"max_invest_slope": -0.056,  # 最大投资斜率（约-5度）
```

**说明**: 只投资斜率小于-5度的机会，过滤掉过于平缓的走势。

### 9. 凯莉公式配置
```python
"kelly_formula": {
    "enabled": True,                    # 是否启用凯莉公式
    "min_capital_threshold": 200000,    # 最小资金阈值，超过此金额使用凯莉公式
    "base_shares": 500,                 # 基础股数（固定投资时使用）
    "min_kelly_fraction": 0.05,         # 最小凯莉投资比例（5%）
    "max_kelly_fraction": 0.30,         # 最大凯莉投资比例（30%）
    "default_win_rate": 0.5,            # 默认胜率（无历史数据时）
    "default_avg_win": 0.15,            # 默认平均盈利（15%）
    "default_avg_loss": -0.08,          # 默认平均亏损（-8%）
}
```

**说明**: 当资金超过20万时，自动使用凯莉公式进行仓位管理。

### 10. 投资过滤配置
```python
"investment_filter": {
    "enabled": True,           # 是否启用投资过滤
    "min_capital_threshold": 500000,  # 资金小于此金额时启用过滤
    "min_roi_threshold": 0.05,        # 最小收益率阈值（5%）
}
```

**说明**: 当资金小于50万时，只投资预期收益率大于5%的机会。

### 11. 测试模式配置
```python
"test_mode": {
    "test_problematic_stocks_only": False,  # 是否只测试问题股票
    "max_test_stocks": None,                # 最大测试股票数量
}
```

**说明**: 控制模拟测试的范围和规模。

### 12. 黑名单配置
```python
"problematic_stocks": {
    "list": [
        "000546.SZ", "000547.SZ", "000599.SZ",
        # ... 更多问题股票
    ],
    "count": 51,  # 问题股票总数
    "description": "基于最新模拟结果自动更新的黑名单"
}
```

**说明**: 问题股票列表，这些股票在模拟中表现不佳，会被自动识别和排除。

## 🔧 配置调优建议

### 1. 历史低点年份
- **保守策略**: 使用 [3, 5, 8] 年，更注重长期低点
- **激进策略**: 使用 [1, 3, 5] 年，更注重短期低点
- **平衡策略**: 使用 [1, 3, 5, 8] 年，兼顾短期和长期

### 2. 投资范围
- **保守策略**: 上方5%，下方3%
- **激进策略**: 上方15%，下方8%
- **平衡策略**: 上方10%，下方5%

### 3. 过滤条件
- **严格过滤**: 提高振幅阈值到15%，斜率阈值到-10度
- **宽松过滤**: 降低振幅阈值到5%，斜率阈值到-3度
- **平衡过滤**: 保持当前设置

### 4. 凯莉公式参数
- **保守设置**: 最大投资比例20%，默认胜率40%
- **激进设置**: 最大投资比例40%，默认胜率60%
- **平衡设置**: 保持当前设置

## 📊 配置验证

### 1. 参数合理性检查
```python
# 检查配置参数是否合理
def validate_config():
    config = strategy_settings
    
    # 检查投资范围
    assert 0 < config["invest_range"]["upper_bound"] < 1
    assert 0 < config["invest_range"]["lower_bound"] < 1
    
    # 检查凯莉公式参数
    assert 0 < config["kelly_formula"]["min_kelly_fraction"] < 1
    assert 0 < config["kelly_formula"]["max_kelly_fraction"] < 1
    
    # 检查过滤条件
    assert 0 < config["amplitude_filter"]["min_amplitude"] < 1
    assert config["max_invest_slope"] < 0
```

### 2. 配置测试
```python
# 测试配置是否有效
def test_config():
    from app.analyzer.strategy.historicLow.strategy import HistoricLowStrategy
    
    strategy = HistoricLowStrategy()
    # 运行简单测试验证配置
```

## 🚀 配置更新

### 1. 手动更新
直接编辑 `strategy_settings.py` 文件中的配置参数。

### 2. 自动更新
某些配置（如黑名单）会在模拟完成后自动更新。

### 3. 配置备份
建议在修改配置前备份原始配置文件。

## ⚠️ 注意事项

1. **参数依赖**: 某些参数之间存在依赖关系，修改时需要注意
2. **数据要求**: 配置参数需要与数据质量匹配
3. **性能影响**: 某些参数会影响模拟性能，需要平衡
4. **风险控制**: 配置参数直接影响投资风险，需要谨慎调整

## 📞 获取帮助

- 查看完整文档: `README.md`
- 快速开始: `QUICK_START.md`
- 配置示例: `strategy_settings.py`
- 策略逻辑: `strategy.py`

