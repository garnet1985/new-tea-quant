# Stocks-Py - A股量化策略回测框架

## 项目概述

Stocks-Py 是一个专注于A股市场的量化策略回测框架，提供完整的策略开发、回测、分析和优化功能。系统采用插件化策略设计，支持灵活的投资目标管理和自定义结算逻辑。

## 核心特性

- 🎯 **投资目标管理系统**: 灵活的分阶段止盈止损、动态止损、保本止损配置
- 🔌 **插件化策略**: 策略模块独立，包含逻辑、配置、分析和结果
- 📊 **完整回测框架**: 多进程模拟、投资生命周期管理、完整的收益分析
- 🧠 **自定义结算**: 支持策略自定义止盈止损逻辑
- 📈 **多策略支持**: RTB反转策略、HL历史低点、动量策略、均值回归等
- 🗄️ **自动数据管理**: 统一的数据加载接口，支持Tushare、AKShare
- ⚙️ **配置化策略**: 零代码实现复杂止盈止损逻辑
- 🔄 **三层回测架构**: 机会枚举 → 价格因子模拟 → 资金分配模拟
- 💰 **资金分配模拟器**: 真实资金约束下的组合回测，支持等资金/等股/Kelly分配策略
- 📉 **价格因子模拟器**: 无资金约束的信号质量评估，快速验证策略有效性
- 🏷️ **版本管理系统**: 独立的版本控制，支持多轮回测结果对比

## 系统架构

```
stocks-py/
├── app/                       # 核心应用模块
│   ├── core/                 # 核心模块
│   │   ├── modules/          # 业务模块
│   │   │   ├── strategy/     # 策略框架
│   │   │   │   ├── components/
│   │   │   │   │   ├── opportunity_enumerator/  # 机会枚举器
│   │   │   │   │   ├── price_factor_simulator/  # 价格因子模拟器
│   │   │   │   │   └── capital_allocation_simulator/  # 资金分配模拟器
│   │   │   │   ├── models/   # 策略模型（Opportunity, StrategySettings）
│   │   │   │   └── helper/   # 辅助工具（采样、统计等）
│   │   │   ├── data_manager/ # 数据管理器（Facade + Service 架构）
│   │   │   │   ├── data_services/  # 数据服务层
│   │   │   │   │   ├── stock/     # 股票服务（List, Kline, Tag, Finance）
│   │   │   │   │   ├── macro/    # 宏观经济服务
│   │   │   │   │   └── calendar/ # 交易日历服务
│   │   │   │   └── base_tables/  # 基础表 Models（私有）
│   │   │   ├── data_source/  # 数据源管理（Handler + Provider 架构）
│   │   │   │   ├── handlers/ # 数据获取处理器
│   │   │   │   └── providers/ # 第三方数据源（Tushare, AKShare等）
│   │   │   ├── tag/          # 标签系统（Scenario + Tag 架构）
│   │   │   │   └── core/     # 标签核心（TagManager, BaseTagWorker）
│   │   │   └── indicator/   # 技术指标计算（基于 pandas-ta-classic）
│   │   └── infra/            # 基础设施
│   │       ├── db/           # 数据库管理（连接池、ORM、Schema）
│   │       └── worker/       # 多进程/多线程工具
│   ├── userspace/            # 用户策略空间
│   │   └── strategies/       # 策略实现
│   │       ├── example/     # 示例策略
│   │       └── ...          # 其他策略
│   └── analyzer_legacy/      # 传统分析框架（兼容，逐步迁移）
│       └── strategy/        # 传统策略实现
├── utils/                     # 通用工具
│   ├── db/                   # 数据库工具（已迁移到 core/infra/db）
│   ├── worker/               # Worker 工具（已迁移到 core/infra/worker）
│   ├── date/                 # 日期工具
│   ├── progress/              # 进度追踪
│   └── icon/                 # 图标服务
├── config/                    # 配置文件
│   └── database/            # 数据库配置
├── tools/                     # 辅助工具
├── fed/                       # 前端界面 (React)
├── bff/                       # 后端API (Flask)
└── start.py                   # 应用入口
```

## 快速开始

### 1. 环境要求

- Python 3.9+
- 数据库（三选一）：
  - PostgreSQL 12+（推荐，支持多进程并发读）
  - MySQL 5.7+ / MariaDB 10.3+
  - SQLite 3.26+（开发/测试环境）
- 8GB+ RAM (推荐)

### 2. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd stocks-py

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置数据库

