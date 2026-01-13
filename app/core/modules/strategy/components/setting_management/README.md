# Setting Management 模块

## 📋 概述

Setting Management 模块提供统一的策略设置管理功能，包括：
- **统一验证**：在基类中统一验证 settings 的完整性和可用性
- **按需验证**：只在用的时候进行 validate，但是是第一步
- **错误分级**：Critical（必须修复）和 Warning（可以继续）
- **默认值补充**：自动添加默认值
- **职责分离**：基类负责公共逻辑，子类负责特定组件配置

## 🏗️ 架构设计

### 模块结构

```
setting_management/
├── __init__.py
├── setting_manager.py          # 设置管理器（统一入口）
├── models/
│   ├── __init__.py
│   ├── setting_errors.py      # 错误类型定义
│   ├── base_settings.py       # 设置基类
│   ├── strategy_settings.py    # 主设置类
│   ├── goal_validator.py       # Goal 配置验证器
│   ├── enumerator_settings.py  # 枚举器设置
│   ├── price_factor_settings.py # 价格因子模拟器设置
│   ├── capital_allocation_settings.py # 资金分配模拟器设置
│   └── scanner_settings.py     # 扫描器设置
└── README.md                   # 本文档
```

### 核心类

#### SettingManager
设置管理器（统一入口）

**职责**：
- 加载策略设置（第一步）
- 验证基础设置（Critical）
- 提供组件特定设置的访问接口
- 管理设置的验证状态

**使用方式**：
```python
from app.core.modules.strategy.components.setting_management import SettingManager

# 1. 创建设置管理器
setting_mgr = SettingManager("example")

# 2. 验证基础设置（第一步，必须）
result = setting_mgr.validate_base_settings()
# 如果有 Critical 错误，会抛出 ValueError

# 3. 获取组件特定设置（自动验证）
enumerator_settings = setting_mgr.get_enumerator_settings()
price_factor_settings = setting_mgr.get_price_factor_settings()
capital_allocation_settings = setting_mgr.get_capital_allocation_settings()
```

#### BaseSettings
设置基类

**职责**：
- 加载原始 settings 字典（不验证）
- 提供按需验证方法 `validate_base_settings()`
- 提供公共字段访问方法
- 添加默认值

#### StrategySettings
主设置类

**职责**：
- 继承 `BaseSettings`
- 提供工厂方法创建子 Settings
- 统一验证入口 `validate_and_prepare()`

#### 组件特定设置

- **EnumeratorSettings**：枚举器设置
- **PriceFactorSettings**：价格因子模拟器设置
- **CapitalAllocationSettings**：资金分配模拟器设置
- **ScannerSettings**：扫描器设置

## 📝 使用方式

### 基本使用

```python
from app.core.modules.strategy.components.setting_management import SettingManager

# 1. 创建设置管理器
setting_mgr = SettingManager("example")

# 2. 验证基础设置（第一步，必须）
result = setting_mgr.validate_base_settings()
# 如果有 Critical 错误，会抛出 ValueError

# 3. 获取组件特定设置（自动验证）
enumerator_settings = setting_mgr.get_enumerator_settings()
price_factor_settings = setting_mgr.get_price_factor_settings()
capital_allocation_settings = setting_mgr.get_capital_allocation_settings()

# 4. 访问配置
print(enumerator_settings.use_sampling)  # bool
print(price_factor_settings.sot_version)  # str
print(capital_allocation_settings.initial_capital)  # float
```

### 在组件中使用

```python
# 在 OpportunityEnumerator 中
def run(self, strategy_name: str):
    setting_mgr = SettingManager(strategy_name)
    setting_mgr.validate_base_settings()  # 第一步验证
    
    enumerator_settings = setting_mgr.get_enumerator_settings()
    # 使用 enumerator_settings.use_sampling, max_workers 等

# 在 PriceFactorSimulator 中
def run(self, strategy_name: str):
    setting_mgr = SettingManager(strategy_name)
    setting_mgr.validate_base_settings()  # 第一步验证
    
    price_factor_settings = setting_mgr.get_price_factor_settings()
    # 使用 price_factor_settings.sot_version, use_sampling 等
```

## 🔍 验证规则

### Critical 错误（必须修复）

#### BaseSettings
- `name` 不能为空或 'unknown'
- `data.base_price_source` 不能为空
- `data.adjust_type` 不能为空

#### EnumeratorSettings
- `goal` 配置必须存在（除非 customized）

#### CapitalAllocationSettings
- `initial_capital` 必须 >= 1000
- `allocation.mode` 必须是有效枚举值：["equal_capital", "equal_shares", "kelly", "custom"]
- `allocation.max_portfolio_size` 必须 > 0

