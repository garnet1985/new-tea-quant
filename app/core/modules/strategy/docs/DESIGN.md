# Strategy 系统设计文档

**版本**: 2.0  
**日期**: 2026-01-08  
**状态**: 设计阶段

---

## 📋 目录

1. [概述](#概述)
2. [设计动机](#设计动机)
3. [核心概念](#核心概念)
4. [系统架构](#系统架构)
5. [核心模块](#核心模块)
6. [核心模型](#核心模型)
7. [CapitalAllocationSimulator 设计](#capitalAllocationsimulator-设计)
8. [数据存储](#数据存储)
9. [执行流程](#执行流程)
10. [实施计划](#实施计划)

---

## 概述

strategy模块的主要作用是发现和回测用户自定义的策略。
结构上主要是2层：
- 基础层：机会模拟器，调用用户自定义的发现机会函数来枚举所有可能出现的机会和结果。这一次的output就是一个机会的长list，每个item就是机会的元信息和目标完成记录。当然为了复用，元信息需要缓存成本地CSV
- 应用层：包括价格回测器，自己分配回测器，实时机会扫描，分析器等多个应用。他们作用和产出分别是：
1. scanner，使用用户制定好的机会发现函数来对最新的所有股票列表的股票进行机会扫描，记录出现的机会，并传递给adapter（adapter模块还没完成）
2. strategy simulator，忽略资金只对价格进行模拟回测的工具，基于枚举器的结果，产出一个模拟的胜率，ROI信息的结果（就是legacy的simulator）
3. capital allocation simulator，多策略包含资金管理的回测模块，基于枚举器的结果，产出配置的自己比例和策略产生的收益结果。主要给用户测试投资资金分配的模块
4. 回测分析器（未实现，但以后会有），基于枚举结果的机器学习，提供因子分析的模块。还有对策略结果分布，概率，适应市场的一系列统计学分析器。

我们的settings我昨天规定了一下格式，是example的settings，看看有没有不妥当的地方。random策略里的setting是legacy时期的格式，需要换成example的新格式。

不要写代码，提出你理解上的问题，我们达成一致后再开始写代码

### 核心特点

- ✅ **多进程并行**：使用 ProcessWorker 高效处理海量股票
- ✅ **面向对象**：Opportunity 核心模型
- ✅ **自动回测**：框架自动执行止盈止损
- ✅ **灵活配置**：支持复杂策略配置
- ✅ **CSV 存储**：高性能、易查看

### 系统四层架构

```
┌─────────────────────────────────────────────────────────┐
│ Layer 0: OpportunityEnumerator（底层公用组件）          │
│   枚举所有可能的投资机会，供上层复用                     │
├─────────────────────────────────────────────────────────┤
│ Layer 1: Scanner（发现层）                              │
│   发现实时投资机会                                       │
├─────────────────────────────────────────────────────────┤
│ Layer 2: Simulator（验证层）                            │
│   验证策略效果（价格层面）                               │
├─────────────────────────────────────────────────────────┤
│ Layer 3: CapitalAllocationSimulator（执行层）           │
│   模拟资金分配执行（资金层面）                           │
└─────────────────────────────────────────────────────────┘
```

---

## 设计动机

### 动机 1: 面向对象设计

**问题**：Legacy 系统主要通过字典传递数据，缺少类型安全。

**解决方案**：引入 `Opportunity` 核心对象，提供类型安全和清晰的数据模型。

### 动机 2: BaseStrategyWorker 设计

**问题**：Legacy BaseStrategy 职责过多，难以测试和扩展。

**解决方案**：简化为 Worker 模式，只在子进程实例化，职责单一。

---

## 核心概念

### 等量交易

**定义**：只关注股价波动（价格变化），不分析金钱盈亏。

**示例**：
```
买入价格：10 元
卖出价格：11 元
收益率：(11 - 10) / 10 = 10%
```

**目的**：关注策略本身的效果（价格预测能力），独立于资金规模。

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

## 系统架构

### 整体架构

```
app/core/modules/
├── strategy/                    # 核心模块
│   ├── strategy_manager.py
│   ├── base_strategy_worker.py
│   ├── models/
│   │   ├── opportunity.py
│   │   └── strategy_settings.py
│   └── components/
│       ├── strategy_worker_data_manager.py
│       ├── opportunity_service.py
│       └── session_manager.py
│
├── opportunity_enumerator/      # Layer 0（新增）
│   ├── opportunity_enumerator.py
│   └── cache_manager.py
│
├── capital_allocation_simulator/ # Layer 3（待实现）
│   └── ...
│
└── indicator/                   # 指标组件
    └── indicator_service.py

app/userspace/strategies/        # 用户策略
└── {strategy_name}/
    ├── strategy_worker.py
    ├── settings.py
    └── results/
        ├── scan/
        └── simulate/
```

### 模块职责

| 模块 | 职责 |
|------|------|
| StrategyManager | 策略管理、作业构建、多进程执行 |
| BaseStrategyWorker | 处理单个股票的扫描或回测 |
| StrategyWorkerDataManager | 数据加载、缓存、过滤 |
| OpportunityService | Opportunity 的存储管理 |
| OpportunityEnumerator | 枚举所有可能的机会（Layer 0） |
| IndicatorService | 技术指标计算（代理 pandas-ta） |

---

## 核心模块

### OpportunityEnumerator（Layer 0）

**职责**：完整枚举所有可能的投资机会，供上层模块使用。

**核心特点**：
- ⭐ **完整枚举**：每天都扫描，不跳过任何机会
- ⭐ **同时追踪多个机会**：不受持仓限制
- ⭐ **完整记录**：每个机会独立追踪，记录 completed_targets
- ⭐ **使用 Opportunity 实例方法**：`check_targets()`, `settle()`
- ⭐ **每次重新计算**：保证结果最新

**API**：

```python
class OpportunityEnumerator:
    @staticmethod
    def enumerate(
        strategy_name: str,
        start_date: str,
        end_date: str,
        stock_list: List[str],
        max_workers: int = 10
    ) -> List[Dict[str, Any]]:
        """完整枚举所有机会"""
        pass
```

**缓存结构**（CSV）：

```
results/opportunity_enumerator/
└── momentum/
    ├── simplified/
    │   ├── 20230101_20231231/
    │   │   ├── opportunities.csv      # 主表
    │   │   ├── targets.csv           # 子表
    │   │   └── metadata.json         # 元信息
    │   └── latest -> 20230101_20231231/
    └── full/
```

**CSV 示例**：

`opportunities.csv`：
```csv
opportunity_id,stock_id,start_date,purchase_price,status,roi
uuid-1,000001.SZ,20230115,10.50,closed,0.067
```

`targets.csv`：
```csv
opportunity_id,target_type,sell_date,sell_price,ratio,roi
uuid-1,take_profit,20230125,11.20,0.5,0.067
```

---

### StrategyManager

**职责**：策略管理器（主进程）

**核心功能**：
- 策略发现
- 作业构建
- 多进程执行
- 全局缓存管理

---

### BaseStrategyWorker

**职责**：策略 Worker 基类（子进程）

**用户实现**：
- `scan_opportunity()` - 发现买入信号

**框架自动**：
- 自动执行回测（根据 goal 配置）
- 止盈止损处理

---

### IndicatorService

**职责**：技术指标计算（代理 pandas-ta-classic）

**API 示例**：

```python
# 计算 MA
ma = IndicatorService.ma(klines, period=20)

# 计算 MACD
macd = IndicatorService.macd(klines)

# 通用 API
result = IndicatorService.calculate('cci', klines, period=14)
```

---

## 核心模型

### Opportunity

投资机会模型（⭐ 带实例方法的智能对象）：

```python
@dataclass
class Opportunity:
    opportunity_id: str
    stock_id: str
    stock_name: str
    strategy_name: str
    
    # 触发信息
    trigger_date: str
    trigger_price: float
    trigger_conditions: Dict
    
    # 回测结果
    status: str  # active / closed / completed
    completed_targets: List[Dict]  # 完成的目标列表
    roi: float
    
    # ===== 实例方法 =====
    
    def check_targets(
        self,
        current_kline: Dict[str, Any],
        goal_config: Dict[str, Any]
    ) -> bool:
        """
        检查止盈止损目标
        
        Returns:
            is_completed: 是否完成（触发止盈/止损）
        """
        pass
    
    def settle(
        self,
        last_kline: Dict[str, Any],
        reason: str = 'backtest_end'
    ):
        """强制结算（回测结束时）"""
        pass
```

### StrategySettings

策略配置模型（字典封装）。

---

## CapitalAllocationSimulator 设计

### 概述

**功能**：模拟资金分配执行（资金层面）

**输入**：策略列表 + 初始资金  
**输出**：ExecutionRecord（实际盈亏）

### 核心业务流程

#### Step 1: 获取所有 Opportunities

使用 `OpportunityEnumerator` 枚举所有机会。

```python
all_opps = OpportunityEnumerator.enumerate(
    strategy_name='momentum',
    mode='simplified',
    signal_window=3,
    use_cache=True
)
```

#### Step 2: 构建 Timeline

事件驱动方式构建时间轴（只处理有事件的日期）。

```python
timeline = {
    '20230115': {
        'buys': [...],
        'sells': [...]
    }
}
```

#### Step 3: 账户执行

按时间轴推进，先卖后买，管理账户和持仓。

#### Step 4: 结果输出

生成统计报告，保存 JSON 结果。

### 核心数据结构

```python
@dataclass
class Account:
    cash: float
    invested_amount: float  # 沉没成本
    positions: Dict[str, Position]
    
@dataclass
class Position:
    stock_id: str
    cost_basis: float
    remaining_shares: float
    
@dataclass
class ExecutionRecord:
    stock_id: str
    buy_date: str
    sell_date: str
    profit: float
    profit_ratio: float
```

---

## 数据存储

### 1. Opportunity 存储（CSV）

**动机**：数据量大（5K-500K），需要高性能、易查看。

**文件结构**：

```
results/opportunity_enumerator/momentum/simplified/20230101_20231231/
├── opportunities.csv      # 主表（~500 KB）
├── targets.csv           # 子表（~800 KB）
└── metadata.json         # 元信息（~5 KB）
```

**优势**：
- 文件小（1-2 MB）
- 加载快（0.1-0.2 秒）
- Excel 直接打开

### 2. Settings 设计

**动机**：保持与项目其他模块（Tag 系统等）的配置风格一致。

**设计**：字典结构 + 分层配置

#### 策略配置（per strategy）

```python
# app/userspace/strategies/example/settings.py
settings = {
    "name": "example",
    "description": "...",
    "is_enabled": False,
    
    # 数据配置
    "data": {
        "base": EntityType.STOCK_KLINE_DAILY.value,
        "adjust": AdjustType.QFQ.value,
        "min_required_records": 1000,
        
        # 技术指标配置（统一格式：数组）⭐
        "indicators": {
            "ma": [
                {"period": 5},
                {"period": 10}
            ],
            "rsi": [
                {"period": 14}
            ]
        },
        
        "required_entities": [...]
    },
    
    # 股票采样配置（per strategy）
    "sampling": {
        "strategy": "pool",
        "sampling_amount": 50,
        
        "pool": {
            # 相对路径：pools/xxx.txt（当前策略文件夹下）⭐
            "id_list_path": "pools/high_quality.txt",
            # 或直接数组
            # "stock_pool": ["000001.SZ", ...]
        }
    },
    
    # Simulator 配置
    "simulator": {
        "start_date": "20230101",
        "end_date": "",
        "goal": {...}  # 止盈止损配置
    },
    
    # 性能配置（per strategy）
    "performance": {
        "max_workers": "auto"
    }
}
```

#### 全局配置（跨策略）

```python
# app/userspace/strategies/global_settings.py
DEFAULT_ALLOCATION = {
    "capital": {...},
    "fees": {...},
    "execution": {...},
    "preprocess": {...}
}
```

**关键点**：
- ✅ 大部分配置是 **per strategy** 的（sampling、data、performance）
- ✅ 只有 Allocation 配置是全局的（跨策略）
- ✅ pools/blacklists 在**策略文件夹下**（per strategy）

---

### 3. Indicators 配置

**动机**：框架需要知道用户需要哪些指标及其参数。

**设计**：统一数组格式

```python
"indicators": {
    # 所有指标都用数组（统一 parse）
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
```

**工作流**：
1. 用户配置需要的指标
2. 框架自动计算并添加到 klines
3. 用户直接使用：`kline["ma5"]`, `kline["rsi"]`

**适用范围**：
- ✅ 只用于 **K 线数据**
- ❌ 不用于其他 entity（GDP、财务数据等）
- 💡 如需其他数据的分析，用户手动调用 `IndicatorService`

---

### 4. Pools/Blacklists 文件

**动机**：处理长列表，方便迁移和管理。

**设计**：per strategy，纯文本文件

**文件结构**：
```
strategies/example/
├── pools/
│   ├── high_quality.txt    # 优质股票池
│   └── test.txt            # 测试用（少量）
└── blacklists/
    └── st_stocks.txt       # ST 股票
```

**文件格式**（纯文本）：
```txt
# 优质股票池
# 一行一个股票代码

000001.SZ
000002.SZ
000333.SZ
```

**配置引用**（相对路径）：
```python
"pool": {
    "id_list_path": "pools/high_quality.txt"  # 相对于策略文件夹
}
```

**优势**：
- ✅ per strategy（隔离、安全）
- ✅ 纯文本（简单、Git 友好）
- ✅ 支持注释

---

## 执行流程

### Scanner 执行流程

```
1. 加载策略配置
2. 获取股票列表（采样）
3. 构建 scan jobs
4. 多进程执行
5. 保存 Opportunity（JSON）
```

### Simulator 执行流程

```
1. 加载策略配置
2. 获取股票列表
3. 构建 simulate jobs
4. 多进程执行（每日推进，自动回测）
5. 保存 Opportunity（JSON）
```

### CapitalAllocationSimulator 执行流程

```
1. 获取所有 Opportunities（OpportunityEnumerator）
2. 构建 Timeline（事件驱动）
3. 按时间轴执行（先卖后买）
4. 生成报告和结果
```

---

## 实施计划

### Phase 1: OpportunityCalculator + OpportunityEnumerator（3 天）

**目标**：建立 Layer 0

1. 创建 OpportunityCalculator（1 天）
   - 提取止盈止损逻辑
   - 创建 `simulate_opportunity()` 方法

2. 创建 OpportunityEnumerator（2 天）
   - 实现简化版（信号窗口）
   - 实现 CSV 存储
   - 缓存管理

**产出**：
- `app/core/modules/opportunity_enumerator/`
- `app/core/modules/strategy/components/opportunity_calculator.py`

---

### Phase 2: CapitalAllocationSimulator（2 天）

**目标**：实现 Step 1-4

1. Step 1: 获取 Opportunities（0.5 天）
2. Step 2: Timeline 构建（0.5 天）
3. Step 3: 执行模拟（0.5 天）
4. Step 4: 结果输出（0.5 天）

**产出**：
- `app/core/modules/capital_allocation_simulator/`

---

### Phase 3: 测试和验证（2 天）

1. 单元测试
2. 集成测试
3. 对比验证

---

### Phase 4: 文档和示例（1 天）

1. 用户文档
2. 示例代码

---

**总计**：8 天（1.5 周）

---

## 未来扩展

### MachineLearning 模块

使用 `OpportunityEnumerator` 生成训练数据，进行因子分析和参数优化。

### ParameterOptimizer 模块

自动寻找最优策略参数。

### RiskAnalyzer 模块

策略风险分析（最大回撤、夏普比率等）。

---

**文档结束**