创建 `config/database/db_config.json`（或复制 `db_config.example.json`）:
```json
{
    "database_type": "postgresql",
    "postgresql": {
        "host": "localhost",
        "port": 5432,
        "database": "stocks_py",
        "user": "postgres",
        "password": "your_password"
    },
    "batch_write": {
        "enable": true,
        "batch_size": 1000,
        "flush_interval": 5.0
    }
}
```

**支持的数据库类型**：
- `postgresql`: PostgreSQL（推荐，支持多进程并发读）
- `mysql`: MySQL/MariaDB
- `sqlite`: SQLite（开发/测试环境）

**旧配置格式（自动兼容）**：
```json
{
    "db_path": "data/stocks.db"  # 自动识别为 SQLite
}
```
或
```json
{
    "host": "localhost",
    "database": "stocks_py",
    "user": "root",
    "password": "password",
    "port": 3306  # 3306=MySQL, 5432=PostgreSQL
}
```

**注意**：如果使用 PostgreSQL，需要先安装并启动 PostgreSQL 服务。

### 4. 初始化数据库

```bash
# 使用 PostgreSQL（推荐）
python3 -c "from app.core.infra.db import DatabaseManager; db = DatabaseManager(); db.initialize(); print('✅ 数据库初始化完成')"

# 或使用 MySQL
# 或使用 SQLite（自动创建文件）
```

### 5. 运行应用

```bash
python3 start.py
```

---

## 数据库配置详解

### PostgreSQL 配置（推荐）

```json
{
    "database_type": "postgresql",
    "postgresql": {
        "host": "localhost",
        "port": 5432,
        "database": "stocks_py",
        "user": "postgres",
        "password": "your_password",
        "pool_size": 10
    }
}
```

**优势**：
- ✅ 支持多进程并发读（解决单文件数据库的并发限制）
- ✅ 性能优秀，适合生产环境
- ✅ 功能丰富（JSON、全文搜索等）

### MySQL 配置

```json
{
    "database_type": "mysql",
    "mysql": {
        "host": "localhost",
        "port": 3306,
        "database": "stocks_py",
        "user": "root",
        "password": "your_password",
        "charset": "utf8mb4"
    }
}
```

### SQLite 配置（开发/测试）

```json
{
    "database_type": "sqlite",
    "sqlite": {
        "db_path": "data/stocks.db",
        "timeout": 5.0
    }
}
```

**注意**：SQLite 不支持多进程并发写，适合单进程开发环境。

---

## 旧版配置兼容

如果你有旧的配置文件（`config/database/db_conf.json`），系统会自动识别并转换：

- `db_path` → 自动识别为 SQLite
- `host` + `database` → 根据端口自动识别（3306=MySQL, 5432=PostgreSQL）

---

## 数据库迁移

如果从旧数据库迁移数据，请参考：
- `tools/migrate_duckdb_to_postgresql.py` - 数据迁移脚本（支持从 DuckDB 迁移到 PostgreSQL）
- `tools/verify_migration_data.py` - 数据验证脚本
- `POSTGRESQL_MIGRATION_CHECKLIST.md` - 迁移清单和进度

---

## 快速开始（旧版配置）

编辑 `config/app_config.json`:
```json
{
    "database": {
        "host": "localhost",
        "user": "root",
        "password": "your_password",
        "database": "stocks_py",
        "port": 3306
    }
}
```

### 4. 配置数据源

#### Tushare配置
```bash
# 创建token文件
echo "your_tushare_token" > app/core/modules/data_source/providers/tushare/auth/token.txt
```

### 5. 运行策略回测

#### 主要命令

```bash
# 机会枚举（生成投资机会）
python start.py enumerate --strategy example

# 价格因子模拟（评估信号质量，无资金约束）
python start.py price_factor --strategy example

# 资金分配模拟（真实资金约束下的组合回测）
python start.py capital_allocation --strategy example

# 数据更新（更新股票行情、标签等数据）
python start.py renew

# 扫描机会（根据策略筛选当前符合条件的股票）
python start.py scan --strategy example

# 标签计算（计算并存储标签）
python start.py tag
python start.py tag --scenario market_value  # 指定场景

# 查看帮助
python start.py --help
```

#### 快捷命令

```bash
python start.py -c    # 快捷: 扫描（等价于 scan）
python start.py -s    # 快捷: 模拟（等价于 simulate）
python start.py -r    # 快捷: 更新（等价于 renew）
python start.py -a    # 快捷: 分析（等价于 analysis）
python start.py -t    # 快捷: 标签（等价于 tag）
python start.py -e    # 快捷: 枚举（等价于 enumerate）
python start.py -p    # 快捷: 价格因子模拟（等价于 price_factor）
```

