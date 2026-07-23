# Data Manager 模块 API 文档

**版本：** `0.3.4`

本文档对 **`DataManager`** 门面采用统一条目格式；各 **领域服务** 方法以表格索引列出（完整签名以源码为准）。

---

## DataManager（门面）

### 函数名
`__init__(self, db: Optional[DatabaseManager] = None, is_verbose: bool = False, force_new: bool = False) -> None`

- 状态：`stable`
- 描述：创建数据管理器；**构造时会调用 `initialize()`**（幂等）。默认进程内单例，`force_new=True` 时新建实例。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `db` (可选) | `Optional[DatabaseManager]` | 外部注入 DB；默认内部创建 |
| `is_verbose` (可选) | `bool` | 详细日志 |
| `force_new` (可选) | `bool` | 跳过单例 |

- 返回值：`None`

---

### 函数名
`initialize(self) -> None`

- 状态：`stable`
- 描述：初始化数据库、表发现与注册、`DataService`；**可重复调用，仅首次生效**。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`None`

---

### 函数名
`reset_instance(cls) -> None`

- 状态：`stable`
- 描述：类方法；清空单例（测试用）。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`None`

---

### 函数名
`get_instance(cls) -> Optional[DataManager]`

- 状态：`stable`
- 描述：类方法；返回当前单例或 `None`。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`Optional[DataManager]`

---

### 函数名
`register_table(self, table_folder_path: str, from_core: bool = False) -> Optional[Type[Any]]`

- 状态：`stable`
- 描述：从含 `schema.py`、`model.py` 的目录注册表 Model；`from_core=True` 时表名须 `sys_` 前缀。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `table_folder_path` | `str` | 表目录路径 |
| `from_core` (可选) | `bool` | core 表规则 |

- 返回值：Model 类或 `None`

---

### 函数名
`get_table(self, table_name: str) -> Any`

- 状态：`stable`
- 描述：按表名返回 Model 实例（**主要供 DataService 内部**）。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `table_name` | `str` | 如 `sys_stock_list` |

- 返回值：Model 实例或 `None`

---

### 函数名
`get_physical_table_name(self, logical_name: str) -> str`

- 状态：`stable`
- 描述：当前库下的物理表名（如 PostgreSQL 带 schema）。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `logical_name` | `str` | 逻辑表名 |

- 返回值：`str`

---

### 属性（领域入口）

