# Data Manager API 文档

数据管理模块对外 API 说明。入口为 `DataManager`，通过属性访问各领域服务（stock、macro、calendar、index、db_cache）及跨服务协调器 `service`。

---

## 1. 入口与初始化

### DataManager

```python
from core.modules.data_manager import DataManager

# 推荐：单例，自动初始化
data_mgr = DataManager(is_verbose=True)
data_mgr.initialize()

# 强制新建实例（测试等）
data_mgr = DataManager(force_new=True)
data_mgr.initialize()
```

| 方法 / 属性 | 说明 |
|-------------|------|
| `initialize()` | 初始化数据库、表发现与注册、DataService。必须先调用再使用 `stock` / `macro` 等。 |
| `get_table(table_name: str)` | 根据表名获取 Model 实例（如 `sys_stock_list`）。主要供 DataService 内部使用。 |
| `stock` | 股票数据服务，见 [2. StockService](#2-stockservice)。 |
| `macro` | 宏观经济数据服务，见 [3. MacroService](#3-macroservice)。 |
| `calendar` | 交易日历服务，见 [4. CalendarService](#4-calendarservice)。 |
| `index` | 指数数据服务，见 [5. IndexService](#5-indexservice)。 |
| `db_cache` | 数据库缓存服务，见 [6. DbCacheService](#6-dbcacheservice)。 |
| `service` | 跨服务协调器（DataService），见 [7. DataService](#7-dataservice)。 |

---

## 2. StockService

访问方式：`data_mgr.stock`。

### 2.1 股票基础与跨表

| 方法 | 签名 | 说明 |
|------|------|------|
| `load_info` | `(stock_id: str) -> Optional[Dict]` | 按股票代码加载基本信息（sys_stock_list 单条）。 |
| `load_with_latest_price` | `(stock_id: str) -> Optional[Dict]` | 股票信息 + 最新日线（JOIN sys_stock_list、sys_stock_klines、sys_stock_industries）。返回含 `id`、`name`、`industry_id`、`industry`、`current_price`、`current_price_date` 等。 |

### 2.2 ListService（股票列表）

访问方式：`data_mgr.stock.list`。

| 方法 | 签名 | 说明 |
|------|------|------|
| `load` | `(filtered: bool = True, order_by: str = 'id') -> List[Dict]` | 加载股票列表；`filtered=True` 时排除科创板、ST、退市等。 |
| `load_all` | `() -> List[Dict]` | 加载全部活跃股票，无过滤。 |
| `load_filtered` | `(exclude_patterns=None, order_by: str = 'id') -> List[Dict]` | 按自定义排除规则过滤；默认排除 id 以 688 开头、name 以 *ST/ST/退 开头。 |
| `load_by_industry` | `(industry: Union[str, int], filtered: bool = True, order_by: str = 'id') -> List[Dict]` | 按行业加载；`industry` 可为行业名称或 sys_stock_industries.id；名称未找到时返回 []。 |
| `load_by_board` | `(board: Union[str, int], filtered: bool = True, order_by: str = 'id') -> List[Dict]` | 按板块加载；`board` 可为板块名称（如「创业板」「科创板」）或 sys_stock_boards.id；未找到时返回 []。 |
| `save` | `(stocks: List[Dict]) -> int` | 批量保存股票列表（replace，unique_keys=['id']）。 |

### 2.3 KlineService（K 线）

访问方式：`data_mgr.stock.kline`。

| 方法 | 签名 | 说明 |
|------|------|------|
| `load` | `(stock_id, term='daily', start_date=None, end_date=None, adjust='qfq', filter_negative=True, as_dataframe=False) -> List[Dict] \| DataFrame` | 加载 K 线；默认前复权；可返回 DataFrame。 |
| `load_raw` | `(stock_id, term=None, start_date=None, end_date=None) -> List[Dict]` | 加载原始 K 线，不复权。 |
| `load_qfq` | `(stock_id, term='daily', start_date=None, end_date=None) -> List[Dict]` | 前复权 K 线。 |
| `load_latest` | `(stock_id: str) -> Optional[Dict]` | 单只股票最新一条 K 线。 |
| `load_by_date` | `(date: str) -> List[Dict]` | 指定交易日全市场 K 线（日度）。 |
| `load_multiple` | `(stock_id: str, settings: Dict) -> Dict[str, List[Dict]]` | 按配置加载多周期 K 线。 |
| `load_batch` | `(stock_ids, term, start_date, end_date, ...) -> Dict[str, List[Dict]]` | 多股票批量加载。 |
| `load_with_latest` | `(stock_id, term='daily') -> Optional[Dict]` | 股票信息 + 该周期最新 K 线（JOIN）。 |
| `load_all_by_date` | `(date: str) -> List[Dict]` | 指定日期全市场 K 线（含股票信息 JOIN）。 |
| `save` | `(klines: List[Dict]) -> int` | 批量保存 K 线。 |
| `save_adj_factor_events` | `(events: List[Dict]) -> int` | 保存复权因子事件。 |
| `delete_adj_factor_events` | `(stock_id: str) -> int` | 删除指定股票复权因子事件。 |

### 2.4 CorporateFinanceService（企业财务）

访问方式：`data_mgr.stock.corporate_finance`。

| 方法 | 签名 | 说明 |
|------|------|------|
| `load` | `(ts_code: str, quarter: str, indicators=None) -> Optional[Dict]` | 指定股票、季度（YYYYQ1–Q4）的财务数据；`indicators` 为字段列表，默认全部。 |
| `load_by_category` | `(ts_code, quarter, category) -> Optional[Dict]` | 按类别加载；category：profitability/growth/solvency/cashflow/operation/assets。 |
| `load_by_categories` | `(stock_id, categories=None, start_date=None, end_date=None) -> Dict` | 按类别与日期范围加载；日期转为季度；无日期时返回最新。 |
| `load_trend` | `(ts_code, start_quarter, end_quarter, indicators=None) -> List[Dict]` | 多季度趋势，按季度排序。 |
| `load_latest` | `(ts_code, indicators=None) -> Optional[Dict]` | 最新一期财务数据。 |
| `save` | `(data: Dict) -> bool` | 保存单条财务记录。 |
| `save_batch` | `(data_list: List[Dict]) -> int` | 批量保存。 |
| `get_stocks_latest_update_quarter` | `() -> Dict[str, str]` | 各股票最新更新季度（stock_id -> quarter）。 |

### 2.5 TagDataService（标签）

访问方式：`data_mgr.stock.tags`。

| 方法 | 签名 | 说明 |
|------|------|------|
| `load_scenario` | `(scenario_name: str) -> Optional[Dict]` | 按名称加载场景。 |
| `save_scenario` | `(...)` | 保存场景。 |
| `update_scenario` | `(...)` | 更新场景。 |
| `list_scenarios` | `(...) -> List` | 场景列表。 |
| `delete_scenario` | `(scenario_id: int, cascade: bool = False)` | 删除场景。 |
| `load` | `(scenario_id, ...)` | 按场景加载标签值。 |
| `save` | `(...)` | 保存标签值。 |
| `get_tag_definitions` | `(scenario_id) -> List` | 场景下标签定义。 |
| `update_tag_definition` | `(...)` | 更新标签定义。 |
| `batch_update_tag_definitions` | `(...)` | 批量更新标签定义。 |
| `delete_tag_definition` | `(tag_definition_id: int)` | 删除标签定义。 |
| `delete_tag_definitions_by_scenario` | `(scenario_id: int)` | 按场景删除标签定义。 |
| `save_value` | `(tag_value_data: Dict) -> int` | 保存单条标签值。 |
| `save_batch` | `(tag_values: List[Dict]) -> int` | 批量保存标签值。 |
| `delete_tag_values_by_scenario` | `(scenario_id: int)` | 按场景删除标签值。 |
| `get_max_as_of_date` | `(tag_definition_ids: List[int]) -> Optional[str]` | 指定定义下的最大 as_of_date。 |
| `get_tag_value_last_update_info` | `(scenario_name: str) -> Dict` | 场景下标签值最后更新信息。 |
| `get_next_trading_date` | `(date: str) -> str` | 下一交易日。 |

---

## 3. MacroService

访问方式：`data_mgr.macro`。

| 方法 | 签名 | 说明 |
|------|------|------|
| `load_gdp` | `(start_quarter=None, end_quarter=None) -> List[Dict]` | GDP，季度 YYYYQ1–Q4。 |
| `load_latest_gdp` | `() -> Optional[Dict]` | 最新季度 GDP。 |
| `load_gdp_by_quarter` | `(quarter: str) -> Optional[Dict]` | 指定季度 GDP。 |
| `load_cpi` | `(start_date=None, end_date=None) -> List[Dict]` | CPI（月度）。 |
| `load_ppi` | `(start_date=None, end_date=None) -> List[Dict]` | PPI。 |
| `load_pmi` | `(start_date=None, end_date=None) -> List[Dict]` | PMI。 |
| `load_money_supply` | `(start_date=None, end_date=None) -> List[Dict]` | 货币供应。 |
| `load_shibor` | `(start_date=None, end_date=None) -> List[Dict]` | Shibor。 |
| `load_shibor_by_date` | `(date: str, fallback: bool = True) -> Optional[Dict]` | 指定日 Shibor。 |
| `load_latest_shibor` | `() -> Optional[Dict]` | 最新 Shibor。 |
| `load_lpr` | `(start_date=None, end_date=None) -> List[Dict]` | LPR。 |
| `load_lpr_by_date` | `(date: str, fallback: bool = True) -> Optional[Dict]` | 指定日 LPR。 |
| `load_latest_lpr` | `() -> Optional[Dict]` | 最新 LPR。 |
| `load_risk_free_rate` | `(date=None, ...) -> Optional[float]` | 无风险利率（可配置来源）。 |
| `load_macro_snapshot` | `(date: str) -> Dict` | 指定日宏观快照（多指标聚合）。 |
| `save_gdp_data` | `(gdp_data: List[Dict]) -> int` | 批量保存 GDP。 |
| `save_shibor_data` | `(shibor_data: List[Dict]) -> int` | 批量保存 Shibor。 |
| `save_lpr_data` | `(lpr_data: List[Dict]) -> int` | 批量保存 LPR。 |
| `save_price_indexes_data` | `(price_indexes_data: List[Dict]) -> int` | 批量保存价格指数。 |

---

## 4. CalendarService

访问方式：`data_mgr.calendar`。

| 方法 | 签名 | 说明 |
|------|------|------|
| `get_latest_completed_trading_date` | `() -> str` | 最新已完成的交易日（YYYYMMDD），非当日；含内存与 DB 缓存。 |
| `refresh` | `() -> str` | 强制刷新并返回最新交易日。 |
| `get_cached_date` | `() -> Optional[str]` | 当前缓存的交易日，不请求外部。 |

---

## 5. IndexService

访问方式：`data_mgr.index`。

| 方法 | 签名 | 说明 |
|------|------|------|
| `load_indicator` | `(index_id, term=None, start_date=None, end_date=None) -> List[Dict]` | 指数指标序列（K 线等）。 |
| `load_latest_indicator` | `(index_id, term=None) -> Optional[Dict]` | 最新一条指标。 |
| `load_latest_indicators_by_term` | `(index_id, ...) -> Dict` | 按周期汇总最新指标。 |
| `save_indicator` | `(indicator_data: List[Dict]) -> int` | 保存指数指标。 |
| `load_weight` | `(index_id, as_of_date=None, ...) -> List[Dict]` | 指数成分股权重。 |
| `load_latest_weight` | `(index_id: str) -> Optional[Dict]` | 最新权重。 |
| `load_latest_weights` | `(...) -> Dict` | 多指数最新权重。 |
| `save_weight` | `(weight_data: List[Dict]) -> int` | 保存权重。 |

---

## 6. DbCacheService

访问方式：`data_mgr.db_cache`。

| 方法 | 签名 | 说明 |
|------|------|------|
| `get` | `(key: str) -> Optional[Dict]` | 按 key 取缓存（含 'value' 等字段）。 |
| `set` | `(key: str, value: str) -> int` | 写缓存。 |
| `delete` | `(key: str) -> int` | 删缓存。 |

---

## 7. DataService（跨服务协调）

访问方式：`data_mgr.service`。

DataService 仅作为子服务入口，无跨服务聚合方法。数据按需通过 `data_mgr.stock`、`data_mgr.macro`、`data_mgr.calendar` 等组装；业务模块（Tag、Strategy）使用各自的数据管理器（如 TagWorkerDataManager、StrategyWorkerDataManager）。

---

## 8. 表名约定

- **Core 表**：由 `core/tables` 与 `userspace/tables` 发现，core 表名以 `sys_` 开头（如 `sys_stock_list`、`sys_stock_klines`、`sys_stock_industries`、`sys_stock_boards`、`sys_stock_markets`、`sys_corporate_finance`、`sys_gdp`、`sys_cpi` 等）。
- **获取 Model**：`data_mgr.get_table("sys_xxx")`，返回对应 Model 实例（供 DataService 内部使用，一般业务代码用各 Service 的 load/save 即可）。

---

## 9. 使用示例

```python
from core.modules.data_manager import DataManager

data_mgr = DataManager(is_verbose=True)
data_mgr.initialize()

# 股票列表与筛选
stocks = data_mgr.stock.list.load(filtered=True)
gem_stocks = data_mgr.stock.list.load_by_board('创业板', filtered=True)
bank_stocks = data_mgr.stock.list.load_by_industry('银行', filtered=True)

# 单股信息与最新价
info = data_mgr.stock.load_info('000001.SZ')
with_price = data_mgr.stock.load_with_latest_price('000001.SZ')

# K 线
klines = data_mgr.stock.kline.load('000001.SZ', term='daily', start_date='20240101', end_date='20241231', adjust='qfq')
latest = data_mgr.stock.kline.load_latest('000001.SZ')

# 企业财务
finance = data_mgr.stock.corporate_finance.load('000001.SZ', '2024Q3')
trend = data_mgr.stock.corporate_finance.load_trend('000001.SZ', '2023Q1', '2024Q3')

# 宏观
gdp = data_mgr.macro.load_gdp('2020Q1', '2024Q4')
lpr = data_mgr.macro.load_lpr('20240101', '20241231')
snapshot = data_mgr.macro.load_macro_snapshot('20240601')

# 日历
last_trade = data_mgr.calendar.get_latest_completed_trading_date()

# 按需组装多源数据
klines = data_mgr.stock.kline.load_multiple('000001.SZ', {'terms': ['daily'], 'start_date': '20240101', 'end_date': '20241231'})
macro_gdp = data_mgr.macro.load_gdp('2024Q1', '2024Q4')
finance = data_mgr.stock.corporate_finance.load_by_categories('000001.SZ', ['profitability'], '20240101', '20241231')
```