#### 组合命令

```bash
# 按顺序执行多个命令
python start.py renew scan          # 更新数据 → 扫描
python start.py renew simulate       # 更新数据 → 模拟
python start.py -r -c -s            # 快捷: 全流程（更新 → 扫描 → 模拟）
```

#### 命令参数

```bash
# 指定策略
python start.py enumerate --strategy example
python start.py price_factor --strategy example
python start.py capital_allocation --strategy example

# 指定标签场景
python start.py tag --scenario market_value

# 详细输出模式
python start.py enumerate --strategy example --verbose
```

## 核心概念

### 三层回测架构

框架采用三层回测架构，从信号生成到资金管理，逐层验证策略有效性：

#### 1. 机会枚举器 (OpportunityEnumerator)
**职责**: 扫描全市场，识别符合策略条件的投资机会

- **输入**: 股票列表、策略配置、K线数据
- **输出**: `opportunities.csv` 和 `targets.csv`（每只股票）
- **特点**: 
  - 多进程并行扫描
  - 支持采样模式（test/）和全量模式（sot/）
  - 版本管理，支持多轮枚举结果对比

#### 2. 价格因子模拟器 (PriceFactorSimulator)
**职责**: 评估信号质量，不考虑资金约束

- **输入**: 枚举器生成的 SOT 结果
- **输出**: 每只股票的收益统计、整体策略表现
- **特点**:
  - 每只股票独立模拟（1股级回放）
  - 无资金约束，快速验证策略有效性
  - 多进程执行，高效处理大量股票
  - 独立版本管理，支持多轮模拟对比

#### 3. 资金分配模拟器 (CapitalAllocationSimulator)
**职责**: 真实资金约束下的组合回测

- **输入**: 枚举器生成的 SOT 结果
- **输出**: 交易记录、权益曲线、组合统计
- **特点**:
  - 单进程执行，保证资金一致性
  - 支持多种分配策略：等资金、等股、Kelly公式
  - 真实的交易费用计算
  - 组合持仓限制和风险控制
  - 独立版本管理，支持多轮回测对比

**工作流程**:
```
策略配置 → 机会枚举 → 价格因子模拟 → 资金分配模拟
         (SOT结果)   (信号质量)      (真实回测)
```

### 投资目标管理系统

这是框架的核心特性，允许通过配置实现复杂的止盈止损逻辑：

```python
# settings.py
"goal": {
    "stop_loss": {
        # 止损阶段
        "stages": [
            {"name": "loss20%", "ratio": -0.2, "close_invest": True}
        ],
        # 保本止损（盈利后回调到成本价）
        "break_even": {"name": "break_even", "ratio": 0},
        # 动态止损（从最高点回调）
        "dynamic": {"name": "dynamic", "ratio": -0.1}
    },
    "take_profit": {
        # 止盈阶段
        "stages": [
            {"name": "win10%", "ratio": 0.1, "sell_ratio": 0.2},
            {"name": "win20%", "ratio": 0.2, "sell_ratio": 0.2, "set_stop_loss": "break_even"},
            {"name": "win30%", "ratio": 0.3, "sell_ratio": 0.2},
            {"name": "win40%", "ratio": 0.4, "sell_ratio": 0.2, "set_stop_loss": "dynamic"}
        ]
    }
}
```

**特性**:
- ✅ 分阶段止盈止损
- ✅ 盈利后切换止损策略（保本/动态）
- ✅ 自动仓位管理（sell_ratio）
- ✅ 配置化，零代码

### 插件化策略

每个策略是独立的模块：

```
example/
├── settings.py          # 策略配置
├── README.md            # 策略文档
└── results/             # 回测结果
    ├── opportunity_enums/  # 枚举结果
    │   ├── test/        # 测试模式结果
    │   └── sot/         # 全量模式结果（Source of Truth）
    └── simulations/     # 模拟结果
        ├── price_factor/    # 价格因子模拟
        └── capital_allocation/  # 资金分配模拟
```

**配置结构** (`settings.py`):
```python
settings = {
    "name": "example",
    "core": {...},           # 策略核心参数
    "data": {...},          # 数据配置
    "goal": {...},          # 投资目标（止盈止损）
    "sampling": {...},      # 股票采样配置
    "enumerator": {...},    # 枚举器配置
    "simulator": {...},     # 价格因子模拟器配置
    "capital_simulator": {...},  # 资金分配模拟器配置
    "fees": {...}          # 交易成本配置
}
```

### 自定义结算逻辑

策略可以覆盖默认的结算逻辑：