| 属性 | 说明 |
|------|------|
| `stock` | [StockService](#2-stockservice) |
| `macro` | [MacroService](#3-macroservice) |
| `calendar` | [CalendarService](#4-calendarservice) |
| `index` | [IndexService](#5-indexservice) |
| `db_cache` | [DbCacheService](#6-dbcacheservice) |
| `backup_restore` | [BackupAndRestoreService](#7-backupandrestoreservice) |
| `service` | [DataService](#7-dataservice) |

```python
from core.modules.data_manager import DataManager

data_mgr = DataManager(is_verbose=True)  # 已触发 initialize
```

---

## 2. StockService

访问方式：`data_mgr.stock`。

### 2.1 股票基础与跨表

| 方法 | 签名 | 说明 |
|------|------|------|
| `load_info` | `(stock_id: str) -> Optional[Dict]` | 按股票代码加载基本信息（sys_stock_list 单条）。 |
| `load_with_latest_price` | `(stock_id: str) -> Optional[Dict]` | 股票信息 + 最新日线（JOIN sys_stock_list、sys_stock_klines、sys_industries）。返回含 `id`、`name`、`industry_id`、`industry`、`current_price`、`current_price_date` 等。 |

### 2.2 ListService（股票列表）

访问方式：`data_mgr.stock.list`。

| 方法 | 签名 | 说明 |
|------|------|------|
| `load_single` | `(stock_id: str) -> Optional[Dict]` | 按 ts_code 加载单条完整行。 |
| `load_meta` | `(stock_id: str) -> Optional[Dict]` | 单条简要字段（id、name、list_status、list_date、delist_date）。 |
| `load_all` | `(order_by: str = 'id') -> List[Dict]` | 加载 `sys_stock_list` 全表。 |
| `load` | `(*, period_start, period_end, as_of_date, list_status, industry, board, market, area, order_by) -> List[Dict]` | **仅关键字参数**。`period_*`：回测窗口参与者；`as_of_date`：某日仍在市；维度与 `list_status` 见实现优先级。 |
| `load_listed` / `load_delisted` / `load_suspended` | `(order_by='id') -> List[Dict]` | 按 `list_status` L / D / P。 |
| `load_by_industry` / `load_by_board` / `load_by_market` / `load_by_area` | 同前 | 糖方法，内部调用 `load(...)`。 |
| `is_tradable_on` | `(stock, trade_date) -> bool` | 资格层：模拟日是否可交易（执行层仍以 K 线为准）。 |
| `save` | `(stocks: List[Dict]) -> int` | 批量保存股票列表（upsert，unique_keys=['id']）。 |

### 2.2.1 StPeriodService（ST / *ST 时段）

访问方式：`data_mgr.stock.st`。表：`sys_stock_st_periods`（由 data source `stock_st_periods` 从 Tushare `namechange` 同步）。

| 方法 | 签名 | 说明 |
|------|------|------|
| `load_by_stock` | `(stock_id) -> List[Dict]` | 该股全部警示时段（行数很少）。 |
| `load_overlapping` | `(stock_ids, *, period_start, period_end) -> Dict[str, List[Dict]]` | 与回测窗有交集的时段，按股分组；**每个 run 调一次**。 |
| `is_on` | `(stock_id, trade_date, *, levels=None, periods=None) -> bool` | 某日是否处于指定 level；`periods` 传入则不再查库。 |
| `is_star_st_on` | `(stock_id, trade_date, *, periods=None) -> bool` | 是否为 `*ST`（`STAR_ST`）。 |
| `is_st_on` | `(stock_id, trade_date, *, include_star_st=True, periods=None) -> bool` | 是否为 ST（默认含 *ST）。 |
| `level_at` | `(trade_date, periods, *, levels=None) -> Optional[str]` | 静态：当日生效 level（*ST 优先）。 |

生效区间：`start_date <= trade_date <= end_date`（`end_date` 空=仍有效）。与 `ann_date` 无关。

### 2.3 KlineService（K 线）

访问方式：`data_mgr.stock.kline`。

| 方法 | 签名 | 说明 |
|------|------|------|
| `load` | `(stock_id, term='daily', start_date=None, end_date=None, adjust='qfq', filter_negative=True, as_dataframe=False) -> List[Dict] \| DataFrame` | 加载 K 线；默认前复权；可返回 DataFrame。 |
| `load_raw` | `(stock_id, term=None, start_date=None, end_date=None) -> List[Dict]` | 加载原始 K 线，不复权。 |
| `load_qfq` | `(stock_id, term='daily', start_date=None, end_date=None) -> List[Dict]` | 前复权 K 线。 |
| `load_latest` | `(stock_id: str) -> Optional[Dict]` | 单只股票最新一条 K 线。 |
| `load_latest_date` | `(term: str = 'daily') -> str` | **全市场**指定周期最新 K 线日期（YYYYMMDD）。用于缓存/指纹以“库内数据更新时间”为准。 |
| `load_earliest_date` | `(term: str = 'daily', stock_ids: Sequence[str] \| None = None) -> str` | 指定周期最早 K 线日期。未传 ``stock_ids`` 为全市场 MIN；传入则为样本池内 MIN。用于回测 ``start_date`` 未配置时的下界。 |
| `load_by_date` | `(date: str) -> List[Dict]` | 指定交易日全市场 K 线（日度）。 |
| `load_multiple` | `(stock_id: str, settings: Dict) -> Dict[str, List[Dict]]` | 按配置加载多周期 K 线。 |
| `load_batch` | `(stock_ids, term, start_date, end_date, ...) -> Dict[str, List[Dict]]` | 多股票批量加载。 |
| `load_with_latest` | `(stock_id, term='daily') -> Optional[Dict]` | 股票信息 + 该周期最新 K 线（JOIN）。 |
| `load_all_by_date` | `(date: str) -> List[Dict]` | 指定日期全市场 K 线（含股票信息 JOIN）。 |
| `save` | `(klines: List[Dict]) -> int` | 批量保存 K 线。 |
| `save_adj_factor_events` | `(events: List[Dict]) -> int` | 保存复权因子事件。 |
| `delete_adj_factor_events` | `(stock_id: str) -> int` | 删除指定股票复权因子事件。 |

**前复权（`load_qfq` / `load_qfq_split`）消费公式（方案 B）**：

```text
qfq(t) = raw(t) × F(段) / F(最新) + C
C = qfq_anchor_最新 - raw_anchor_最新 × F_最新事件 / F(最新)
```

- 顶层 `open/close/high/low/pre_close` 同式；列名与 raw 一致，语义为前复权价。
- 同层附带 `raw: {open, high, low, close, pre_close?}` 为折算前不复权价（无事件时与顶层相同）。
- 详见 `userspace/extensions/data_source/handlers/adj_factor_event/README.md`；对比基准见 `experiments/qfq_baseline/方案B_tencent_validation.json`。

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
| 配置项 ``default_start_date`` / ``default_end_date`` | `userspace/config/data.json` | renew 拉数下界/上界；未配置 ``default_end_date`` 时不截断 end。 |
| ``DataSourceManager.renew(table_name, force=)`` | 核心入口 | 单表（表名或 source key）或全部已启用数据源；``force=True`` 强制 refresh。 |
| `get_real_world_latest_completed_trading_date` | `() -> str` | 真实世界最新已完成交易日（API / cache）；不读 ``sys_trade_calendar``。 |
| `get_db_latest_completed_trading_date` | `(*, as_of_date=None) -> str` | 库内日历最新开市日（``is_open=1``）；数据同步进度锚点。 |
| `get_db_latest_trading_date` | `(*, as_of_date=None, is_open_only=False) -> str` | 库内日历最新 ``cal_date``；默认含休市，`is_open_only=True` 等同上。 |
| `refresh` | `() -> str` | 强制刷新并返回真实世界最新交易日。 |
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

## 7. BackupAndRestoreService

访问方式：`data_mgr.backup_restore`（推荐）或 `data_mgr.service.backup_restore`。

用于跨表级别的备份与恢复，底层复用各表 model 的 `export_data` / `import_data`。

| 方法 | 签名 | 说明 |
|------|------|------|
| `backup` | `(*, tables=None, root_dir=None, backup_date=None, archive_format='tar.gz', condition='1=1', params=(), keep=3) -> List[BackupResult]` | 备份单表/多表；`tables` 为空时备份全部注册表；完成后按 `keep` 自动清理旧日期目录。 |
| `restore` | `(*, backup_date: str, tables=None, root_dir=None, mode='overwrite', target_table_map=None) -> List[str]` | 从指定日期目录恢复单表/多表；返回成功恢复的表名列表。 |
| `prune_old_backups` | `(*, root_dir=None, keep=3) -> List[str]` | 清理旧备份日期目录，仅保留最近 `keep` 个。 |

---

## 8. DataService（跨服务协调）

访问方式：`data_mgr.service`。

DataService 仅作为子服务入口，无跨服务聚合方法。数据按需通过 `data_mgr.stock`、`data_mgr.macro`、`data_mgr.calendar` 等组装；业务模块（Tag、Strategy）使用各自的数据管理器（如 TagWorkerDataManager、StrategyWorkerDataManager）。

---

## 9. 表名约定

- **Core 表**：由 `core/tables` 与 `userspace/tables` 发现，core 表名以 `sys_` 开头（如 `sys_stock_list`、`sys_stock_klines`、`sys_industries`、`sys_boards`、`sys_markets`、`sys_areas`、`sys_corporate_finance`、`sys_gdp`、`sys_cpi` 等）。
- **获取 Model**：`data_mgr.get_table("sys_xxx")`，返回对应 Model 实例（供 DataService 内部使用，一般业务代码用各 Service 的 load/save 即可）。

---

## 10. 使用示例

```python
from core.modules.data_manager import DataManager

data_mgr = DataManager(is_verbose=True)

# 股票列表（筛选由 Tag 等负责）
stocks = data_mgr.stock.list.load_all()
window = data_mgr.stock.list.load(period_start="20150101", period_end="20241231")
one = data_mgr.stock.list.load_single("000001.SZ")
gem_stocks = data_mgr.stock.list.load_by_board("创业板")

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
last_trade = data_mgr.calendar.get_real_world_latest_completed_trading_date()

# 跨表备份/恢复
backup_results = data_mgr.backup_restore.backup(
    tables=["sys_stock_list", "sys_stock_klines"],
    keep=3,
)
restored_tables = data_mgr.backup_restore.restore(
    backup_date="20260422",
    tables=["sys_stock_list"],
)

# 按需组装多源数据
klines = data_mgr.stock.kline.load_multiple('000001.SZ', {'terms': ['daily'], 'start_date': '20240101', 'end_date': '20241231'})
macro_gdp = data_mgr.macro.load_gdp('2024Q1', '2024Q4')
finance = data_mgr.stock.corporate_finance.load_by_categories('000001.SZ', ['profitability'], '20240101', '20241231')
```

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DESIGN.md](DESIGN.md)
- [DECISIONS.md](DECISIONS.md)
