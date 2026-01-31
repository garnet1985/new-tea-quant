# DataManager 架构设计文档

## 📋 概述

`DataManager` 是系统的统一数据访问层，负责管理所有数据的读取、写入和协调。本文档描述了 `DataManager` 模块的架构设计、设计理念和使用方式。

## 🎯 设计理念

### 核心原则

1. **Facade 模式**：`DataManager` 作为薄门面层，仅负责单例管理、数据库初始化和服务入口暴露，不包含业务逻辑
2. **职责分离**：每个服务专注于特定领域，严格遵循单一职责原则，不提供跨服务的便捷委托方法
3. **明确性优先**：遵循 Python "Explicit is better than implicit" 原则，通过嵌套属性访问明确指定服务路径
4. **封装性保证**：底层 Model 类完全私有化，外部代码只能通过 DataService 层访问数据
5. **性能优化**：优先使用 SQL JOIN 查询减少数据库访问次数，在数据库层面完成过滤和关联

### 设计背景

在系统演进过程中，数据访问逻辑逐渐分散，出现了以下问题：
- 数据访问方法散落在多个模块，缺乏统一入口
- 业务逻辑与数据访问耦合，难以维护和测试
- 底层 Model 直接暴露，导致外部代码依赖实现细节
- 多次数据库查询效率低下，缺乏优化

为了解决这些问题，我们设计了分层的数据访问架构：
- **Facade 层**：提供统一入口，管理生命周期
- **Coordinator 层**：协调跨服务请求
- **Service 层**：封装领域特定的数据访问逻辑
- **Model 层**：底层数据表操作，完全封装

## 🏗️ 架构概览

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

### 三层架构

1. **Facade 层（DataManager）**
   - 进程级单例管理
   - 数据库初始化和连接池管理
   - 表模型自动发现和注册
   - 属性访问入口（`data_mgr.stock`, `data_mgr.macro`, `data_mgr.calendar`）

2. **Coordinator 层（DataService）**
   - 管理所有子服务实例
   - 统一服务访问入口（data_mgr.stock / macro / calendar 等）

3. **Service 层（领域服务）**
   - 领域特定的数据访问逻辑
   - 封装业务方法
   - 处理跨表查询和数据组装
   - 优化 SQL 查询（JOIN、WHERE 条件等）

## 📁 目录结构

```
data_manager/
├── ARCHITECTURE.md              # 本文档
├── README.md                   # 使用说明
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

## 🔑 核心组件

### 1. DataManager（Facade）

**职责**：
- 进程级单例管理（线程安全）
- 数据库初始化（DatabaseManager、连接池、表结构）
- 表模型自动发现（Base Tables）和注册（用户自定义表）
- 提供属性访问入口（`stock`, `macro`, `calendar`, `service`）

**设计理念**：
- 作为薄门面层，不包含业务逻辑
- 所有业务逻辑委托给 DataService 层
- 提供 `get_table()` 方法供内部服务使用（不对外暴露）

**使用方式**：
```python
from app.core.modules.data_manager import DataManager

# 直接创建并使用（自动单例，自动初始化）
data_mgr = DataManager(is_verbose=True)

# 属性访问（创建后即可使用）
klines = data_mgr.stock.kline.load('000001.SZ', term='daily')
gdp = data_mgr.macro.load_gdp('2020Q1', '2024Q4')
latest_date = data_mgr.calendar.get_latest_completed_trading_date()
```

### 2. DataService（Coordinator）

**职责**：
- 管理所有子服务实例（`stock`, `macro`, `calendar` 等）
- 统一服务访问入口

**设计理念**：
- 作为服务协调器，处理需要跨多个服务的复杂请求
- 不包含领域特定的业务逻辑
- 所有领域逻辑都在对应的 Service 中

**使用方式**：
```python
# 通过 DataManager 访问
data_service = data_mgr.service
# 按需通过 data_mgr.stock / data_mgr.macro 等组装数据；业务模块（Tag、Strategy）使用各自的数据管理器
```

### 3. StockService

**职责**：
- 提供单个股票的基础信息查询（`load_info`）
- 提供跨表查询（组合 `stock_list` 和 `stock_kline` 的数据）
- 作为子服务的入口，提供子服务属性访问

**设计理念**：
- 严格遵循单一职责：只负责股票基础信息和跨表查询
- 不提供便捷委托方法：所有子服务功能必须通过子服务访问
- 子服务包括：`list`（股票列表）、`kline`（K线）、`tags`（标签）、`corporate_finance`（财务）

**子服务**：
- `list`: 股票列表服务（加载、过滤、按类型/行业查询）
- `kline`: K线数据服务（加载、保存、QFQ调整、多周期）
- `tags`: 标签系统服务（scenario、tag_definition、tag_value）
- `corporate_finance`: 财务数据服务（按季度、按类别、趋势分析）

**使用方式**：
```python
# 股票基础信息（StockService 核心职责）
stock_info = data_mgr.stock.load_info('000001.SZ')
stock_with_price = data_mgr.stock.load_with_latest_price('000001.SZ')