```python
# Momentum策略示例：周期调仓
@staticmethod
def should_take_profit(...) -> Tuple[bool, Dict]:
    # 自定义止盈逻辑
    if is_last_day_of_period():
        return True, close_all_positions()
    return False, investment
```

## 内置策略

### 1. RTB (Reverse Trend Bet) - 反转策略
**理念**: 识别趋势反转点，买入反转上涨的股票

**核心参数** (基于ML分析):
- 波动率: 2%-15%
- 反转后成交量放大: ≥1.5倍
- 均线收敛度: <5%
- 价格相对均线位置: ±5-8%

**特点**:
- ML增强版本，基于7407个样本训练
- 小盘股偏好（成功率89.1% > 大盘股86.6%）
- 完整的分阶段止盈止损

### 2. HL (HistoricLow) - 历史低点策略
**理念**: 在股票接近历史低点时买入

**特点**:
- 基于3/5/8年历史低点分析
- 动态建仓比例（凯莉公式）
- 完整的统计分析

### 3. Momentum - 动量策略
**理念**: 周期调仓，买入过去L天涨幅最大的股票

**特点**:
- 支持月度/季度/年度调仓
- 动量计算：`(MA_short - MA_long) / MA_long`
- 横截面动量，选择前N%股票

### 4. MeanReversion - 均值回归策略
**理念**: 价格偏离均值时买入，回归均值时卖出

**特点**:
- 基于历史分位数的偏离度计算
- 动态止盈止损

### 5. Random - 随机策略
**理念**: 作为基准策略，随机买入股票

**特点**:
- 5%随机投资概率
- 动态止损（基于20日波动率）

## 策略开发

### 创建新策略

1. **创建策略目录**
```bash
mkdir app/userspace/strategies/MyStrategy
cd app/userspace/strategies/MyStrategy
```

2. **实现策略类**
```python
# MyStrategy.py
from app.core.modules.analyzer.components.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self):
        self.name = "MyStrategy"
        self.key = "MS"
        self.version = "1.0.0"
        super().__init__()
    
    @staticmethod
    def scan_opportunity(stock_info, required_data, settings):
        # 扫描投资机会
        # 返回 Opportunity 或 None
        pass
```

3. **配置策略参数**
```python
# settings.py
settings = {
    "name": "MyStrategy",
    "core": {
        # 策略核心参数
    },
    "data": {
        "base_price_source": "stock_kline_daily",
        "adjust_type": "qfq",
        "indicators": {...}
    },
    "goal": {
        # 止盈止损配置（顶层配置，跨模块使用）
        "expiration": {...},
        "stop_loss": {...},
        "take_profit": {...}
    },
    "sampling": {
        "strategy": "continuous",
        "sampling_amount": 20
    },
    "enumerator": {
        "use_sampling": True,
        "max_workers": "auto"
    },
    "simulator": {
        "sot_version": "latest",
        "use_sampling": True
    },
    "capital_simulator": {
        "sot_version": "latest",
        "initial_capital": 1_000_000,
        "allocation": {
            "mode": "equal_capital",
            "max_portfolio_size": 10
        }
    }
}
```

### 策略生命周期

```python
# 1. 前置处理
on_before_simulate(stock_list, settings)

# 2. 扫描机会
scan_opportunity(stock_info, required_data, settings)

# 3. 自定义结算（可选）
should_stop_loss(...) / should_take_profit(...)

# 4. 汇总处理
on_summarize_session(base_session_summary, stock_summaries, settings)

# 5. 报告生成
present_extra_session_report(session_summary, settings)
```

## Core Modules 核心模块

框架的核心功能由 `app/core/modules/` 下的模块提供，采用模块化设计，职责清晰。

### 1. DataManager - 数据管理器

**职责**: 统一的数据访问层，管理所有数据的读取、写入和协调

**架构设计**:
```
DataManager (Facade)
    │
    ├── DataService (Coordinator)
    │       │
    │       ├── StockService
    │       │   ├── ListService (股票列表)
    │       │   ├── KlineService (K线数据)
    │       │   ├── TagDataService (标签系统)
    │       │   └── CorporateFinanceService (财务数据)
    │       │
    │       ├── MacroService (宏观经济)
    │       │
    │       └── CalendarService (交易日历)
    │
    └── BaseTables (Models - 私有)
```

**设计理念**:
- **Facade 模式**: DataManager 作为薄门面层，仅负责单例管理和服务入口
- **职责分离**: 每个服务专注于特定领域，严格遵循单一职责原则
- **明确性优先**: 通过嵌套属性访问明确指定服务路径（如 `data_mgr.service.stock.kline.load_qfq()`）
- **封装性保证**: 底层 Model 类完全私有化，外部只能通过 DataService 访问