#### Goal 配置
- `goal` 不能为空（除非 customized）
- `take_profit.stages` 必须是非空列表（除非 customized）
- `stop_loss.stages` 必须是非空列表（除非 customized）
- 没有 expiration 的情况下，`take_profit` 的 `sell_ratio` 总和必须 <= 1.0

### Warning（可以继续）

#### EnumeratorSettings
- `use_sampling` 未配置时，默认 False

#### PriceFactorSettings
- `sot_version` 配置的版本不存在（默认使用 "latest"）
- `use_sampling` 未配置时，默认 True
- `start_date` / `end_date` 未配置时，使用默认时间范围

#### CapitalAllocationSettings
- `sot_version` 配置的版本不存在（默认使用 "latest"）
- `use_sampling` 未配置时，默认 True
- `fees` 配置缺失时，默认忽略交易费用

#### Goal 配置
- `goal` 配置不完整（例如只有 stop_loss 没有 take_profit）
- `expiration` 缺失（建议配置）

### 默认值

#### BaseSettings
- `data.min_required_records`: 100
- `data.indicators`: {}
- `data.extra_data_sources`: []
- `sampling.strategy`: "continuous"
- `sampling.sampling_amount`: 10

#### EnumeratorSettings
- `use_sampling`: False
- `max_test_versions`: 10
- `max_sot_versions`: 3
- `max_workers`: "auto"

#### PriceFactorSettings
- `sot_version`: "latest"
- `use_sampling`: True
- `start_date`: ""（表示从默认开始日期）
- `end_date`: ""（表示到最新交易日）
- `max_workers`: "auto"

#### CapitalAllocationSettings
- `sot_version`: "latest"
- `use_sampling`: True
- `initial_capital`: 1_000_000.0
- `allocation.mode`: "equal_capital"
- `allocation.max_portfolio_size`: 5
- `allocation.max_weight_per_stock`: 0.3
- `allocation.lot_size`: 100
- `allocation.lots_per_trade`: 1
- `allocation.kelly_fraction`: 0.5
- `output.save_trades`: True
- `output.save_equity_curve`: True
- `fees`: 忽略交易费用（所有费率 = 0）

## 🎯 设计特点

1. **按需验证**：只在用的时候验证，但是是第一步
2. **错误分级**：Critical 和 Warning 区分
3. **默认值补充**：自动添加默认值
4. **分层验证**：基础设置和组件设置分开验证
5. **强可读性**：函数名清晰描述功能
6. **类型安全**：使用 dataclass 和类型提示

## 🔄 验证流程

### 1. 策略初始化阶段
```python
setting_mgr = SettingManager("example")
result = setting_mgr.validate_base_settings()  # 验证基础设置（Critical）
```

### 2. 组件使用阶段
```python
# 枚举器
enumerator_settings = setting_mgr.get_enumerator_settings()  # 自动验证

# 价格因子模拟器
price_factor_settings = setting_mgr.get_price_factor_settings()  # 自动验证

# 资金分配模拟器
capital_allocation_settings = setting_mgr.get_capital_allocation_settings()  # 自动验证
```

## 📌 重要说明

### use_sampling 的含义

- **枚举器**：指在 stock list 里的采样（默认 False）
- **模拟器**：指在枚举器采样结果里的抽样（默认 True）

### goal 配置的 customized 标记

支持两种方式：
- **顶层**：`goal.is_customized = True` → 跳过所有 goal 验证
- **子项**：`goal.take_profit.is_customized = True` → 只跳过 take_profit 验证
- **子项**：`goal.stop_loss.is_customized = True` → 只跳过 stop_loss 验证

### ratio 总和验证

如果没有 `expiration` 配置，系统会验证 `take_profit` 的 `sell_ratio` 总和是否 <= 1.0。如果超过 100%，交易将永远无法关闭，这是 Critical 错误。

### 日期范围默认值

- `start_date` 未配置时，使用 `DateUtils.DEFAULT_START_DATE`（默认 '20080101'）
- `end_date` 未配置时，使用 `DataManager.service.calendar.get_latest_completed_trading_date()`

## ✅ 已实现功能

- ✅ 错误类型定义（SettingError, SettingValidationResult）
- ✅ 基础设置验证（BaseSettings）
- ✅ 主设置类（StrategySettings）
- ✅ Goal 配置验证器（GoalValidator）
- ✅ 枚举器设置（EnumeratorSettings）
- ✅ 价格因子模拟器设置（PriceFactorSettings）
- ✅ 资金分配模拟器设置（CapitalAllocationSettings）
- ✅ 扫描器设置（ScannerSettings）
- ✅ 设置管理器（SettingManager）

## 📊 模块统计

- **Python 文件数**: 11 个
- **总代码行数**: 1,868 行
- **文档文件**: 1 个（README.md）

## 📋 下一步

1. 更新现有组件使用新的 SettingManager
2. 测试验证逻辑
3. 更新相关文档