# 股票列表（通过 list 服务）
stock_list = data_mgr.stock.list.load(filtered=True)
all_stocks = data_mgr.stock.list.load_all()
filtered_by_board = data_mgr.stock.list.load_by_board('主板', filtered=True)

# K线数据（通过 kline 服务）
klines = data_mgr.stock.kline.load('000001.SZ', term='daily')
qfq_klines = data_mgr.stock.kline.load_qfq('000001.SZ', start_date='20240101')

# 标签数据（通过 tags 服务）
scenario = data_mgr.stock.tags.load_scenario('my_scenario')
tag_def = data_mgr.stock.tags.load('tag_name', scenario_id=1)

# 财务数据（通过 corporate_finance 服务）
finance = data_mgr.stock.corporate_finance.load('000001.SZ', quarter='2024Q1')
finance_by_category = data_mgr.stock.corporate_finance.load_by_category('000001.SZ', '2024Q1', 'profitability')
```

### 4. ListService

**职责**：
- 股票列表的查询和操作
- 支持全量股票列表、过滤股票列表
- 支持按类型、行业等条件筛选

**设计理念**：
- 使用 SQL WHERE 条件在数据库层面过滤，而不是加载所有数据到内存
- 提供灵活的过滤规则配置

### 5. KlineService

**职责**：
- K线数据的加载和保存
- QFQ（前复权）调整计算
- 多周期K线加载
- 复权因子处理

**设计理念**：
- 使用 SQL JOIN 优化 QFQ 查询，一次查询获取所有需要的数据
- 提供回退机制确保查询失败时的健壮性
- 统一日期格式处理

### 6. TagDataService

**职责**：
- 标签系统管理（scenario、tag_definition、tag_value）
- 标签计算和查询
- 标签值批量操作

**设计理念**：
- 提取公共逻辑（如 `_update_entity`）减少代码重复
- 使用 JOIN 优化删除操作
- 统一日期格式转换

### 7. CorporateFinanceService

**职责**：
- 企业财务数据加载
- 按类别查询（盈利能力、成长能力、偿债能力等）
- 多季度趋势分析

**设计理念**：
- 使用 `INDICATOR_CATEGORIES` 映射统一管理指标分类
- 简化字段过滤逻辑
- 统一方法命名（移除冗余实体名）

### 8. MacroService

**职责**：
- 宏观经济数据加载
- GDP、CPI、PPI、PMI、货币供应量
- Shibor、LPR利率数据

**设计理念**：
- 使用 `INDICATOR_CATEGORIES` 映射统一管理指标分类
- 提取通用方法（如 `_load_price_indexes`, `_load_rate_data`）减少重复代码
- 简化无风险利率计算逻辑

### 9. CalendarService

**职责**：
- 交易日查询和缓存
- 交易日历管理

**设计理念**：
- 多级缓存机制：内存缓存（进程内快速访问）+ 数据库缓存（持久化）
- 多 Fallback 机制：东方财富 API → 新浪财经 API → 系统猜测
- 线程安全：使用线程锁保证缓存访问的线程安全
- 智能刷新：每天只请求一次 API，降低外部依赖

## 🔌 API 访问模式

### 属性访问模式

所有数据服务通过属性访问，遵循以下模式：

```python
# 一级服务（直接访问）
data_mgr.stock
data_mgr.macro
data_mgr.calendar
data_mgr.service  # DataService 协调器