**使用示例**:
```python
from app.core.modules.data_manager import DataManager

data_mgr = DataManager(is_verbose=False)

# 加载K线数据（前复权）
klines = data_mgr.service.stock.kline.load_qfq(
    stock_id='000001.SZ',
    start_date='20200101',
    end_date='20231231'
)

# 加载股票列表
stocks = data_mgr.service.stock.list.load(filtered=True)

# 加载宏观经济数据
gdp = data_mgr.service.macro.gdp.load(start_date='20200101')

# 获取最新交易日
latest_date = data_mgr.service.calendar.get_latest_completed_trading_date()
```

**核心服务**:
- **StockService**: 股票相关数据（列表、K线、标签、财务）
- **MacroService**: 宏观经济数据（GDP、CPI、价格指数等）
- **CalendarService**: 交易日历和日期工具

### 2. DataSource - 数据源管理

**职责**: 统一管理从多个第三方数据源获取数据的过程

**核心概念**:
```
dataSource (框架需要的数据类型)
    ↓ 对应唯一
schema (数据格式规范)
    ↓ 可以有多个实现
handler (获取方法定义)
    ↓ 可能使用多个
provider (第三方数据源)
```

**支持的数据源**:
- **Tushare**: 专业金融数据API（主要）
- **AKShare**: 开源金融数据接口（备用）
- **EastMoney**: 东方财富API（特定数据）
- **Sina**: 新浪财经API（特定数据）

**特性**:
- ✅ **配置驱动**: 通过 `mapping.json` 配置 handler 的启用、依赖和参数
- ✅ **运行时切换**: 通过配置文件切换 handler，无需修改代码
- ✅ **多实现共存**: 一个 dataSource 可以有多个 handler
- ✅ **易于扩展**: 添加新 dataSource 或 handler 不影响现有代码

**使用示例**:
```python
from app.core.modules.data_source import DataSourceManager

dsm = DataSourceManager()

# 获取股票列表
stock_list = dsm.get_data('stock_list')

# 获取K线数据
kline_data = dsm.get_data('kline', stock_id='000001.SZ', start_date='20200101')
```

### 3. Strategy - 策略框架

**职责**: 提供完整的策略开发、枚举、模拟框架

**核心组件**:
- **OpportunityEnumerator**: 机会枚举器，扫描全市场识别投资机会
- **PriceFactorSimulator**: 价格因子模拟器，评估信号质量（无资金约束）
- **CapitalAllocationSimulator**: 资金分配模拟器，真实资金约束下的组合回测
- **StrategyManager**: 策略管理器，统一管理策略生命周期
- **BaseStrategyWorker**: 策略 Worker 基类，在子进程中执行策略逻辑

**模型**:
- **Opportunity**: 投资机会模型，包含触发条件、目标、状态等
- **StrategySettings**: 策略配置模型，统一管理策略参数

**辅助工具**:
- **StockSamplingHelper**: 股票采样工具（连续采样、随机采样等）
- **StatisticsHelper**: 统计分析工具

### 4. Tag - 标签系统

**职责**: 预计算和存储实体属性/状态的框架

**核心概念**:
- **Scenario（业务场景）**: 一个业务逻辑单元，对应一个 TagWorker
- **Tag Definition（标签定义）**: Scenario 产生的具体标签
- **Tag Value（标签值）**: 标签的实际计算结果

**数据模型**:
```
tag_scenario (业务场景层)
    │
    ├─▶ tag_definition (标签定义层)
            │
            └─▶ tag_value (标签值层)
```

**特性**:
- ✅ **配置驱动**: 通过 Python 配置文件定义业务场景
- ✅ **多进程支持**: 支持多进程并行计算标签
- ✅ **增量计算**: 支持增量更新，只计算新增数据
- ✅ **灵活扩展**: 继承 BaseTagWorker 实现自定义标签计算逻辑

**使用示例**:
```python
from app.core.modules.tag import TagManager

tag_mgr = TagManager()

# 执行所有场景
tag_mgr.run_all_scenarios()

# 执行指定场景
tag_mgr.run_scenario('market_value')
```

### 5. Indicator - 技术指标计算

**职责**: 提供技术指标计算服务，基于 `pandas-ta-classic`

