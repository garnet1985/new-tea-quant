# Strategy 系统使用指南

**版本：** 3.0  
**最后更新**: 2026-01-17

---

## 📋 目录

1. [概述](#概述)
2. [核心概念](#核心概念)
3. [快速开始](#快速开始)
4. [使用场景](#使用场景)
5. [配置指南](#配置指南)
6. [开发指南](#开发指南)
7. [最佳实践](#最佳实践)
8. [常见问题](#常见问题)
9. [相关文档](#相关文档)

---

## 概述

Strategy 系统是一个用于**发现和回测用户自定义策略**的框架。系统采用**配置驱动**的方式，允许用户通过 Python 配置文件定义策略，框架自动执行扫描、枚举和回测。

### 为什么需要 Strategy 系统？

在量化交易中，我们需要：
- **策略发现**：从市场中发现投资机会
- **策略验证**：回测历史数据，验证策略效果
- **资金管理**：模拟真实资金约束下的交易

Strategy 系统通过**四层架构**解决了这些问题：
- ✅ **Layer 0（OpportunityEnumerator）**：完整枚举所有可能机会
- ✅ **Layer 1（Scanner）**：实时机会扫描
- ✅ **Layer 2（PriceFactorSimulator）**：价格因子模拟（无资金约束）
- ✅ **Layer 3（CapitalAllocationSimulator）**：资金分配模拟（真实资金约束）

---

## 核心概念

### 投资机会（Opportunity）

一个投资机会，包含触发信息、回测结果和状态管理。

**触发信息**：
- `trigger_date`：触发日期
- `trigger_price`：触发价格
- `trigger_conditions`：触发条件

**回测结果**：
- `sell_date`：卖出日期
- `sell_price`：卖出价格
- `sell_reason`：卖出原因（止盈/止损/到期）
- `roi`：收益率

**状态**：
- `active`：正在追踪中
- `closed`：已完成
- `open`：未完成

### 等量交易（Price Factor）

只关注股价波动（价格变化），不分析金钱盈亏。

**示例**：
```
买入价格：10 元
卖出价格：11 元
收益率：(11 - 10) / 10 = 10%
```

**目的**：关注策略本身的效果（价格预测能力），独立于资金规模。

### 四层架构

**Layer 0: OpportunityEnumerator（底层公用组件）**
- 完整枚举所有可能的投资机会
- 每天都扫描，不跳过任何机会
- 同时追踪多个机会（不受持仓限制）
- 输出：CSV 双表（`opportunities.csv` + `targets.csv`）

**Layer 1: Scanner（发现层）**
- 发现当前的投资机会
- 只扫描最新一天的数据
- 输出：Opportunity（JSON 格式，status=active）
- 用途：实盘提示

**Layer 2: PriceFactorSimulator（验证层）**
- 验证策略效果（价格层面）
- 无资金约束，只关注价格变化
- 基于 OpportunityEnumerator 的枚举输出结果
- 输出：Investment 记录（JSON 格式）
- 用途：快速验证信号质量

**Layer 3: CapitalAllocationSimulator（执行层）**
- 模拟资金分配执行（资金层面）
- 真实资金约束，考虑费用、持仓限制
- 基于 OpportunityEnumerator 的枚举输出结果
- 输出：Trade 记录、Equity Curve、Summary（JSON 格式）
- 用途：完整回测

### Scanner vs Simulator

**Scanner**：
- 作用：发现当前的投资机会
- 数据范围：只扫描最新一天的数据
- 输出：Opportunity（status=active）
- 用途：实盘提示

**Simulator**：
- 作用：回测历史机会的效果
- 数据范围：历史数据
- 输出：Opportunity（status=closed）
- 用途：策略验证

---

## 快速开始

### 1. 创建策略

在 `userspace/strategies/` 目录下创建新的策略目录：

```bash
mkdir -p userspace/strategies/my_strategy
```

### 2. 创建配置文件

创建 `userspace/strategies/my_strategy/settings.py`：

```python
settings = {
    "name": "my_strategy",
    "description": "我的策略",
    "is_enabled": True,
    
    # 数据配置
    "data": {
        "base": "stock_kline_daily",
        "adjust": "qfq",
        "min_required_records": 1000,
        "indicators": {
            "ma": [
                {"period": 5},
                {"period": 10}
            ],
            "rsi": [
                {"period": 14}
            ]
        }
    },
    
    # 股票采样配置
    "sampling": {
        "strategy": "pool",
        "sampling_amount": 50,
        "pool": {
            "id_list_path": "pools/high_quality.txt"
        }
    },
    
    # 模拟器配置
    "simulator": {
        "start_date": "20230101",
        "end_date": "",
        "goal": {
            "take_profit": [
                {"ratio": 0.1, "sell_ratio": 0.5},
                {"ratio": 0.2, "sell_ratio": 0.5}
            ],
            "stop_loss": [
                {"ratio": -0.05}
            ]
        }
    },
    
    # 性能配置
    "performance": {
        "max_workers": "auto"
    }
}
```

### 3. 实现 StrategyWorker

创建 `userspace/strategies/my_strategy/strategy_worker.py`：

```python
from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from core.modules.strategy.models.opportunity import Opportunity
from typing import Optional, Dict, Any

class MyStrategyWorker(BaseStrategyWorker):
    """我的策略 Worker"""
    
    def scan_opportunity(
        self,
        data_of_today: Dict[str, Any]
    ) -> Optional[Opportunity]:
        """
        扫描投资机会
        
        Args:
            data_of_today: 今天及之前的所有数据
                - data_of_today['klines']['daily']: 日线数据（已计算技术指标）
                - data_of_today.get('gdp', []): GDP 数据（如果配置了）
                - data_of_today.get('tags', {}): Tag 数据（如果配置了）
                
        Returns:
            Opportunity 对象，如果没有机会则返回 None
        """
        # 获取当前 K 线
        klines = data_of_today['klines']['daily']
        if not klines:
            return None
        
        current_kline = klines[-1]  # 最新一条
        
        # 访问技术指标（框架已自动计算）
        ma5 = current_kline.get('ma5')
        ma10 = current_kline.get('ma10')
        rsi = current_kline.get('rsi')
        
        # 实现策略逻辑
        # 例如：MA5 上穿 MA10 且 RSI < 30
        if ma5 and ma10 and rsi:
            if ma5 > ma10 and rsi < 30:
                # 创建 Opportunity
                opportunity = Opportunity(
                    stock=self.stock_info,
                    record_of_today=current_kline,
                    extra_fields={
                        "ma5": ma5,
                        "ma10": ma10,
                        "rsi": rsi
                    }
                )
                return opportunity
        
        return None
```

### 4. 执行策略

#### 扫描实时机会

```python
from core.modules.strategy.strategy_manager import StrategyManager

# 创建 StrategyManager
manager = StrategyManager(is_verbose=True)

# 扫描实时机会
manager.scan(strategy_name="my_strategy")
```

#### 枚举所有机会

```python
from core.modules.strategy.components.opportunity_enumerator import OpportunityEnumerator

# 枚举所有机会
opportunities = OpportunityEnumerator.enumerate(
    strategy_name="my_strategy",
    start_date="20230101",
    end_date="20231231",
    stock_list=["000001.SZ", "000002.SZ", ...],
    max_workers="auto"
)
```

#### 价格因子模拟

```python
from core.modules.strategy.components.simulator.price_factor import PriceFactorSimulator

# 价格因子模拟
simulator = PriceFactorSimulator(is_verbose=True)
result = simulator.run(strategy_name="my_strategy")
```

#### 资金分配模拟

```python
from core.modules.strategy.components.simulator.capital_allocation import CapitalAllocationSimulator

# 资金分配模拟
simulator = CapitalAllocationSimulator(is_verbose=True)
result = simulator.run(strategy_name="my_strategy")
```

---

## 使用场景

### 场景 1：实时机会扫描

**需求**：每天扫描市场，发现当前的投资机会

**实现**：
1. 实现 `scan_opportunity()` 方法
2. 调用 `manager.scan(strategy_name="my_strategy")`
3. 结果保存在 `results/scan/{date}/opportunities.json`

### 场景 2：完整机会枚举

**需求**：枚举历史所有可能的机会，供后续分析使用

**实现**：
1. 调用 `OpportunityEnumerator.enumerate()`
2. 结果保存在 `results/opportunity_enums/{strategy_name}/{version_dir}/`
3. 输出 CSV 双表（`opportunities.csv` + `targets.csv`）

### 场景 3：价格因子验证

**需求**：快速验证策略的信号质量，不考虑资金约束

**实现**：
1. 先运行 OpportunityEnumerator 生成枚举输出结果
2. 调用 `PriceFactorSimulator.run()`
3. 结果保存在 `results/price_factor/{strategy_name}/{version_dir}/`

### 场景 4：资金分配回测

**需求**：在真实资金约束下回测策略效果

**实现**：
1. 先运行 OpportunityEnumerator 生成枚举输出结果
2. 调用 `CapitalAllocationSimulator.run()`
3. 结果保存在 `results/capital_allocation/{strategy_name}/{version_dir}/`
4. 包含交易记录、权益曲线、汇总统计

---

## 配置指南

### 基本配置

**必需配置**：
- `name`：策略唯一代码
- `data.base`：基础数据实体类型（如 `stock_kline_daily`）
- `data.adjust`：复权类型（如 `qfq`）

**可选配置**：
- `description`：描述信息
- `is_enabled`：是否启用（默认 `False`）

### 数据配置

**技术指标配置**：
```python
{
    "data": {
        "indicators": {
            "ma": [
                {"period": 5},
                {"period": 10},
                {"period": 20}
            ],
            "rsi": [
                {"period": 14}
            ],
            "macd": [
                {"fast": 12, "slow": 26, "signal": 9}
            ]
        }
    }
}
```

**依赖数据配置**：
```python
{
    "data": {
        "required_entities": [
            {"type": "gdp"},
            {"type": "tag", "scenario": "momentum"}
        ]
    }
}
```

### 采样配置

**股票池采样**：
```python
{
    "sampling": {
        "strategy": "pool",
        "sampling_amount": 50,
        "pool": {
            "id_list_path": "pools/high_quality.txt"
        }
    }
}
```

**连续采样**：
```python
{
    "sampling": {
        "strategy": "continuous",
        "sampling_amount": 100
    }
}
```

### 止盈止损配置

```python
{
    "simulator": {
        "goal": {
            "take_profit": [
                {"ratio": 0.1, "sell_ratio": 0.5},  # 10% 止盈，卖出 50%
                {"ratio": 0.2, "sell_ratio": 0.5}   # 20% 止盈，卖出 50%
            ],
            "stop_loss": [
                {"ratio": -0.05}  # 5% 止损
            ]
        }
    }
}
```

### 完整配置示例

> **详细配置结构请参考** `userspace/strategies/example/settings.py`，该文件包含完整的配置示例和每个属性的详细解释。

---

## 开发指南

### 实现 StrategyWorker

StrategyWorker 需要继承 `BaseStrategyWorker` 并实现 `scan_opportunity()` 方法：

```python
from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from core.modules.strategy.models.opportunity import Opportunity
from typing import Optional, Dict, Any

class MyStrategyWorker(BaseStrategyWorker):
    def scan_opportunity(
        self,
        data_of_today: Dict[str, Any]
    ) -> Optional[Opportunity]:
        """
        扫描投资机会
        
        Args:
            data_of_today: 今天及之前的所有数据
                - data_of_today['klines']['daily']: 日线数据（已计算技术指标）
                - data_of_today.get('gdp', []): GDP 数据（如果配置了）
                - data_of_today.get('tags', {}): Tag 数据（如果配置了）
                
        Returns:
            Opportunity 对象，如果没有机会则返回 None
        """
        # 实现策略逻辑
        klines = data_of_today['klines']['daily']
        if not klines:
            return None
        
        current_kline = klines[-1]
        
        # 访问技术指标（框架已自动计算）
        ma5 = current_kline.get('ma5')
        rsi = current_kline.get('rsi')
        
        # 实现策略逻辑
        if ma5 and rsi and ma5 > 10 and rsi < 30:
            opportunity = Opportunity(
                stock=self.stock_info,
                record_of_today=current_kline,
                extra_fields={"ma5": ma5, "rsi": rsi}
            )
            return opportunity
        
        return None
```

### 访问数据

**K 线数据**：
```python
klines = data_of_today['klines']['daily']
current_kline = klines[-1]  # 最新一条
```

**技术指标**（框架已自动计算）：
```python
ma5 = current_kline.get('ma5')
ma10 = current_kline.get('ma10')
rsi = current_kline.get('rsi')
macd = current_kline.get('macd')
```

**依赖数据**：
```python
gdp_data = data_of_today.get('gdp', [])
tag_data = data_of_today.get('tags', {})
```

**股票信息**：
```python
stock_id = self.stock_id  # 股票代码
stock_name = self.stock_info.get('name')  # 股票名称
```

### 钩子函数

StrategyWorker 可以重写以下钩子函数：

- `on_init()`：初始化钩子（无参数）
- `on_before_scan()`：扫描前钩子（无参数）
- `on_opportunity_found(opportunity)`：发现机会后钩子
- `on_scan_complete(result)`：扫描完成钩子

---

## 最佳实践

### 1. 配置管理

- ✅ **使用有意义的名称**：策略名称应该清晰表达业务含义
- ✅ **添加描述信息**：为策略添加 `description`
- ✅ **合理设置采样**：根据计算资源选择合适的 `sampling_amount`
- ✅ **配置技术指标**：在 `data.indicators` 中声明需要的指标，框架自动计算

### 2. 策略逻辑

- ✅ **避免"上帝模式"**：框架已自动过滤数据到当前日期，无需担心
- ✅ **处理边界情况**：检查数据是否足够（如计算 MA 需要至少 N 条数据）
- ✅ **使用技术指标**：优先使用框架自动计算的技术指标，避免重复计算
- ✅ **记录额外信息**：使用 `extra_fields` 记录策略特定的信息

### 3. 性能优化

- ✅ **合理设置 worker 数量**：使用 `"auto"` 让框架自动决定
- ✅ **使用股票池**：对于测试，使用小股票池（如 `pools/test.txt`）
- ✅ **缓存利用**：Scanner 支持缓存机制，避免重复扫描

### 4. 结果分析

- ✅ **查看 CSV 结果**：OpportunityEnumerator 的 CSV 结果可以用 Excel 打开
- ✅ **对比不同版本**：使用版本管理对比不同版本的结果
- ✅ **分析权益曲线**：CapitalAllocationSimulator 的权益曲线可以可视化分析

---

## 常见问题

### Q1: 如何查看扫描结果？

**A**: Scanner 的结果保存在 `results/scan/{date}/opportunities.json`，可以直接查看 JSON 文件。

### Q2: 如何查看枚举结果？

**A**: OpportunityEnumerator 的结果保存在 `results/opportunity_enums/{strategy_name}/{version_dir}/`，包含 CSV 文件，可以用 Excel 打开。

### Q3: Scanner 和 OpportunityEnumerator 的区别是什么？

**A**: 
- **Scanner**：只扫描最新一天的数据，用于实盘提示
- **OpportunityEnumerator**：枚举历史所有可能的机会，用于完整分析

### Q4: PriceFactorSimulator 和 CapitalAllocationSimulator 的区别是什么？

**A**: 
- **PriceFactorSimulator**：只关注价格变化，无资金约束，适合快速验证
- **CapitalAllocationSimulator**：考虑真实资金约束，适合完整回测

### Q5: 如何配置技术指标？

**A**: 在 `settings.py` 的 `data.indicators` 中配置：

```python
{
    "data": {
        "indicators": {
            "ma": [{"period": 5}, {"period": 10}],
            "rsi": [{"period": 14}]
        }
    }
}
```

框架会自动计算并添加到 klines 中，可以直接使用 `kline["ma5"]`, `kline["rsi"]`。

### Q6: 如何配置止盈止损？

**A**: 在 `settings.py` 的 `simulator.goal` 中配置：

```python
{
    "simulator": {
        "goal": {
            "take_profit": [
                {"ratio": 0.1, "sell_ratio": 0.5}
            ],
            "stop_loss": [
                {"ratio": -0.05}
            ]
        }
    }
}
```

### Q7: 如何查看执行进度？

**A**: 创建 StrategyManager 时设置 `is_verbose=True`，系统会实时显示执行进度。

---

## 相关文档

- **[ARCHITECTURE.md](./ARCHITECTURE.md)**：架构文档，包含详细的技术设计、数据流、运行时 Workflow 和重要决策记录
- **示例配置**：`userspace/strategies/example/settings.py` - 完整的配置示例
- **组件文档**：
  - `components/opportunity_enumerator/README.md` - OpportunityEnumerator 使用指南
  - `components/setting_management/README.md` - 设置管理指南

---

**文档结束**
