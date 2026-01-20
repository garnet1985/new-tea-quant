# DataManager 模块概览

> **提示**：本文档提供快速上手指南。如需了解详细的设计理念、架构设计和决策记录，请参考 [architecture.md](./architecture.md) 和 [decisions.md](./decisions.md)。

## 📋 模块简介

`DataManager` 是系统的统一数据访问层，负责管理所有数据的读取、写入和协调。它提供了统一的 API 接口，屏蔽了底层数据库的复杂性，让上层业务代码可以专注于业务逻辑。

**核心特性**：
- 声明式数据库结构（Schema 驱动）
- 自动建表和管理
- 多数据库支持（PostgreSQL/MySQL/SQLite）
- 三层架构：Manager（Facade）→ Service（Coordinator）→ Model（私有）

> 详细的设计理念和架构说明请参考 [architecture.md](./architecture.md)

## 📦 模块的组件

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

---

## 📁 模块的文件夹结构

```
core/modules/data_manager/
├── __init__.py                 # 模块导出
├── data_manager.py             # DataManager 主类（Facade）
├── enums.py                    # 枚举定义
│
├── base_tables/               # 基础表 Models（私有）
│   ├── stock_list/
│   ├── stock_kline/
│   ├── corporate_finance/
│   ├── gdp/
│   ├── price_indexes/
│   ├── shibor/
│   ├── lpr/
│   ├── system_cache/
│   ├── tag_scenario/
│   ├── tag_definition/
│   ├── tag_value/
│   └── ...
│
├── data_services/             # 数据服务层
│   ├── __init__.py            # BaseDataService 基类
│   ├── data_service.py        # DataService 主类（Coordinator）
│   │
│   ├── stock/                 # 股票相关服务
│   │   ├── __init__.py
│   │   ├── stock_service.py   # StockService（统一入口）
│   │   └── sub_services/      # 子服务目录
│   │       ├── __init__.py
│   │       ├── list_service.py        # ListService
│   │       ├── kline_service.py        # KlineService
│   │       ├── tag_service.py         # TagDataService
│   │       └── corporate_finance_service.py  # CorporateFinanceService
│   │
│   ├── macro/                 # 宏观经济服务
│   │   ├── __init__.py
│   │   └── macro_service.py  # MacroService
│   │
│   ├── calendar/              # 日历服务
│   │   ├── __init__.py
│   │   └── calendar_service.py # CalendarService
│   │
│   └── ui_transit/            # UI 过渡服务
│       └── investment/        # 投资相关服务
│           ├── investment_data_service.py
│           └── target_calculator.py
│
└── helpers/                   # 通用辅助工具
    └── filtering.py
```

---

## 🚀 模块的使用方法

### 基本使用

```python
from core.modules.data_manager import DataManager

# 直接创建并使用（自动单例，自动初始化）
data_mgr = DataManager(is_verbose=True)

# 属性访问（创建后即可使用）
klines = data_mgr.stock.kline.load('000001.SZ', term='daily')
gdp = data_mgr.macro.load_gdp('2020Q1', '2024Q4')
latest_date = data_mgr.calendar.get_latest_completed_trading_date()
```

### 数据访问示例

```python
# K线数据（通过 KlineService）
klines = data_mgr.stock.kline.load('000001.SZ', term='daily', start_date='20240101')
qfq_klines = data_mgr.stock.kline.load_qfq('000001.SZ', start_date='20240101')

# 股票基础信息（StockService 核心职责）
stock_info = data_mgr.stock.load_info('000001.SZ')
stock_with_price = data_mgr.stock.load_with_latest_price('000001.SZ')

# 股票列表（通过 ListService）
stock_list = data_mgr.stock.list.load(filtered=True)
all_stocks = data_mgr.stock.list.load_all()
filtered_by_industry = data_mgr.stock.list.load_by_industry('银行', filtered=True)

# 标签数据（通过 TagDataService）
scenario = data_mgr.stock.tags.load_scenario('my_scenario')
tag_def = data_mgr.stock.tags.load('tag_name', scenario_id=1)

# 财务数据（通过 CorporateFinanceService）
finance = data_mgr.stock.corporate_finance.load('000001.SZ', quarter='2024Q1')
finance_by_category = data_mgr.stock.corporate_finance.load_by_category('000001.SZ', '2024Q1', 'profitability')

# 宏观数据
gdp = data_mgr.macro.load_gdp('2020Q1', '2024Q4')
cpi = data_mgr.macro.load_cpi('202001', '202412')
shibor = data_mgr.macro.load_shibor('20240101', '20241231')

# 交易日
latest_date = data_mgr.calendar.get_latest_completed_trading_date()
```


---

## 📚 模块详细文档

- **[architecture.md](./architecture.md)**：架构文档，包含详细的技术设计、核心组件、运行时 Workflow
- **[decisions.md](./decisions.md)**：重要决策记录，包含架构设计决策和理由

> **阅读建议**：先阅读本文档快速上手，然后阅读 [architecture.md](./architecture.md) 了解详细设计，最后阅读 [decisions.md](./decisions.md) 了解设计决策。

---

**文档结束**