**特性**:
- ✅ **通用模块**: 所有模块（strategy, tag, analyzer 等）都可使用
- ✅ **Proxy 模式**: 代理 pandas-ta-classic，不搬运代码
- ✅ **便捷 API**: 8 个常用指标的快速调用方法
- ✅ **通用 API**: 支持所有 150+ 指标
- ✅ **静态工具类**: 无需实例化

**支持的指标**:
- 趋势指标：SMA, EMA, WMA, DEMA, TEMA 等
- 动量指标：RSI, MACD, CCI, CMO, ROC 等
- 波动指标：ATR, BBANDS, NATR 等
- 成交量指标：OBV, AD, ADOSC 等

**使用示例**:
```python
from app.core.modules.indicator import IndicatorService

# 便捷 API（常用指标）
ma20 = IndicatorService.ma(klines, length=20)
rsi14 = IndicatorService.rsi(klines, length=14)
macd = IndicatorService.macd(klines)

# 通用 API（所有指标）
cci = IndicatorService.calculate('cci', klines, length=20)
```

### 6. Adapter - 适配器系统

**职责**: 提供统一的适配器接口，支持多种输出格式

**特性**:
- 支持多种适配器（Console、File、Database 等）
- 可扩展的适配器架构
- 统一的适配器管理接口

## 模块间关系

### 数据流向

```
DataSource (外部数据源: Tushare, AKShare等)
    ↓
DataManager (统一数据访问层)
    ├── StockService (股票数据)
    ├── MacroService (宏观经济)
    └── CalendarService (交易日历)
    ↓
Strategy Components (策略组件)
    ├── OpportunityEnumerator (机会枚举)
    ├── PriceFactorSimulator (价格因子模拟)
    └── CapitalAllocationSimulator (资金分配模拟)
    ↓
Results (回测结果: JSON文件)
```

### 典型工作流程

1. **数据准备阶段**
   - DataSource 从第三方 API 获取数据（Tushare/AKShare）
   - DataManager 存储和管理数据到数据库
   - Tag 系统计算标签（可选，用于策略筛选）

2. **策略开发阶段**
   - 在 `userspace/strategies/` 下创建策略目录
   - 配置 `settings.py`（核心参数、数据配置、投资目标等）
   - 实现策略逻辑（扫描机会、自定义结算等）

3. **回测执行阶段**
   - `enumerate`: 扫描全市场，生成投资机会（SOT结果）
   - `price_factor`: 评估信号质量，无资金约束（快速验证）
   - `capital_allocation`: 真实资金约束下的组合回测（完整回测）

4. **结果分析阶段**
   - 查看生成的 JSON 文件（汇总统计、交易记录、权益曲线）
   - 分析收益曲线和统计指标
   - 对比不同版本的结果（版本管理系统）

### 模块依赖关系

- **Strategy** 依赖: DataManager, Indicator, Database, Worker
- **Tag** 依赖: DataManager, Indicator, Database, Worker
- **DataManager** 依赖: Database, DataSource
- **DataSource** 依赖: Database (用于缓存)
- **Indicator** 独立模块，无依赖

## Infrastructure 基础设施

框架的基础设施由 `app/core/infra/` 提供，包括数据库管理和 Worker 系统。

### 1. Database - 数据库管理

**职责**: 提供数据库连接池、ORM 模型、表结构管理

**核心组件**:
- **DatabaseManager**: 数据库连接池管理，支持多进程安全
- **DbBaseModel**: ORM 基类，提供统一的数据库操作接口
- **DbSchemaManager**: 表结构管理，自动创建和验证表结构

**特性**:
- ✅ **连接池管理**: 自动管理数据库连接，支持多进程环境
- ✅ **ORM 模型**: 基于字典的轻量级 ORM，支持复杂查询
- ✅ **自动表管理**: 基于 JSON Schema 自动创建和验证表结构
- ✅ **多进程安全**: 子进程自动重置连接，避免连接状态错误

**使用示例**:
```python
from app.core.infra.db.db_base_model import DbBaseModel

class MyModel(DbBaseModel):
    table_name = "my_table"
    
    def find_by_id(self, id):
        return self.find_one({"id": id})
```

### 2. Worker - 多进程/多线程工具

**职责**: 提供并行执行框架，支持多进程和多线程

**核心组件**:
- **ProcessWorker**: 多进程 Worker，支持队列模式和批处理模式
- **FuturesWorker**: 多线程 Worker，基于 ThreadPoolExecutor

**特性**:
- ✅ **多进程支持**: 基于 `multiprocessing`，适合 CPU 密集型任务
- ✅ **多线程支持**: 基于 `concurrent.futures`，适合 I/O 密集型任务
- ✅ **自动资源管理**: 子进程自动重置数据库连接
- ✅ **进度追踪**: 内置进度条和结果统计
- ✅ **错误处理**: 完善的错误处理和结果收集

