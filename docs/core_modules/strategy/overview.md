# Strategy 模块概览

**版本：** 3.0  
**最后更新**: 2026-01-17

---

## 📋 概述

Strategy 系统是一个用于**发现和回测用户自定义策略**的框架。系统采用**配置驱动**的方式，允许用户通过 Python 配置文件定义策略，框架自动执行扫描、枚举和回测。

### 为什么需要 Strategy 系统？

在量化交易中，我们需要：
- **策略发现**：从市场中发现投资机会
- **策略验证**：回测历史数据，验证策略效果
- **资金管理**：模拟真实资金约束下的交易

Strategy 系统通过**四层架构**解决了这些问题，其中 **OpportunityEnumerator + 双模拟器分层** 是整个框架的核心亮点：
- ✅ **Layer 0（OpportunityEnumerator）**：完整枚举所有可能机会 —— 作为「底层枚举器」，一次性把所有可能的交易机会（枚举输出结果：枚举输出标准结果）算出来并持久化：
  - 一次计算，多次复用：后续所有模拟、分析、机器学习训练都复用同一份枚举结果，而不再重复跑 on-bar 回测
  - 可追溯：任何时刻都可以回到某只股票、某天、某机会的完整路径，极大方便调试
  - 对分析/ML 友好：枚举输出结果 本质上就是一个结构化的数据集，天然适合分析工具和模型训练使用
  - 相当于回测缓存层：把昂贵的 on-bar 回测拆成「先枚举机会，再叠加模拟」，大幅缩短迭代时间
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
- 验证策略效果（价格层面），只关注「价格是否走对了」，不涉及资金规模和仓位
- 无资金约束，只关心等量交易的收益曲线，天然对应「价格因子」视角
- 基于 OpportunityEnumerator 的 枚举输出结果，复用枚举缓存，速度非常快，适合频繁调整策略与参数
- 输出：Investment 记录（JSON 格式），可直接用于统计分析和可视化

**Layer 3: CapitalAllocationSimulator（执行层）**
- 模拟资金分配执行（资金层面），在确定了价格层面策略可行之后，进一步回答「多少钱、怎么买、怎么买多只」
- 真实资金约束，考虑费用、持仓限制、多股票间的资金竞争等
- 同样基于 OpportunityEnumerator 的 枚举输出结果，在价格模拟验证通过后再叠加资金管理逻辑，避免过早卷入复杂度
- 输出：Trade 记录、Equity Curve、Summary（JSON 格式），帮助用户真正制定和调试仓位分配策略

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
            "sma": [
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
        sma5 = current_kline.get('ssma5')
        sma10 = current_kline.get('sma10')
        rsi = current_kline.get('rsi')
        
        # 实现策略逻辑
        # 例如：MA5 上穿 MA10 且 RSI < 30
        if sma5 and sma10 and rsi:
            if sma5 > sma10 and rsi < 30:
                # 创建 Opportunity
                opportunity = Opportunity(
                    stock=self.stock_info,
                    record_of_today=current_kline,
                    extra_fields={
                        "ssma5": sma5,
                        "sma10": sma10,
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
1. 先运行 OpportunityEnumerator 生成 枚举输出结果
2. 调用 `PriceFactorSimulator.run()`
3. 结果保存在 `results/price_factor/{strategy_name}/{version_dir}/`

### 场景 4：资金分配回测

**需求**：在真实资金约束下回测策略效果

**实现**：
1. 先运行 OpportunityEnumerator 生成 枚举输出结果
2. 调用 `CapitalAllocationSimulator.run()`
3. 结果保存在 `results/capital_allocation/{strategy_name}/{version_dir}/`
4. 包含交易记录、权益曲线、汇总统计

---

## 相关文档

- **[architecture.md](./architecture.md)**：架构文档，包含详细的技术设计、数据流、运行时 Workflow
- **[decisions.md](./decisions.md)**：重要决策记录，包含架构设计决策和理由
- **示例配置**：`userspace/strategies/example/settings.py` - 完整的配置示例
- **组件文档**：
  - `components/opportunity_enumerator/README.md` - OpportunityEnumerator 使用指南
  - `components/setting_management/README.md` - 设置管理指南

---

**文档结束**
