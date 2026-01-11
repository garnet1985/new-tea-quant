# DataManager 架构设计文档

## 📋 概述

`DataManager` 是系统的统一数据访问层，负责管理所有数据的读取、写入和协调。本文档描述了重构后的 `DataManager` 模块架构、设计原则和使用方式。

## 🎯 设计目标

1. **模块化**：清晰的服务边界，每个服务专注于特定领域
2. **易用性**：统一的属性访问方式，直观的 API 设计
3. **可扩展性**：易于添加新的数据服务
4. **可维护性**：代码结构清晰，职责明确

## 🏗️ 架构概览

```
DataManager (Facade)
    │
    ├── DataService (Coordinator)
    │       │
    │       ├── StockService
    │       │   ├── KlineService
    │       │   ├── TagService
    │       │   └── CorporateFinanceService
    │       │
    │       ├── MacroService
    │       │
    │       └── CalendarService
    │
    └── BaseTables (Models)
```

### 三层架构

1. **Facade 层（DataManager）**
   - 单例模式管理
   - 数据库初始化
   - 属性访问入口（`data_mgr.stock`, `data_mgr.macro`, `data_mgr.calendar`）

2. **Coordinator 层（DataService）**
   - 管理所有子服务
   - 提供跨服务协调方法（如 `prepare_data`）
   - 统一访问入口

3. **Service 层（StockService, MacroService, CalendarService）**
   - 领域特定的数据访问逻辑
   - 封装业务方法
   - 处理跨表查询和数据组装

## 📁 目录结构

```
data_manager/
├── ARCHITECTURE.md              # 本文档
├── README.md                   # 使用说明
├── __init__.py                 # 模块导出
├── data_manager.py             # DataManager 主类（Facade）
├── enums.py                    # 枚举定义
│
├── base_tables/               # 基础表 Models
│   ├── stock_list/
│   ├── stock_kline/
│   ├── stock_labels/
│   ├── corporate_finance/
│   ├── gdp/
│   ├── price_indexes/
│   ├── shibor/
│   ├── lpr/
│   └── ...
│
├── data_services/             # 数据服务层
│   ├── __init__.py            # BaseDataService 基类
│   ├── data_service.py        # DataService 主类（Coordinator）
│   │
│   ├── stock/                 # 股票相关服务
│   │   ├── __init__.py
│   │   ├── stock_service.py   # StockService（统一入口）
│   │   ├── kline_service.py  # KlineService（K线数据）
│   │   ├── tag_service.py    # TagService（标签系统）
│   │   ├── finance_service.py # CorporateFinanceService（财务数据）
│   │   └── helpers/
│   │       └── adjustment.py  # 复权计算工具
│   │
│   ├── macro/                 # 宏观经济服务
│   │   ├── __init__.py
│   │   └── macro_service.py  # MacroService
│   │
│   └── calendar/              # 日历服务
│       ├── __init__.py
│       └── calendar_service.py # CalendarService
│
└── helpers/                   # 通用辅助工具
    ├── filtering.py
    └── target_calculator.py
```

## 🔑 核心组件

### 1. DataManager（Facade）

**职责**：
- 单例管理（进程级单例）
- 数据库初始化（DatabaseManager、连接池、表结构）
- 提供属性访问入口（`stock`, `macro`, `calendar`）
- 向后兼容的便捷方法

**使用方式**：
```python
from app.core.modules.data_manager import DataManager

# 初始化（自动单例）
data_mgr = DataManager(is_verbose=True)
data_mgr.initialize()

# 属性访问
klines = data_mgr.stock.load_klines('000001.SZ', term='daily')
gdp = data_mgr.macro.load_gdp('2020Q1', '2024Q4')
latest_date = data_mgr.calendar.get_latest_trading_date()
```

### 2. DataService（Coordinator）

**职责**：
- 管理所有子服务（`stock`, `macro`, `calendar`）
- 提供跨服务协调方法（如 `prepare_data`）
- 统一访问入口

**使用方式**：
```python
# 通过 DataManager 访问
data_service = data_mgr.service

# 直接访问子服务
klines = data_service.stock.kline.load_klines('000001.SZ')
tags = data_service.stock.tags.load_scenario('my_scenario')
```

### 3. StockService

**职责**：
- 股票相关数据的统一入口
- 管理子服务（`kline`, `tags`, `corporate_finance`）
- 提供常用方法的便捷访问

**子服务**：
- `kline`: K线数据（加载、保存、QFQ调整、多周期）
- `tags`: 标签系统（scenario、tag_definition、tag_value）
- `corporate_finance`: 财务数据（按季度、按类别、趋势分析）

**使用方式**：
```python
# 常用方法（直接访问）
klines = data_mgr.stock.load_klines('000001.SZ', term='daily')
tags = data_mgr.stock.load_tags('000001.SZ', date='20241201')
finance = data_mgr.stock.load_corporate_finance('000001.SZ', categories=['profitability'])

# 复杂方法（通过子服务）
qfq_klines = data_mgr.stock.kline.load_qfq_klines('000001.SZ', start_date='20240101')
scenario_tags = data_mgr.stock.tags.load_scenario('my_scenario')
```