# 二级服务（StockService 的子服务）
data_mgr.stock.list
data_mgr.stock.kline
data_mgr.stock.tags
data_mgr.stock.corporate_finance

# 方法调用
data_mgr.stock.kline.load(...)           # K线数据
data_mgr.stock.tags.load_scenario(...)   # 标签数据
data_mgr.stock.corporate_finance.load(...)  # 财务数据
```

### 设计原则

1. **严格职责分离**：每个服务专注于自己的领域，不提供便捷委托方法
   ```python
   # StockService 只负责股票基础信息
   data_mgr.stock.load_info(...)
   data_mgr.stock.load_with_latest_price(...)
   
   # 所有子服务功能通过子服务访问
   data_mgr.stock.list.load(...)
   data_mgr.stock.kline.load_qfq(...)
   data_mgr.stock.tags.load_scenario(...)
   data_mgr.stock.corporate_finance.load(...)
   ```

2. **明确性优先**：遵循 Python "Explicit is better than implicit" 原则，明确指定服务
   ```python
   # ✅ 明确指定服务
   data_mgr.stock.kline.load_qfq(...)
   data_mgr.stock.corporate_finance.load(...)
   
   # ❌ 避免隐式路由
   # data_mgr.stock.load_klines(...)  # 已移除，避免混淆
   ```

3. **方法命名规范**：移除冗余的实体名，使方法名更简洁
   ```python
   # ✅ 简洁命名
   data_mgr.stock.list.load(...)  # 而不是 load_stock_list
   data_mgr.stock.kline.load_qfq(...)  # 而不是 load_qfq_klines
   data_mgr.stock.corporate_finance.load(...)  # 而不是 load_financials
   ```

## 📊 数据访问示例

### 基础数据加载

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
tag_values = data_mgr.stock.tags.save_value(tag_value_data)

# 财务数据（通过 CorporateFinanceService）
finance = data_mgr.stock.corporate_finance.load('000001.SZ', quarter='2024Q1')
finance_by_category = data_mgr.stock.corporate_finance.load_by_category('000001.SZ', '2024Q1', 'profitability')
finance_trend = data_mgr.stock.corporate_finance.load_trend('000001.SZ', '2023Q1', '2024Q4')

# 宏观数据
gdp = data_mgr.macro.load_gdp('2020Q1', '2024Q4')
cpi = data_mgr.macro.load_cpi('202001', '202412')
shibor = data_mgr.macro.load_shibor('20240101', '20241231')
macro_snapshot = data_mgr.macro.load_macro_snapshot('20241201')

# 交易日
latest_date = data_mgr.calendar.get_latest_completed_trading_date()
```

### 按需组装数据

数据按需通过各 Service 加载，业务模块（Tag、Strategy）使用各自的数据管理器（TagWorkerDataManager、StrategyWorkerDataManager）组装 klines、macro、corporate_finance 等，例如：

```python
klines = data_mgr.stock.kline.load_multiple(stock_id, {'terms': ['daily'], 'start_date': '20240101', 'end_date': '20241231'})
macro = data_mgr.macro.load_gdp('2024Q1', '2024Q4')
finance = data_mgr.stock.corporate_finance.load_by_categories(stock_id, ['profitability'], '20240101', '20241231')
```

## 🔧 表模型管理

### 自动发现机制

**Base Tables（基础表）**：
- 路径固定：`app/core/modules/data_manager/base_tables/`
- 自动发现：系统启动时自动扫描并注册所有 `DbBaseModel` 子类
- 无需手动注册：所有基础表模型自动可用

**用户自定义表**：
- 通过 `register_table()` 方法注册
- 接受表文件夹路径，自动发现 Model 类
- 注册成功后返回 Model 实例

**设计理念**：
- 减少手动配置，提高开发效率
- 统一表模型访问方式（`get_table()`）
- 缓存机制避免重复发现

### 表模型访问

```python
# 内部服务使用（不对外暴露）
model = data_manager.get_table('stock_kline')  # 获取 Model 类
klines = model.load("id = %s", ('000001.SZ',))

# 外部代码应通过 DataService 访问
klines = data_mgr.stock.kline.load('000001.SZ')
```

## 🎨 设计原则总结

