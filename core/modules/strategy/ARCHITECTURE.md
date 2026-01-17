# Strategy 系统架构文档

**版本：** 3.0  
**最后更新**: 2026-01-17  
**状态：** 生产环境

---

## 📋 目录

1. [设计背景](#设计背景)
2. [核心概念](#核心概念)
3. [系统架构](#系统架构)
4. [四层架构设计](#四层架构设计)
5. [核心组件](#核心组件)
6. [核心模型](#核心模型)
7. [运行时 Workflow](#运行时-workflow)
8. [数据流设计](#数据流设计)
9. [重要决策记录 (Decisions)](#重要决策记录-decisions)
10. [配置设计](#配置设计)
11. [数据存储](#数据存储)
12. [职责边界](#职责边界)
13. [设计原则](#设计原则)
14. [文件组织](#文件组织)
15. [版本历史](#版本历史)

---

## 设计背景

### 问题背景

Strategy 模块旨在解决以下问题：

1. **策略发现和回测**：需要支持用户自定义策略的发现和回测
2. **完整枚举 vs 主线回测**：需要区分完整枚举（所有可能机会）和主线回测（实际交易路径）
3. **价格层面 vs 资金层面**：需要区分价格因子评估（无资金约束）和资金分配模拟（真实资金约束）
4. **多进程并行**：需要支持大规模并行计算，充分利用多核 CPU
5. **配置驱动**：通过配置声明策略行为，无需修改代码

### 设计目标

1. **四层架构**：清晰分离不同层次的职责（枚举、扫描、价格模拟、资金分配）
2. **配置驱动**：通过 Python 配置文件定义策略，无需修改框架代码
3. **多进程并行**：充分利用多核 CPU，提高计算效率
4. **CSV 存储**：高性能、易查看的结果存储
5. **易于扩展**：提供钩子函数和扩展点，方便用户扩展功能

---

## 核心概念

### 投资机会（Opportunity）

一个投资机会，包含触发信息、回测结果和状态管理。

- **触发信息**：`trigger_date`, `trigger_price`, `trigger_conditions`
- **回测结果**：`sell_date`, `sell_price`, `sell_reason`, `roi`
- **状态**：`active`（正在追踪）、`closed`（已完成）、`open`（未完成）

### 等量交易（Price Factor）

只关注股价波动（价格变化），不分析金钱盈亏。

- **目的**：关注策略本身的效果（价格预测能力），独立于资金规模
- **示例**：买入价格 10 元，卖出价格 11 元，收益率 = (11 - 10) / 10 = 10%

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

### OpportunityEnumerator vs Simulator

**OpportunityEnumerator**（完整枚举）：
- 持仓限制：同时追踪多个机会（可重叠）
- 扫描频率：每天都扫描，不跳过任何机会
- 输出：所有可能机会（多条路径）
- 用途：完整枚举（供 Allocation 使用）

**Simulator**（主线回测）：
- 持仓限制：同时只能持有 1 个
- 扫描频率：无持仓时才扫描
- 输出：主线机会（一条路径）
- 用途：策略验证（主线回测）

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│              Strategy 系统架构                            │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────────────────────────────┐          │
│  │  StrategyManager (主进程)                  │          │
│  │  - 策略发现和管理                          │          │
│  │  - 作业构建                                │          │
│  │  - 多进程调度                              │          │
│  └──────────────────────────────────────────┘          │
│           │                                              │
│           ├─▶ Scanner (Layer 1)                        │
│           │   - 实时机会扫描                            │
│           │   - 保存 Opportunity (JSON)                │
│           │                                              │
│           ├─▶ OpportunityEnumerator (Layer 0)           │
│           │   - 完整枚举所有机会                        │
│           │   - CSV 双表存储                            │
│           │                                              │
│           ├─▶ PriceFactorSimulator (Layer 2)            │
│           │   - 价格因子模拟（无资金约束）              │
│           │   - 基于 SOT 结果                           │
│           │                                              │
│           └─▶ CapitalAllocationSimulator (Layer 3)      │
│               - 资金分配模拟（真实资金约束）            │
│               - 基于 SOT 结果                           │
│                                                           │
│           │                                              │
│           ▼                                              │
│  ┌──────────────────────────────────────────┐          │
│  │  BaseStrategyWorker (子进程)              │          │
│  │  - 处理单个股票的扫描或回测                │          │
│  │  - 数据加载和过滤                          │          │
│  └──────────────────────────────────────────┘          │
│                                                           │
│           │                                              │
│           ▼                                              │
│  ┌──────────────────────────────────────────┐          │
│  │  Results Storage                         │          │
│  │  - CSV (OpportunityEnumerator)           │          │
│  │  - JSON (Scanner, Simulators)            │          │
│  └──────────────────────────────────────────┘          │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

---

## 四层架构设计

### Layer 0: OpportunityEnumerator（底层公用组件）

**职责**：完整枚举所有可能的投资机会，供上层复用

**核心特点**：
- ✅ **完整枚举**：每天都扫描，不跳过任何可能的机会
- ✅ **同时追踪多个机会**：不受持仓限制
- ✅ **完整记录**：每个机会独立追踪，记录 `completed_targets`
- ✅ **CSV 存储**：高性能，Excel 可直接打开
- ✅ **每次重新计算**：保证结果反映最新策略代码

**输出**：CSV 双表（`opportunities.csv` + `targets.csv`）

### Layer 1: Scanner（发现层）

**职责**：发现实时投资机会

**核心特点**：
- ✅ **实时扫描**：只扫描最新一天的数据
- ✅ **缓存管理**：支持缓存机制，避免重复扫描
- ✅ **Adapter 分发**：支持多个 Adapter 分发机会

**输出**：Opportunity（JSON 格式，status=active）

### Layer 2: PriceFactorSimulator（验证层）

**职责**：验证策略效果（价格层面）

**核心特点**：
- ✅ **无资金约束**：只关注价格变化，不涉及资金管理
- ✅ **基于 SOT**：使用 OpportunityEnumerator 的 SOT 结果
- ✅ **单股独立**：每只股票独立模拟，适合多进程

**输出**：Investment 记录（JSON 格式）

### Layer 3: CapitalAllocationSimulator（执行层）

**职责**：模拟资金分配执行（资金层面）

**核心特点**：
- ✅ **真实资金约束**：考虑资金分配、费用、持仓限制
- ✅ **事件驱动**：基于事件流（trigger/target）执行
- ✅ **账户管理**：管理账户、持仓、交易记录

**输出**：Trade 记录、Equity Curve、Summary（JSON 格式）

---

## 核心组件

### 1. StrategyManager (`strategy_manager.py`)

**职责**：策略管理器（主进程）

**核心功能**：
1. **策略发现**：自动发现所有策略，加载 settings 和 worker 类
2. **作业构建**：构建 scan/simulate jobs
3. **多进程执行**：使用 ProcessWorker 执行多进程计算
4. **全局缓存管理**：管理股票列表、交易日等全局缓存

### 2. BaseStrategyWorker (`base_strategy_worker.py`)

**职责**：策略 Worker 基类（子进程）

**核心功能**：
1. **执行流程**：`run()` 方法处理单个股票的扫描或回测
2. **数据管理**：通过 `StrategyWorkerDataManager` 加载和过滤数据
3. **生命周期钩子**：提供多个钩子函数供用户扩展

**用户实现**：
- `scan_opportunity()` - 发现买入信号（必需）

**框架自动**：
- 自动执行回测（根据 goal 配置）
- 止盈止损处理

### 3. OpportunityEnumerator (`opportunity_enumerator.py`)

**职责**：完整枚举所有可能的投资机会（Layer 0）

**核心功能**：
1. **完整枚举**：每天都扫描，不跳过任何机会
2. **多进程并行**：使用 ProcessWorker 高效处理大量股票
3. **CSV 存储**：高性能 CSV 双表存储
4. **版本管理**：每次运行创建一个版本目录

### 4. Scanner (`scanner.py`)

**职责**：实时机会扫描（Layer 1）

**核心功能**：
1. **日期解析**：解析扫描日期（支持严格模式）
2. **缓存管理**：支持缓存机制，避免重复扫描
3. **Adapter 分发**：支持多个 Adapter 分发机会

### 5. PriceFactorSimulator (`price_factor_simulator.py`)

**职责**：价格因子模拟（Layer 2）

**核心功能**：
1. **基于 SOT**：使用 OpportunityEnumerator 的 SOT 结果
2. **单股独立**：每只股票独立模拟，适合多进程
3. **结果聚合**：聚合所有股票的结果，生成整体 summary

### 6. CapitalAllocationSimulator (`capital_allocation_simulator.py`)

**职责**：资金分配模拟（Layer 3）

**核心功能**：
1. **事件驱动**：基于事件流（trigger/target）执行
2. **账户管理**：管理账户、持仓、交易记录
3. **费用计算**：计算交易费用（佣金、印花税、过户费）
4. **分配策略**：支持多种资金分配策略

### 7. StrategyWorkerDataManager (`strategy_worker_data_manager.py`)

**职责**：子进程数据管理器，负责所有数据加载、缓存、过滤逻辑

**核心功能**：
1. **数据需求解析**：从 settings 自动解析数据需求
2. **技术指标计算**：根据配置自动计算技术指标
3. **数据过滤**：过滤数据到指定日期，避免"上帝模式"
4. **Required Data 加载**：加载 GDP、Tag 等依赖数据

---

## 核心模型

### Opportunity

投资机会模型（带实例方法的智能对象）：

```python
@dataclass
class Opportunity:
    # 触发信息
    trigger_date: str
    trigger_price: float
    trigger_conditions: Dict
    
    # 回测结果
    status: str  # active / closed / completed
    completed_targets: List[Dict]  # 完成的目标列表
    roi: float
    
    # 实例方法
    def check_targets(current_kline, goal_config) -> bool:
        """检查止盈止损目标"""
    
    def settle(last_kline, reason='backtest_end'):
        """强制结算（回测结束时）"""
```

### StrategySettings

策略配置模型（字典封装），包含：
- 数据配置：`data.base`, `data.adjust`, `data.indicators`
- 采样配置：`sampling.strategy`, `sampling.sampling_amount`
- 模拟器配置：`simulator.start_date`, `simulator.end_date`, `simulator.goal`
- 性能配置：`performance.max_workers`

### Account & Position

账户和持仓模型（CapitalAllocationSimulator 使用）：

```python
@dataclass
class Account:
    cash: float
    invested_amount: float
    positions: Dict[str, Position]

@dataclass
class Position:
    stock_id: str
    cost_basis: float
    remaining_shares: float
```

### Trade & Event

交易记录和事件模型：

```python
@dataclass
class Trade:
    trade_type: Literal['buy', 'sell']
    stock_id: str
    date: str
    price: float
    shares: int
    commission: float
    # ...

@dataclass
class Event:
    event_type: Literal['trigger', 'target']
    date: str
    stock_id: str
    opportunity: Optional[Dict]
    target: Optional[Dict]
```

---

## 运行时 Workflow

### 完整执行流程

```
1. 用户调用 StrategyManager 的方法
   │
   ├─▶ 2. Scanner 执行流程（Layer 1）
   │      │
   │      ├─▶ a. 解析扫描日期和股票列表
   │      │      - 使用 ScanDateResolver 解析日期
   │      │      - 使用 StockSamplingHelper 获取股票列表
   │      │
   │      ├─▶ b. 检查缓存（ScanCacheManager）
   │      │      - 如果缓存存在且有效，直接返回
   │      │
   │      ├─▶ c. 构建 scan jobs（每只股票一个 job）
   │      │      - 包含 stock_id, scan_date, settings 等
   │      │
   │      ├─▶ d. 多进程执行（ProcessWorker）
   │      │      │
   │      │      └─▶ 子进程执行流程：
   │      │             │
   │      │             ├─▶ 1. 初始化 BaseStrategyWorker
   │      │             │      - 加载股票信息
   │      │             │      - 初始化 StrategyWorkerDataManager
   │      │             │
   │      │             ├─▶ 2. 加载数据
   │      │             │      - 加载 K 线数据（到 scan_date）
   │      │             │      - 计算技术指标
   │      │             │      - 加载 required_entities
   │      │             │
   │      │             ├─▶ 3. 调用 scan_opportunity()
   │      │             │      - 用户实现的机会发现逻辑
   │      │             │      - 返回 Opportunity 或 None
   │      │             │
   │      │             └─▶ 4. 返回结果
   │      │
   │      ├─▶ e. 保存结果（OpportunityService）
   │      │      - 保存 Opportunity（JSON 格式）
   │      │      - 保存配置快照
   │      │
   │      └─▶ f. 分发到 Adapters（AdapterDispatcher）
   │             - 支持多个 Adapter（Console、File、Database 等）
   │
   ├─▶ 3. OpportunityEnumerator 执行流程（Layer 0）
   │      │
   │      ├─▶ a. 加载策略配置
   │      │      - StrategySettings → OpportunityEnumeratorSettings
   │      │      - 校验和补全默认值
   │      │
   │      ├─▶ b. 创建版本目录（VersionManager）
   │      │      - 自增版本 ID
   │      │      - 创建版本目录
   │      │
   │      ├─▶ c. 构建 jobs（每只股票一个 job）
   │      │      - 包含 stock_id, settings, start_date, end_date 等
   │      │
   │      ├─▶ d. 多进程执行（ProcessWorker）
   │      │      │
   │      │      └─▶ 子进程执行流程（OpportunityEnumeratorWorker）：
   │      │             │
   │      │             ├─▶ 1. 加载全量 K 线数据
   │      │             │      - 根据 settings.data.base/adjust
   │      │             │
   │      │             ├─▶ 2. 一次性计算技术指标
   │      │             │      - 根据 settings.data.indicators
   │      │             │
   │      │             ├─▶ 3. 加载 required_entities
   │      │             │      - GDP、Tag 等依赖数据
   │      │             │
   │      │             ├─▶ 4. 逐日迭代（核心逻辑）
   │      │             │      - 用游标获取"截至今天"的数据快照
   │      │             │      - 检查所有 active opportunities 是否完成
   │      │             │        （调用 opportunity.check_targets()）
   │      │             │      - 调用用户 scan_opportunity() 扫描新机会
   │      │             │      - 如果发现新机会，添加到 active_opportunities
   │      │             │
   │      │             ├─▶ 5. 回测结束时结算
   │      │             │      - 对所有未完成的 opportunities 调用 settle()
   │      │             │
   │      │             └─▶ 6. 写出 CSV（进程结束前）
   │      │                    - {stock_id}_opportunities.csv
   │      │                    - {stock_id}_targets.csv
   │      │
   │      ├─▶ e. 聚合 summary
   │      │      - 只收集 opportunity_count，不拉回全量数据
   │      │
   │      └─▶ f. 写入 metadata.json
   │             - 包含 settings_snapshot、统计信息等
   │
   ├─▶ 4. PriceFactorSimulator 执行流程（Layer 2）
   │      │
   │      ├─▶ a. 解析策略配置
   │      │      - StrategySettings → PriceFactorSimulatorConfig
   │      │
   │      ├─▶ b. 解析 SOT 版本目录（VersionManager）
   │      │      - 支持 "latest"、具体版本号、"test/latest" 等
   │      │
   │      ├─▶ c. 扫描 SOT 目录，获取股票列表
   │      │      - 从 CSV 文件列表提取股票 ID
   │      │
   │      ├─▶ d. 构建 jobs（每只股票一个 job）
   │      │      - 包含 stock_id, sot_version_dir, settings 等
   │      │
   │      ├─▶ e. 多进程执行（ProcessWorker）
   │      │      │
   │      │      └─▶ 子进程执行流程（PriceFactorSimulatorWorker）：
   │      │             │
   │      │             ├─▶ 1. 加载该股票的 SOT 数据
   │      │             │      - opportunities.csv
   │      │             │      - targets.csv
   │      │             │
   │      │             ├─▶ 2. 构建 Investment 列表
   │      │             │      - 从 Opportunity 创建 PriceFactorInvestment
   │      │             │      - 固定 1 股，无资金约束
   │      │             │
   │      │             ├─▶ 3. 计算统计信息
   │      │             │      - 胜率、平均 ROI、最大回撤等
   │      │             │
   │      │             └─▶ 4. 返回结果
   │      │
   │      ├─▶ f. 聚合所有股票的结果
   │      │      - 使用 ResultAggregator 聚合
   │      │
   │      └─▶ g. 保存结果（ResultPathManager）
   │             - summary_stock.json
   │             - summary_strategy.json
   │
   └─▶ 5. CapitalAllocationSimulator 执行流程（Layer 3）
          │
          ├─▶ a. 解析策略配置
          │      - StrategySettings → CapitalAllocationSimulatorConfig
          │
          ├─▶ b. 解析 SOT 版本目录（VersionManager）
          │
          ├─▶ c. 创建模拟器版本目录（VersionManager）
          │
          ├─▶ d. 构建事件流（DataLoader）
          │      - 从 SOT CSV 构建 Event 列表
          │      - 按日期排序
          │
          ├─▶ e. 初始化账户（Account）
          │      - 初始资金
          │      - 空持仓
          │
          ├─▶ f. 按时间轴执行（单进程主循环）
          │      │
          │      └─▶ 对每个日期：
          │             │
          │             ├─▶ 1. 处理卖出事件（先卖后买）
          │             │      - 遍历该日期的所有 target 事件
          │             │      - 检查持仓，执行卖出
          │             │      - 更新账户和持仓
          │             │      - 记录 Trade
          │             │
          │             ├─▶ 2. 处理买入事件
          │             │      - 遍历该日期的所有 trigger 事件
          │             │      - 根据分配策略决定买入数量
          │             │      - 检查资金是否足够
          │             │      - 执行买入
          │             │      - 更新账户和持仓
          │             │      - 记录 Trade
          │             │
          │             └─▶ 3. 更新权益曲线
          │                    - 计算当前总资产（现金 + 持仓市值）
          │
          ├─▶ g. 生成交易记录和权益曲线
          │      - trades.json
          │      - equity_curve.json
          │
          └─▶ h. 保存汇总结果（ResultPathManager）
                 - summary_stock.json
                 - summary_strategy.json
```

### StrategyManager 执行流程

**Scanner 模式**：

1. **加载策略配置**
   - 使用 `StrategyDiscoveryHelper` 发现策略
   - 加载 settings 和 worker 类

2. **解析扫描日期和股票列表**
   - 使用 `ScanDateResolver` 解析日期
   - 使用 `StockSamplingHelper` 获取股票列表

3. **检查缓存**
   - 使用 `ScanCacheManager` 检查缓存
   - 如果缓存有效，直接返回

4. **构建 scan jobs**
   - 使用 `JobBuilderHelper.build_scan_jobs()`
   - 每只股票一个 job

5. **多进程执行**
   - 使用 `ProcessWorker` 执行
   - 子进程调用 `BaseStrategyWorker.run()`

6. **保存结果**
   - 使用 `OpportunityService` 保存 Opportunity

7. **分发到 Adapters**
   - 使用 `AdapterDispatcher` 分发到多个 Adapter

**Simulator 模式**：

1. **加载策略配置**
2. **创建 Session**（使用 `SessionManager`）
3. **确定回测日期范围**
4. **构建 simulate jobs**
5. **多进程执行**
6. **收集结果**
7. **保存结果**

### BaseStrategyWorker 执行流程（子进程）

**Scan 模式**（`_execute_scan`）：

1. **初始化阶段**
   - 从 payload 提取信息
   - 初始化 `StrategyWorkerDataManager`
   - 调用 `on_init()` 钩子

2. **数据加载阶段**
   - 加载 K 线数据（到 scan_date）
   - 计算技术指标
   - 加载 required_entities

3. **扫描阶段**
   - 调用用户 `scan_opportunity()` 方法
   - 如果发现机会，创建 Opportunity 对象

4. **返回结果**

**Simulate 模式**（`_execute_simulate`）：

1. **初始化阶段**
   - 从 payload 提取 opportunity
   - 初始化 `StrategyWorkerDataManager`
   - 调用 `on_init()` 钩子

2. **数据加载阶段**
   - 加载 K 线数据（从 trigger_date 到 end_date）
   - 计算技术指标
   - 加载 required_entities

3. **回测阶段**
   - 遍历每个交易日
   - 对每个日期：
     - 获取历史数据并过滤到当前日期
     - 调用 `opportunity.check_targets()` 检查止盈止损
     - 如果完成，调用 `opportunity.settle()`

4. **结算阶段**
   - 如果回测结束时仍未完成，调用 `opportunity.settle()`

5. **返回结果**

### OpportunityEnumerator 执行流程

**主进程**（`OpportunityEnumerator.enumerate`）：

1. **加载策略配置**
   - `StrategySettings.from_dict()` → `OpportunityEnumeratorSettings.from_base()`
   - 校验和补全默认值

2. **创建版本目录**
   - 使用 `VersionManager.create_enumerator_version()`
   - 自增版本 ID

3. **构建 jobs**
   - 每只股票一个 job
   - 包含 stock_id, settings, start_date, end_date 等

4. **多进程执行**
   - 使用 `ProcessWorker` 执行

5. **聚合 summary**
   - 只收集 opportunity_count，不拉回全量数据

6. **写入 metadata.json**

**子进程**（`OpportunityEnumeratorWorker.run`）：

1. **加载全量 K 线数据**
2. **一次性计算技术指标**
3. **加载 required_entities**
4. **逐日迭代**（核心逻辑）：
   - 用游标获取"截至今天"的数据快照
   - 检查所有 active opportunities 是否完成
   - 调用用户 `scan_opportunity()` 扫描新机会
5. **回测结束时结算**
6. **写出 CSV**（进程结束前）

### PriceFactorSimulator 执行流程

**主进程**（`PriceFactorSimulator.run`）：

1. **解析策略配置**
   - `StrategySettings` → `PriceFactorSimulatorConfig`

2. **解析 SOT 版本目录**
   - 使用 `VersionManager.resolve_sot_version()`

3. **创建模拟器版本目录**
   - 使用 `VersionManager.create_price_factor_version()`

4. **扫描 SOT 目录，获取股票列表**

5. **构建 jobs**（每只股票一个 job）

6. **多进程执行**

7. **聚合所有股票的结果**
   - 使用 `ResultAggregator` 聚合

8. **保存结果**
   - 使用 `ResultPathManager` 保存

**子进程**（`PriceFactorSimulatorWorker.run`）：

1. **加载该股票的 SOT 数据**
   - 使用 `DataLoader.load_opportunities_and_targets()`

2. **构建 Investment 列表**
   - 从 Opportunity 创建 `PriceFactorInvestment`
   - 固定 1 股，无资金约束

3. **计算统计信息**
   - 胜率、平均 ROI、最大回撤等

4. **返回结果**

### CapitalAllocationSimulator 执行流程

**主进程**（`CapitalAllocationSimulator.run`）：

1. **解析策略配置**
   - `StrategySettings` → `CapitalAllocationSimulatorConfig`

2. **解析 SOT 版本目录**

3. **创建模拟器版本目录**

4. **构建事件流**
   - 使用 `DataLoader.build_event_stream()`
   - 从 SOT CSV 构建 Event 列表
   - 按日期排序

5. **初始化账户**
   - 创建 `Account` 对象
   - 设置初始资金

6. **按时间轴执行**（单进程主循环）：
   - 对每个日期：
     - 处理卖出事件（先卖后买）
     - 处理买入事件
     - 更新权益曲线

7. **生成交易记录和权益曲线**

8. **保存汇总结果**

---

## 数据流设计

### 数据流向图

```
┌─────────────────────────────────────────────────────────────┐
│                    Strategy 系统数据流                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Settings (配置文件)                                         │
│       │                                                      │
│       ▼                                                      │
│  StrategySettings (策略配置模型)                             │
│       │                                                      │
│       ├─▶ Scanner                                           │
│       │      │                                               │
│       │      ├─▶ StockSamplingHelper                        │
│       │      │      │                                       │
│       │      │      ▼                                       │
│       │      │   Stock List (采样后)                        │
│       │      │                                               │
│       │      ├─▶ StrategyWorkerDataManager                  │
│       │      │      │                                       │
│       │      │      ├─▶ 加载 K 线数据                        │
│       │      │      │      │                                │
│       │      │      │      ▼                                │
│       │      │      │   DataManager.stock.kline             │
│       │      │      │                                       │
│       │      │      ├─▶ 计算技术指标                        │
│       │      │      │      │                                │
│       │      │      │      ▼                                │
│       │      │      │   IndicatorService                    │
│       │      │      │                                       │
│       │      │      └─▶ 加载 Required Data                  │
│       │      │             │                                │
│       │      │             ▼                                │
│       │      │          DataManager (GDP, Tag 等)           │
│       │      │                                               │
│       │      ├─▶ scan_opportunity()                          │
│       │      │      │                                       │
│       │      │      ▼                                       │
│       │      │   Opportunity (status=active)                │
│       │      │                                               │
│       │      └─▶ OpportunityService                          │
│       │             │                                        │
│       │             ▼                                        │
│       │          JSON (scan results)                         │
│       │                                                       │
│       ├─▶ OpportunityEnumerator                             │
│       │      │                                               │
│       │      ├─▶ OpportunityEnumeratorWorker                 │
│       │      │      │                                        │
│       │      │      ├─▶ 加载全量 K 线数据                    │
│       │      │      │      │                                │
│       │      │      │      ▼                                │
│       │      │      │   DataManager.stock.kline             │
│       │      │      │                                       │
│       │      │      ├─▶ 计算技术指标                        │
│       │      │      │      │                                │
│       │      │      │      ▼                                │
│       │      │      │   IndicatorService                    │
│       │      │      │                                       │
│       │      │      ├─▶ 逐日迭代                            │
│       │      │      │      │                                │
│       │      │      │      ├─▶ check_targets()              │
│       │      │      │      │   (检查止盈止损)                │
│       │      │      │      │                                │
│       │      │      │      └─▶ scan_opportunity()           │
│       │      │      │          (扫描新机会)                  │
│       │      │      │                                       │
│       │      │      └─▶ 写出 CSV                            │
│       │      │             │                                │
│       │      │             ▼                                │
│       │      │          CSV (opportunities + targets)       │
│       │      │                                               │
│       │      └─▶ metadata.json                               │
│       │                                                       │
│       ├─▶ PriceFactorSimulator                               │
│       │      │                                               │
│       │      ├─▶ DataLoader.load_opportunities_and_targets()│
│       │      │      │                                       │
│       │      │      ▼                                       │
│       │      │   SOT CSV (opportunities + targets)          │
│       │      │                                               │
│       │      ├─▶ PriceFactorSimulatorWorker                  │
│       │      │      │                                       │
│       │      │      ├─▶ 从 Opportunity 创建 Investment      │
│       │      │      │      │                                │
│       │      │      │      ▼                                │
│       │      │      │   PriceFactorInvestment               │
│       │      │      │                                       │
│       │      │      └─▶ 计算统计信息                        │
│       │      │             │                                │
│       │      │             ▼                                │
│       │      │          Stock Summary                        │
│       │      │                                               │
│       │      ├─▶ ResultAggregator                            │
│       │      │      │                                       │
│       │      │      ▼                                       │
│       │      │   Strategy Summary                            │
│       │      │                                               │
│       │      └─▶ ResultPathManager                           │
│       │             │                                        │
│       │             ▼                                        │
│       │          JSON (summary_stock + summary_strategy)     │
│       │                                                       │
│       └─▶ CapitalAllocationSimulator                         │
│              │                                               │
│              ├─▶ DataLoader.build_event_stream()            │
│              │      │                                       │
│              │      ▼                                       │
│              │   Event Stream (按日期排序)                   │
│              │                                               │
│              ├─▶ 按时间轴执行                                │
│              │      │                                       │
│              │      ├─▶ 处理卖出事件                         │
│              │      │      │                                │
│              │      │      ├─▶ 更新 Account                 │
│              │      │      │                                │
│              │      │      └─▶ 记录 Trade                   │
│              │      │                                       │
│              │      ├─▶ 处理买入事件                         │
│              │      │      │                                │
│              │      │      ├─▶ AllocationStrategy           │
│              │      │      │   (决定买入数量)                │
│              │      │      │                                │
│              │      │      ├─▶ FeeCalculator                │
│              │      │      │   (计算费用)                    │
│              │      │      │                                │
│              │      │      ├─▶ 更新 Account                 │
│              │      │      │                                │
│              │      │      └─▶ 记录 Trade                   │
│              │      │                                       │
│              │      └─▶ 更新权益曲线                        │
│              │             │                                │
│              │             ▼                                │
│              │          Equity Curve                         │
│              │                                               │
│              └─▶ ResultPathManager                           │
│                     │                                        │
│                     ▼                                        │
│                  JSON (trades + equity_curve + summary)       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 数据加载流程

**StrategyWorkerDataManager**：

1. **解析数据需求**
   - 从 settings 提取 `data.base`, `data.adjust`, `data.indicators`
   - 提取 `required_entities`

2. **加载 Base Data（K 线）**
   - 根据 `data.base` 和 `data.adjust` 加载 K 线数据
   - 一次性加载到 `end_date`（或 `scan_date`）

3. **计算技术指标**
   - 根据 `data.indicators` 配置计算技术指标
   - 自动添加到 klines 中（如 `kline["ma5"]`, `kline["rsi"]`）

4. **加载 Required Data**
   - 加载 GDP、Tag 等依赖数据
   - 全量加载到 `end_date`

5. **数据过滤**
   - `filter_data_to_date(as_of_date)` 过滤数据到指定日期
   - 避免"上帝模式"问题

### 数据存储流程

**OpportunityEnumerator（CSV）**：

1. **子进程写出 CSV**
   - 每个子进程写出 `{stock_id}_opportunities.csv`
   - 每个子进程写出 `{stock_id}_targets.csv`

2. **主进程写入 metadata.json**
   - 包含 settings_snapshot、统计信息等

**Scanner/Simulators（JSON）**：

1. **保存 Opportunity/Investment**
   - 使用 `OpportunityService` 保存（Scanner）
   - 使用 `ResultPathManager` 保存（Simulators）

2. **保存 Summary**
   - `summary_stock.json`：单股汇总
   - `summary_strategy.json`：策略汇总

---

## 重要决策记录 (Decisions)

### 决策 1：四层架构设计

**问题**：如何组织 Scanner、Simulator、OpportunityEnumerator 的关系？

**决策**：采用四层架构，清晰分离不同层次的职责。

**理由**：
- **Layer 0（OpportunityEnumerator）**：完整枚举所有可能机会，供上层复用
- **Layer 1（Scanner）**：实时机会扫描，用于实盘提示
- **Layer 2（PriceFactorSimulator）**：价格因子模拟，验证信号质量
- **Layer 3（CapitalAllocationSimulator）**：资金分配模拟，真实资金约束

**影响**：
- 清晰的职责分离，便于理解和维护
- 上层可以复用下层的输出（如 Simulators 使用 Enumerator 的 SOT 结果）

---

### 决策 2：完整枚举 vs 主线回测

**问题**：OpportunityEnumerator 和 Simulator 的区别是什么？

**决策**：OpportunityEnumerator 做完整枚举，Simulator 做主线回测。

**理由**：
- **完整枚举**：每天都扫描，同时追踪多个机会，输出所有可能路径（供 Allocation 使用）
- **主线回测**：无持仓时才扫描，同时只能持有 1 个，输出单一路径（策略验证）

**影响**：
- OpportunityEnumerator 输出数据量大（CSV 格式，高性能）
- Simulator 输出数据量小（JSON 格式，易读）

---

### 决策 3：价格层面 vs 资金层面分离

**问题**：PriceFactorSimulator 和 CapitalAllocationSimulator 的区别是什么？

**决策**：PriceFactorSimulator 只关注价格变化，CapitalAllocationSimulator 考虑真实资金约束。

**理由**：
- **价格层面**：快速验证信号质量，无资金约束，适合快速迭代
- **资金层面**：真实资金约束，考虑费用、持仓限制，适合完整回测

**影响**：
- 用户可以先使用 PriceFactorSimulator 快速验证，再使用 CapitalAllocationSimulator 完整回测
- 两个模拟器可以共享 SOT 结果，避免重复计算

---

### 决策 4：CSV vs JSON 存储

**问题**：OpportunityEnumerator 使用 CSV，其他组件使用 JSON，为什么？

**决策**：OpportunityEnumerator 使用 CSV，其他组件使用 JSON。

**理由**：
- **CSV（OpportunityEnumerator）**：
  - 数据量大（5K-500K 条记录）
  - 需要高性能（加载快，0.1-0.2 秒）
  - Excel 可直接打开，便于查看
- **JSON（Scanner/Simulators）**：
  - 数据量小（几百到几千条记录）
  - 需要结构化数据（嵌套对象、数组）
  - 便于程序处理

**影响**：
- OpportunityEnumerator 需要 CSV 读写逻辑
- 其他组件需要 JSON 序列化/反序列化

---

### 决策 5：多进程 vs 单进程

**问题**：哪些组件使用多进程，哪些使用单进程？

**决策**：
- **多进程**：Scanner、OpportunityEnumerator、PriceFactorSimulator（每只股票独立，适合并行）
- **单进程**：CapitalAllocationSimulator（需要全局账户状态，不适合并行）

**理由**：
- **多进程场景**：每只股票的处理相互独立，可以并行执行
- **单进程场景**：需要全局账户状态，按时间顺序执行，不适合并行

**影响**：
- 多进程组件需要序列化 job payload
- 单进程组件需要按时间顺序处理事件

---

### 决策 6：事件驱动 vs 逐日迭代

**问题**：CapitalAllocationSimulator 使用事件驱动还是逐日迭代？

**决策**：使用事件驱动方式。

**理由**：
- **事件驱动**：只处理有事件的日期（trigger/target），效率高
- **逐日迭代**：需要遍历所有日期，效率低

**影响**：
- 需要构建事件流（从 SOT CSV 构建 Event 列表）
- 需要按日期排序事件

---

### 决策 7：Settings 两层架构

**问题**：如何组织 Settings？使用继承还是组合？

**决策**：使用两层架构（BaseSetting + 组件视图）。

**理由**：
- **BaseSetting（StrategySettings）**：通用配置，所有模块共用
- **组件视图（如 OpportunityEnumeratorSettings）**：组件专用配置，组合而非继承
- **优势**：职责清晰，便于验证和补全默认值

**影响**：
- 每个组件需要定义自己的 Settings 视图
- 需要实现 `from_base()` 方法

---

### 决策 8：技术指标自动计算

**问题**：技术指标是在框架层面自动计算，还是用户手动计算？

**决策**：框架层面自动计算。

**理由**：
- **统一管理**：框架统一计算，避免重复代码
- **性能优化**：一次性计算所有指标，避免重复计算
- **易于使用**：用户直接使用 `kline["ma5"]`，无需手动计算

**影响**：
- 需要在 `StrategyWorkerDataManager` 中实现指标计算逻辑
- 需要解析 `data.indicators` 配置

---

### 决策 9：数据过滤策略

**问题**：如何避免"上帝模式"问题（计算时看到未来数据）？

**决策**：框架层面强制过滤到 `as_of_date`。

**理由**：
- **保证计算一致性**：框架层面过滤，保证所有 StrategyWorker 都遵循相同规则
- **简化用户代码**：用户无需关心数据过滤，只需关注业务逻辑
- **减少出错可能**：避免用户忘记过滤数据

**影响**：
- 每次调用 `scan_opportunity()` 前都需要过滤数据（性能开销可接受）
- 用户无法访问未来数据（这是期望的行为）

---

### 决策 10：版本管理设计

**问题**：如何管理 SOT 版本和模拟器版本？

**决策**：使用统一的 VersionManager，支持版本目录和版本号。

**理由**：
- **版本对比**：可以对比不同版本的结果
- **版本清理**：可以清理旧版本，节省空间
- **版本追溯**：可以追溯历史版本

**影响**：
- 需要实现版本目录创建和解析逻辑
- 需要支持 "latest"、具体版本号、"test/latest" 等格式

---

## 配置设计

### 配置结构

> **详细配置结构请参考** `userspace/strategies/example/settings.py`，该文件包含完整的配置示例和每个属性的详细解释。

配置采用扁平化结构，主要包含：
- **顶层配置**：`name`, `description`, `is_enabled` 等
- **数据配置**：`data.base`, `data.adjust`, `data.indicators`, `data.required_entities`
- **采样配置**：`sampling.strategy`, `sampling.sampling_amount`, `sampling.pool`
- **模拟器配置**：`simulator.start_date`, `simulator.end_date`, `simulator.goal`
- **性能配置**：`performance.max_workers`

### 技术指标配置

**统一数组格式**：

```python
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
```

**工作流**：
1. 用户配置需要的指标
2. 框架自动计算并添加到 klines
3. 用户直接使用：`kline["ma5"]`, `kline["rsi"]`

### Pools/Blacklists 文件

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

**配置引用**（相对路径）：
```python
"pool": {
    "id_list_path": "pools/high_quality.txt"  # 相对于策略文件夹
}
```

---

## 数据存储

### 1. Opportunity 存储

**OpportunityEnumerator（CSV）**：
- 文件结构：`{stock_id}_opportunities.csv` + `{stock_id}_targets.csv`
- 优势：文件小（1-2 MB）、加载快（0.1-0.2 秒）、Excel 可直接打开

**Scanner（JSON）**：
- 文件结构：`results/scan/{date}/opportunities.json`
- 优势：结构化数据、便于程序处理

### 2. 结果存储

**PriceFactorSimulator（JSON）**：
- `summary_stock.json`：单股汇总
- `summary_strategy.json`：策略汇总

**CapitalAllocationSimulator（JSON）**：
- `trades.json`：交易记录
- `equity_curve.json`：权益曲线
- `summary_stock.json`：单股汇总
- `summary_strategy.json`：策略汇总

### 3. 版本管理

**版本目录结构**：
```
results/
├── opportunity_enums/
│   └── {strategy_name}/
│       ├── meta.json              # 版本管理元信息
│       └── {version_dir}/
│           ├── 0_metadata.json    # 本次运行的元信息
│           ├── {stock_id}_opportunities.csv
│           └── {stock_id}_targets.csv
├── price_factor/
│   └── {strategy_name}/
│       └── {version_dir}/
│           ├── summary_stock.json
│           └── summary_strategy.json
└── capital_allocation/
    └── {strategy_name}/
        └── {version_dir}/
            ├── trades.json
            ├── equity_curve.json
            ├── summary_stock.json
            └── summary_strategy.json
```

---

## 职责边界

### 组件职责矩阵

| 功能 | StrategyManager | BaseStrategyWorker | OpportunityEnumerator | Scanner | PriceFactorSimulator | CapitalAllocationSimulator |
|------|----------------|-------------------|---------------------|---------|---------------------|--------------------------|
| 策略发现 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 作业构建 | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| 多进程调度 | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ |
| 数据加载 | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 机会发现 | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ |
| 回测执行 | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| 资金管理 | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 结果保存 | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ |

---

## 设计原则

### 1. 职责单一

每个组件只负责自己的职责：
- StrategyManager 只管理
- BaseStrategyWorker 只处理单个股票
- OpportunityEnumerator 只枚举机会
- Scanner 只扫描实时机会
- Simulators 只模拟回测

### 2. 配置驱动

通过配置声明行为，而不是硬编码：
- 配置与代码分离
- 声明式配置，便于维护

### 3. 可扩展性

提供钩子函数和扩展点：
- 用户可以在不修改框架代码的情况下扩展功能
- 支持自定义数据加载和计算逻辑

### 4. 早期验证

在创建实例前就验证配置：
- 避免不必要的初始化开销
- 提前发现问题

### 5. 统一接口

所有 StrategyWorkers 遵循相同的接口：
- 便于统一管理和执行
- 降低学习成本

---

## 文件组织

### 目录结构

```
core/modules/strategy/
├── strategy_manager.py              # 策略管理器（主进程）
├── base_strategy_worker.py          # 策略 Worker 基类（子进程）
├── enums.py                          # 枚举定义
├── models/                           # 领域模型
│   ├── opportunity.py                # 机会模型
│   ├── strategy_settings.py          # 策略配置模型
│   ├── account.py                    # 账户模型
│   ├── trade.py                      # 交易记录模型
│   ├── event.py                      # 事件模型
│   └── investment.py                 # 投资模型
├── components/                       # 组件（执行器）
│   ├── opportunity_enumerator/       # Layer 0：机会枚举器
│   ├── scanner/                       # Layer 1：扫描器
│   ├── simulator/                    # Layer 2-3：模拟器
│   │   ├── price_factor/              # Layer 2：价格因子模拟器
│   │   └── capital_allocation/        # Layer 3：资金分配模拟器
│   ├── setting_management/           # 设置管理
│   ├── analyzer/                      # 分析器
│   ├── strategy_worker_data_manager.py # 数据管理器
│   ├── opportunity_service.py         # 机会服务
│   └── session_manager.py             # 会话管理器
├── helper/                            # 辅助函数
│   ├── strategy_discovery_helper.py   # 策略发现
│   ├── stock_sampling_helper.py       # 股票采样
│   ├── job_builder_helper.py          # 作业构建
│   └── statistics_helper.py           # 统计辅助
├── managers/                          # 管理器
│   ├── version_manager.py             # 版本管理器
│   ├── result_path_manager.py         # 结果路径管理器
│   └── data_loader.py                 # 数据加载器
├── docs/                              # 文档（旧文档，待整理）
└── ARCHITECTURE.md                    # 架构文档（本文档）
```

---

## 版本历史

### 版本 3.0 (2026-01-17)

**主要变更**：
- 重命名 DESIGN.md 为 ARCHITECTURE.md
- 添加"重要决策记录 (Decisions)"章节
- 添加"运行时 Workflow"章节，详细描述执行流程
- 添加"数据流设计"章节，详细描述数据流向
- 整合多个设计文档（DESIGN.md, ARCHITECTURE_DESIGN.md 等）
- 更新版本号和最后更新日期

### 版本 2.0 (2026-01-08)

**主要变更**：
- 引入四层架构设计
- 引入 OpportunityEnumerator（Layer 0）
- 重构 Settings 两层架构
- 引入 CSV 存储（OpportunityEnumerator）

### 版本 1.0 (初始版本)

**主要功能**：
- 基础 Strategy 系统实现
- Scanner 和 Simulator 支持
- 多进程执行支持

---

**文档结束**