### 4. KlineService

**职责**：
- K线数据的加载和保存
- QFQ（前复权）调整计算
- 多周期K线加载
- 复权因子处理

**主要方法**：
- `load_klines()`: 加载K线数据
- `load_qfq_klines()`: 加载前复权K线
- `load_multiple_terms()`: 加载多周期K线
- `load_latest_kline()`: 加载最新K线
- `save_klines()`: 保存K线数据

### 5. TagService

**职责**：
- 标签系统管理（scenario、tag_definition、tag_value）
- 标签计算和查询
- 标签值批量操作

**主要方法**：
- `load_scenario()`: 加载scenario配置
- `get_tag_definitions()`: 获取tag定义列表
- `load_tag_values()`: 加载标签值
- `save_tag_values()`: 保存标签值

### 6. CorporateFinanceService

**职责**：
- 企业财务数据加载
- 按类别查询（盈利能力、成长能力、偿债能力等）
- 多季度趋势分析

**主要方法**：
- `load()`: 兼容接口（按类别和日期范围）
- `load_financials()`: 按季度加载
- `load_financials_by_category()`: 按类别加载
- `load_financials_trend()`: 趋势分析

### 7. MacroService

**职责**：
- 宏观经济数据加载
- GDP、CPI、PPI、PMI、货币供应量
- Shibor、LPR利率数据

**主要方法**：
- `load_gdp()`: 加载GDP数据
- `load_cpi()`: 加载CPI数据
- `load_shibor()`: 加载Shibor利率
- `load_lpr()`: 加载LPR利率
- `load_macro_snapshot()`: 加载指定日期的宏观快照

### 8. CalendarService

**职责**：
- 交易日查询和缓存
- 交易日历管理

**主要方法**：
- `get_latest_trading_date()`: 获取最新交易日
- `get_latest_completed_trading_date()`: 获取最新已完成交易日
- `refresh()`: 强制刷新缓存

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
data_mgr.stock.kline
data_mgr.stock.tags
data_mgr.stock.corporate_finance

# 方法调用
data_mgr.stock.load_klines(...)           # 常用方法，直接访问
data_mgr.stock.kline.load_qfq_klines(...)  # 复杂方法，通过子服务
```

### 设计原则

1. **常用方法直接访问**：高频使用的简单方法直接在 `StockService` 上提供
   ```python
   data_mgr.stock.load_klines(...)
   data_mgr.stock.load_tags(...)
   ```

2. **复杂方法通过子服务**：复杂或低频的方法通过子服务访问
   ```python
   data_mgr.stock.kline.load_multiple_terms(...)
   data_mgr.stock.tags.load_scenario(...)
   ```

3. **明确性优于简洁性**：遵循 Python "Explicit is better than implicit" 原则
   ```python
   # ✅ 明确指定服务
   data_mgr.stock.kline.load_qfq_klines(...)
   
   # ❌ 避免隐式路由
   # data_mgr.load_qfq_klines(...)  # 不清楚是哪个服务
   ```

## 📊 数据访问示例

### 基础数据加载

```python
# K线数据
klines = data_mgr.stock.load_klines('000001.SZ', term='daily', start_date='20240101')
qfq_klines = data_mgr.stock.kline.load_qfq_klines('000001.SZ', start_date='20240101')

# 股票信息
stock_info = data_mgr.stock.load_stock_info('000001.SZ')
stock_list = data_mgr.stock.load_stock_list(filtered=True)

# 标签数据
tags = data_mgr.stock.load_tags('000001.SZ', date='20241201')
scenario_tags = data_mgr.stock.tags.load_scenario('my_scenario')

# 财务数据
finance = data_mgr.stock.load_corporate_finance(
    '000001.SZ',
    categories=['profitability', 'growth'],
    start_date='20240101',
    end_date='20241231'
)

# 宏观数据
gdp = data_mgr.macro.load_gdp('2020Q1', '2024Q4')
shibor = data_mgr.macro.load_shibor('20240101', '20241231')
macro_snapshot = data_mgr.macro.load_macro_snapshot('20241201')

# 交易日
latest_date = data_mgr.calendar.get_latest_trading_date()
```

### 配置驱动数据准备

```python
# 通过 prepare_data 方法，根据配置自动加载所需数据
settings = {
    'kline': {
        'term': 'daily',
        'start_date': '20240101',
        'end_date': '20241231',
        'adjust': 'qfq'
    },
    'stock_labels': {
        'start_date': '20240101',
        'end_date': '20241231'
    },
    'macro': {
        'GDP': True,
        'Shibor': True,
        'LPR': True,
        'start_date': '20240101',
        'end_date': '20241231'
    },
    'corporate_finance': {
        'categories': ['profitability', 'growth'],
        'start_date': '20240101',
        'end_date': '20241231'
    }
}