**使用示例**:
```python
from app.core.infra.worker.multi_process import ProcessWorker

def job_executor(payload):
    # 处理单个任务
    return result

worker = ProcessWorker(
    max_workers=4,
    job_executor=job_executor
)

jobs = [{"id": i, "payload": data} for i, data in enumerate(data_list)]
worker.run_jobs(jobs)
results = worker.get_results()
```

## 回测结果

### 查看结果

```bash
# 枚举结果
cd app/userspace/strategies/example/results/opportunity_enums/sot/
ls -lt | head  # 查看最新版本

# 价格因子模拟结果
cd app/userspace/strategies/example/results/simulations/price_factor/
cat 1_20260112_161317/0_session_summary.json

# 资金分配模拟结果
cd app/userspace/strategies/example/results/capital_allocation/
cat 1_20260112_161317/summary_strategy.json
cat 1_20260112_161317/trades.json  # 交易记录
cat 1_20260112_161317/portfolio_timeseries.json  # 权益曲线
```

### 结果指标

**机会枚举器**:
- 每只股票的机会数量
- 机会触发日期和价格
- 目标达成情况

**价格因子模拟器**:
- 总投资数
- 胜率
- 平均ROI
- 年化收益率
- 平均持仓天数
- 每只股票的详细统计

**资金分配模拟器**:
- 初始资金和最终权益
- 总收益率和年化收益率
- 最大回撤
- 交易记录（买入/卖出）
- 权益曲线（每日）
- 组合持仓统计
- 按股票的盈亏统计

## 进阶功能

### 使用技术指标

```python
from app.core.modules.indicator import IndicatorService
from app.core.modules.data_manager import DataManager

data_mgr = DataManager()

# 在策略中使用
klines = data_mgr.service.stock.kline.load_qfq('000001.SZ')
rsi = IndicatorService.rsi(klines, length=14)
ma20 = IndicatorService.ma(klines, length=20)

# 策略逻辑
if rsi[-1] < 30 and klines[-1]['close'] > ma20[-1]:
    return Opportunity(...)
```

### 使用标签系统

```python
from app.core.modules.tag import TagManager
from app.core.modules.data_manager import DataManager

# 执行标签计算
tag_mgr = TagManager()
tag_mgr.run_scenario('market_value')

# 在策略中查询标签
data_mgr = DataManager()
tags = data_mgr.service.stock.tag.get_tags(
    stock_id='000001.SZ',
    scenario='market_value',
    date='20231231'
)
```

### 自定义数据源

```python
# 1. 在 data_source/handlers/ 下创建新的 handler
# 2. 在 data_source/providers/ 下创建新的 provider
# 3. 在 mapping.json 中配置 handler 和 provider 的映射关系
# 4. 通过 DataSourceManager 使用
```

### 创建自定义标签场景

```python
from app.core.modules.tag import BaseTagWorker

class MyTagWorker(BaseTagWorker):
    def calculate_tag(self, entity_id, date):
        # 计算标签逻辑
        return {
            'tag_name': tag_value
        }

# 在 scenarios/ 目录下创建配置文件
# 通过 TagManager 执行
```

### 扩展数据服务

```python
# 在 data_manager/data_services/ 下创建新的服务
# 继承 BaseDataService
# 在 DataService 中注册新服务
```

### 自定义报告

```python
@staticmethod
def present_extra_session_report(session_summary, settings):
    """自定义报告输出"""
    print("\n🎯 自定义报告")
    # 你的报告逻辑
```

### 自动分析

```python
# settings.py
"simulation": {
    "analysis": True  # 自动运行分析
}

# 实现analysis方法
def analysis(self):
    # 分析逻辑
    return analysis_result
```

## 性能优化

### 数据库优化
- **连接池管理**: 使用 DBUtils 管理连接，支持多进程环境
- **批量操作**: 支持批量插入、批量更新，减少数据库交互
- **SQL 优化**: 优先使用 JOIN 查询，减少查询次数
- **索引优化**: 自动创建和维护索引，提升查询性能

### 并行处理
- **多进程模拟**: 自动并行化处理多只股票（OpportunityEnumerator, PriceFactorSimulator）
- **多线程支持**: 适合 I/O 密集型任务（数据获取、标签计算）
- **自动资源管理**: 子进程自动重置数据库连接，避免连接状态错误