1. **单一职责**：每个服务专注于特定领域，不提供便捷委托方法
2. **分层清晰**：Facade → Coordinator → Service → Model
3. **属性访问**：统一的属性访问模式，直观易用
4. **明确性优先**：明确指定服务，避免隐式路由
5. **性能优化**：优先使用 SQL JOIN 和 WHERE 条件，减少数据库访问和内存占用
6. **封装性保证**：底层 Model 完全私有化，外部只能通过 DataService 访问
7. **代码复用**：提取公共逻辑，减少重复代码

## 📝 技术细节

### 初始化机制

**自动初始化设计**：
- `DataManager` 在 `__init__` 中自动调用 `initialize()`，创建后即可使用
- `initialize()` 方法是幂等的，多次调用只会执行一次
- 显式的 `initialize()` 方法保留是为了：
  1. **特殊情况控制**：某些场景（如测试、延迟初始化）可能需要手动控制初始化时机
  2. **向后兼容**：保留接口便于未来扩展或特殊需求
  3. **接口清晰性**：显式的方法让接口意图更清晰

**使用建议**：
- **常规使用**：直接创建即可，无需手动调用 `initialize()`
  ```python
  data_mgr = DataManager(is_verbose=True)
  klines = data_mgr.stock.kline.load('000001.SZ')  # 创建后即可使用
  ```
- **特殊场景**：如需延迟初始化或测试场景，可以显式调用
  ```python
  data_mgr = DataManager(is_verbose=False)
  # ... 其他操作 ...
  data_mgr.initialize()  # 需要时才初始化
  ```

### 单例模式

- **进程级单例**：`DataManager` 使用进程级单例，多进程环境下每个进程有独立实例
- **线程安全**：使用线程锁保证单例创建的线程安全
- **延迟初始化**：部分 Model 使用延迟初始化，减少启动开销

### 缓存策略

- **内存缓存**：`CalendarService` 使用进程内内存缓存，快速访问最新交易日
- **数据库缓存**：交易日数据持久化到 `system_cache` 表，降低 API 调用频率
- **智能刷新**：每天只请求一次外部 API，过期后自动刷新

### 性能优化

- **SQL JOIN**：`KlineService.load_qfq()` 使用 JOIN 一次查询获取所有数据
- **SQL WHERE**：`ListService.load_by_board()` 和 `load_by_industry()` 在数据库层面过滤（基于 industry_id/board_id）
- **批量操作**：支持批量保存和更新，减少数据库访问次数

### 错误处理

- **回退机制**：关键查询（如 `load_qfq`）提供回退方案，确保健壮性
- **异常捕获**：所有数据库操作和 API 调用都有异常处理
- **日志记录**：关键操作都有日志记录，便于问题排查

## 🔒 封装性保证

### Model 访问限制

**重要原则**：底层的 `base_tables` Model 类不应被外部代码直接访问。

#### ❌ 错误做法

```python
# 不要直接导入 Model
from app.core.modules.data_manager.base_tables import StockKlineModel

# 不要直接实例化 Model
kline_model = StockKlineModel()
klines = kline_model.load_by_date_range(...)

# 不要通过服务访问私有 Model
klines = data_mgr.stock._stock_kline.load_by_date_range(...)  # 错误！
```

#### ✅ 正确做法

```python
# 通过 DataService 层访问
klines = data_mgr.stock.kline.load('000001.SZ', start_date='20240101')
qfq_klines = data_mgr.stock.kline.load_qfq('000001.SZ', start_date='20240101')
```

### 实现细节

1. **私有属性**：所有 DataService 中的 Model 实例都使用 `_` 前缀（如 `_stock_kline`, `_gdp`），表示私有属性
2. **内部访问**：Model 只在 DataService 内部使用，不对外暴露
3. **封装边界**：`DataManager.get_table()` 方法仅供内部使用，外部不应直接调用

### 为什么需要封装？

1. **解耦**：外部代码不依赖底层 Model 实现，只依赖稳定的 DataService API
2. **灵活性**：可以自由重构 Model 层，而不影响外部代码
3. **一致性**：所有数据访问都通过统一的 DataService 接口，保证行为一致
4. **可维护性**：清晰的边界使得代码更容易理解和维护