stock = {'id': '000001.SZ'}
data = data_mgr.prepare_data(stock, settings)
# data 包含：kline, stock_labels, macro, corporate_finance
```

## 🔧 扩展指南

### 添加新的数据服务

1. **创建服务目录和文件**：
   ```bash
   mkdir -p app/core/modules/data_manager/data_services/new_service
   touch app/core/modules/data_manager/data_services/new_service/__init__.py
   touch app/core/modules/data_manager/data_services/new_service/new_service.py
   ```

2. **实现服务类**：
   ```python
   # new_service/new_service.py
   from .. import BaseDataService
   
   class NewService(BaseDataService):
       def __init__(self, data_manager):
           super().__init__(data_manager)
           # 初始化相关 Model
           self.model = data_manager.get_model('table_name')
       
       def load_data(self, *args, **kwargs):
           # 实现数据加载逻辑
           pass
   ```

3. **在 DataService 中注册**：
   ```python
   # data_services/data_service.py
   def __init__(self, data_manager):
       # ...
       from .new_service.new_service import NewService
       self.new_service = NewService(data_manager)
   ```

4. **在 DataManager 中暴露**：
   ```python
   # data_manager.py
   @property
   def new_service(self):
       """新服务访问入口"""
       return self._data_service.new_service
   ```

### 添加 StockService 的子服务

1. **创建服务文件**：
   ```bash
   touch app/core/modules/data_manager/data_services/stock/new_sub_service.py
   ```

2. **实现服务类**：
   ```python
   # stock/new_sub_service.py
   from .. import BaseDataService
   
   class NewSubService(BaseDataService):
       def __init__(self, data_manager):
           super().__init__(data_manager)
           # ...
   ```

3. **在 StockService 中注册**：
   ```python
   # stock/stock_service.py
   def __init__(self, data_manager):
       # ...
       from .new_sub_service import NewSubService
       self.new_sub_service = NewSubService(data_manager)
   ```

4. **在 StockService 中添加便捷方法（可选）**：
   ```python
   def load_new_data(self, *args, **kwargs):
       """常用方法，统一入口"""
       return self.new_sub_service.load_data(*args, **kwargs)
   ```

## 🎨 设计原则总结

1. **单一职责**：每个服务专注于特定领域
2. **分层清晰**：Facade → Coordinator → Service
3. **属性访问**：统一的属性访问模式，直观易用
4. **明确性优先**：明确指定服务，避免隐式路由
5. **常用方法便捷**：高频方法直接访问，复杂方法通过子服务
6. **向后兼容**：保留必要的向后兼容接口

## 📝 注意事项

1. **单例模式**：`DataManager` 使用进程级单例，多进程环境下每个进程有独立实例
2. **线程安全**：`CalendarService` 使用线程锁保证缓存访问的线程安全
3. **延迟初始化**：部分 Model 使用延迟初始化，减少启动开销
4. **缓存策略**：交易日数据使用内存缓存，每天只请求一次 API

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
klines = data_mgr.stock.load_klines('000001.SZ', start_date='20240101')
qfq_klines = data_mgr.stock.kline.load_qfq_klines('000001.SZ', start_date='20240101')
```

### 实现细节

1. **私有属性**：所有 DataService 中的 Model 实例都使用 `_` 前缀（如 `_stock_kline`, `_gdp`），表示私有属性
2. **内部访问**：Model 只在 DataService 内部使用，不对外暴露
3. **警告注释**：`base_tables/__init__.py` 包含警告，说明不应被外部导入
4. **封装边界**：`DataManager.get_model()` 方法仅供内部使用，外部不应直接调用

### 为什么需要封装？

1. **解耦**：外部代码不依赖底层 Model 实现，只依赖稳定的 DataService API
2. **灵活性**：可以自由重构 Model 层，而不影响外部代码
3. **一致性**：所有数据访问都通过统一的 DataService 接口，保证行为一致
4. **可维护性**：清晰的边界使得代码更容易理解和维护

## 🔄 迁移指南

从旧 API 迁移到新 API：

```python
# 旧方式
stock_service = data_mgr.get_data_service('stock_related.stock')
klines = stock_service.load_klines(...)

# 新方式
klines = data_mgr.stock.load_klines(...)
```

```python
# 旧方式
tag_service = data_mgr.get_data_service('tag')
tags = tag_service.load_tags(...)

# 新方式
tags = data_mgr.stock.tags.load_scenario(...)
```

```python
# 旧方式
trading_date_cache = get_trading_date_cache()
date = trading_date_cache.get_latest_trading_date()

# 新方式
date = data_mgr.calendar.get_latest_trading_date()
```

## 📚 相关文档

- `data_services/README.md` - DataService 层详细说明
- `data_services/DESIGN.md` - DataService 设计文档
- `base_tables/README.md` - 基础表 Models 说明