### 数据加载优化
- **批量数据加载**: 一次性加载所需数据，减少数据库查询
- **缓存机制**: DataSource 支持缓存，避免重复获取
- **增量计算**: Tag 系统支持增量更新，只计算新增数据
- **内存优化**: 及时释放不需要的数据，避免内存泄漏

### 进度追踪
- **实时进度显示**: 内置进度条和结果统计
- **性能分析**: 支持性能分析，追踪数据库查询次数和执行时间

## 开发指南

### 代码规范
- **PEP 8**: 遵循 Python 代码风格指南
- **类型注解**: 使用 `typing` 模块提供类型提示
- **日志记录**: 使用 `logging` 模块，合理设置日志级别
- **文档字符串**: 为公共 API 提供清晰的文档字符串
- **最小化注释**: 代码即文档，只注释必要部分

### 模块开发规范

#### 创建新的数据服务
```python
# 1. 在 data_services/ 下创建服务目录
# 2. 继承 BaseDataService
# 3. 实现领域特定的数据访问方法
# 4. 在 DataService 中注册服务
```

#### 创建新的策略组件
```python
# 1. 在 strategy/components/ 下创建组件目录
# 2. 实现核心逻辑（枚举器、模拟器等）
# 3. 创建配置模型（如需要）
# 4. 在 start.py 中添加 CLI 入口
```

#### 创建新的标签场景
```python
# 1. 继承 BaseTagWorker
# 2. 实现 calculate_tag 方法
# 3. 创建场景配置文件
# 4. 在 scenarios/ 目录下注册
```

### 提交规范
```
feat: 添加新功能
fix: 修复bug
refactor: 代码重构
docs: 更新文档
chore: 构建工具变动
perf: 性能优化
test: 添加测试
style: 代码格式调整
```

### 测试建议
- 使用虚拟环境进行测试
- 使用采样模式快速验证功能
- 检查生成的 JSON 文件格式
- 验证数据库查询性能

## 更新日志

### v4.0.0 (2026-01-XX)
- 🎯 **三层回测架构**: 机会枚举 → 价格因子模拟 → 资金分配模拟
- 💰 **资金分配模拟器**: 真实资金约束下的组合回测，支持等资金/等股/Kelly分配策略
- 📉 **价格因子模拟器**: 无资金约束的信号质量评估，快速验证策略有效性
- 🏷️ **版本管理系统**: 独立的版本控制，支持多轮回测结果对比
- ⚙️ **配置系统重构**: 统一的配置结构，移除向后兼容，更清晰的字段命名
- 🔄 **模块化优化**: 代码拆分和重构，提高可维护性
- 📊 **结果输出优化**: 详细的交易记录、权益曲线、汇总统计
- 🗄️ **DataManager 重构**: Facade + Service 架构，职责分离，明确性优先
- 📦 **DataSource 系统**: Handler + Provider 架构，配置驱动，易于扩展，支持多数据源切换
- 🏷️ **Tag 系统**: Scenario + Tag 三层架构，配置驱动的标签计算框架，支持多进程并行计算
- 📈 **Indicator 模块**: 基于 pandas-ta-classic，支持 150+ 技术指标，通用模块设计
- 🔧 **Infrastructure 完善**: Database 和 Worker 系统优化，多进程安全，自动资源管理

### v3.0.0 (2024-XX-XX)
- 重构策略框架，支持插件化策略
- 新增投资目标管理系统
- 新增自定义结算逻辑支持
- 新增Momentum、MeanReversion策略
- 优化RTB策略（ML增强版）
- 完善文档和示例

### v2.0.0 (2023-XX-XX)
- 从Node.js迁移到Python
- 重构系统架构
- 添加多数据源支持

## 相关资源

### 文档
- [DataManager 架构文档](app/core/modules/data_manager/ARCHITECTURE.md)
- [DataSource 设计文档](app/core/modules/data_source/docs/DESIGN.md)
- [Strategy 框架设计](app/core/modules/strategy/docs/DESIGN.md)
- [Tag 系统设计](app/core/modules/tag/docs/DESIGN.md)
- [数据库模块文档](app/core/infra/db/README.md)

### 示例策略
- [Example 策略](app/userspace/strategies/example/) - 完整的策略示例，包含配置和文档

### 工具脚本
- `tools/` - 辅助工具脚本
  - `fix_incomplete_kline_data.py` - 修复不完整的K线数据
  - `generate_comparison_excel.py` - 生成对比Excel
  - `improve_stock_sampling.py` - 改进股票采样

## 许可证

MIT License

---

**免责声明**: 本项目仅供学习和研究使用，不构成投资建议。投资有风险，入市需谨慎。
