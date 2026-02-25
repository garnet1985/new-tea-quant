# DataManager 模块 API 文档

按「描述、函数签名、参数、输出、示例」列出 DataManager 模块中**应用代码会直接使用的入口**；内部 helper / 私有 model 不列入。架构与设计见 `architecture.md` / `decisions.md`，快速上手见 `overview.md`。

---

## DataManager

### DataManager（构造函数）

**描述**：数据管理服务的总入口。负责创建并持有 `DatabaseManager`，初始化所有基础表（Base Tables）、自动发现用户自定义表，并挂载各类数据服务（`stock`、`macro`、`calendar` 等）。

**函数签名**：`DataManager(db: Optional[DatabaseManager] = None, is_verbose: bool = False, force_new: bool = False)`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `db` | `Optional[DatabaseManager]` | 可选的 `DatabaseManager` 实例；不传时自动创建并初始化默认实例 |
| `is_verbose` | `bool` | 是否输出更详细日志（初始化过程等），默认 `False` |
| `force_new` | `bool` | 是否强制创建新实例（通常保持默认 `False`，让单例模式生效） |

**输出**：无（构造实例）

**Example**：

```python
from core.modules.data_manager import DataManager

data_mgr = DataManager(is_verbose=True)
```

---

### initialize

**描述**：显式初始化 DataManager。通常在 `__init__` 中已自动调用，只有在特殊场景（如手动注入自定义 `DatabaseManager` 后）才需要显式调用。

**函数签名**：`DataManager.initialize() -> None`

**参数**：无

**输出**：`None`（完成数据库连接池、基础表创建、表发现和 DataService 初始化）

**Example**：

```python
from core.modules.data_manager import DataManager
from core.utils.db.database_manager import DatabaseManager

db = DatabaseManager(is_verbose=True)
data_mgr = DataManager(db=db, is_verbose=True)
data_mgr.initialize()  # 幂等，多次调用只执行一次
```

---

### register_table

**描述**：将一个表文件夹（包含 `schema.py` + `model.py`）注册为 DataManager 可管理的表。用于挂载用户自定义表或特殊表。

**函数签名**：`DataManager.register_table(table_folder_path: str, from_core: bool = False) -> Optional[Type[Any]]`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `table_folder_path` | `str` | 表文件夹路径，如 `"userspace/tables/my_custom_table"` |
| `from_core` | `bool` | 是否来自 `core/tables`；为 `True` 时表名必须以 `sys_` 开头 |

**输出**：`Optional[Type[Any]]` —— 成功时返回注册的 Model 类，否则为 `None`。

**Example**：

```python
from core.modules.data_manager import DataManager
from core.infra.project_context import PathManager

data_mgr = DataManager()

custom_table_dir = PathManager.get_root() / "userspace" / "tables" / "my_custom_table"
model_cls = data_mgr.register_table(str(custom_table_dir), from_core=False)
```

---

## 核心数据服务入口

> 下列属性通过 `DataManager` 暴露为**属性型服务入口**，常用调用方式为：  
> `data_mgr.stock.list.load(...)`、`data_mgr.macro.load_gdp(...)`、`data_mgr.calendar.get_latest_completed_trading_date()` 等。

---

### StockService（`data_mgr.stock`）

**模块路径**：`core.modules.data_manager.data_services.stock.stock_service.StockService`

**描述**：股票相关数据的统一入口，内部再细分为 `list` / `kline` / `tags` / `corporate_finance` 等子服务。

**典型属性与方法**：

- `data_mgr.stock.list.load(filtered: bool = True) -> List[Dict[str, Any]]`  
  读取股票列表，可按是否过滤退市、ST 等条件。
- `data_mgr.stock.kline.load(stock_id: str, term: str = "daily", start_date: str | None = None, end_date: str | None = None) -> List[Dict[str, Any]]`  
  读取指定股票的 K 线数据。
- `data_mgr.stock.corporate_finance.load(stock_id: str, quarter: str) -> Dict[str, Any]`  
  读取财务数据。
- `data_mgr.stock.tags.load_values_for_entity(...)`  
  详见 Tag 模块 API 文档中的 `TagDataService`。

**Example**：

```python
from core.modules.data_manager import DataManager

data_mgr = DataManager()

# 股票列表
stocks = data_mgr.stock.list.load(filtered=True)

# 日线 K 线
klines = data_mgr.stock.kline.load("000001.SZ", term="daily", start_date="20240101")
```

---

### MacroService（`data_mgr.macro`）

**模块路径**：`core.modules.data_manager.data_services.macro.macro_service.MacroService`

**描述**：宏观经济数据服务，包括 GDP、CPI、Shibor、LPR 等。

**常用方法示例**：

- `load_gdp(start_quarter: str, end_quarter: str) -> List[Dict[str, Any]]`  
- `load_cpi(start_month: str, end_month: str) -> List[Dict[str, Any]]`  
- `load_shibor(start_date: str, end_date: str) -> List[Dict[str, Any]]`

**Example**：

```python
gdp = data_mgr.macro.load_gdp("2020Q1", "2024Q4")
cpi = data_mgr.macro.load_cpi("202001", "202412")
```

---

### CalendarService（`data_mgr.calendar`）

**模块路径**：`core.modules.data_manager.data_services.calendar.calendar_service.CalendarService`

**描述**：交易日历相关服务，提供交易日查询与缓存。

**常用方法**（部分）：

- `get_latest_completed_trading_date() -> str`  
  返回最近一个已完成的交易日（`YYYYMMDD`）。
- `is_trading_date(date: str) -> bool`  
  判断某日是否为交易日。

**Example**：

```python
latest_date = data_mgr.calendar.get_latest_completed_trading_date()
if data_mgr.calendar.is_trading_date("20250210"):
    ...
```

---

### UI Transit / InvestmentDataService（`data_mgr.ui.investment`）

**模块路径**：`core.modules.data_manager.data_services.ui_transit.investment.investment_data_service.InvestmentDataService`

**描述**：为 UI/报表层提供的投资数据中转服务，聚合 `investment_trades` / `investment_operations` 两张表的查询。

> 具体方法签名参考对应模块；此处仅说明 DataManager 入口。

**Example**：

```python
ui = data_mgr.ui  # UI Transit 根服务
investments = ui.investment_service.load_trades(strategy_name="my_strategy")
```

---

## 相关文档

- [DataManager 概览](./overview.md)  
- [DataManager 架构](./architecture.md)  
- [DataManager 设计决策](./decisions.md)  

