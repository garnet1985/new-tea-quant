# Data Manager API 文档

**版本：** `0.4.0`  
**最低支持核心版本：** `>=0.4.1`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `DataManager`；`BaseTableNames` 从 [`contracts.py`](./contracts.py) 导入。  
领域服务经属性访问（如 `DataManager.calendar`），**不**从包根导出。实现位于本模块内部，禁止 deep-import。

---

## DataManager

**描述：** 统一数据访问门面（进程内默认单例）

### __init__ / initialize

- **类型：** 构造 / 实例方法
- **状态：** `beta`
- **描述：** 构造时幂等 `initialize()`（锁保护）；默认单例，`force_new=True` 可破例
- **参数（构造）：**
  - `db`：可选已有 `DatabaseManager`
  - `is_verbose`：日志详细度
  - `force_new`：强制新实例（测试/隔离）

### get_instance / reset_instance

- **类型：** `classmethod`
- **状态：** `beta`
- **描述：** 读当前单例 / 清空单例（测试用）

### get_table / register_table

- **状态：** `beta`
- **描述：** 按逻辑表名取已注册 Model 实例；从「表目录」（含 `schema.py`/`model.py`）注册

### get_physical_table_name

- **状态：** `beta`
- **描述：** 逻辑名 → 物理名（如 PostgreSQL `schema.table`）

### normalize_delist_date

`DataManager.normalize_delist_date(raw) -> str | None`（staticmethod）

- **状态：** `beta`
- **描述：** 将源数据占位退市日（`0` / `0.0`）视为未退市；跨模块入口

### register_calendar_real_world_fetcher

`DataManager.register_calendar_real_world_fetcher(fetcher) -> None`（staticmethod）

- **状态：** `beta`
- **描述：** 注入日历 real-world 网络探测（`Callable[[], tuple[date, provider] | None]`）。通常由 `DataSourceManager` 在导入/构造时注册；DM 不依赖 DS

### attach_data_service

`DataManager.attach_data_service() -> DataService`

- **状态：** `beta`
- **描述：** 绑定 / 重建领域 `DataService`（worker 子进程、DuckDB pool resume）。跨模块勿 deep-import `core.data_services.DataService`

### ensure_duckdb_pool_holder_resolver

`DataManager.ensure_duckdb_pool_holder_resolver() -> None`（classmethod）

- **状态：** `beta`
- **描述：** 向 `infra.db` 注册 holder 解析（单例 / 可选新建），避免 infra import `DataManager`。包导入与构造时自动调用

### ensure_restored_after_worker_pool

`DataManager.ensure_restored_after_worker_pool(data_mgr=None) -> DataManager | Any`（classmethod）

- **状态：** `beta`
- **描述：** ProcessPool / 中断后恢复主进程 DM + DB 的应用层入口

### bind_as_default_instance

`DataManager.bind_as_default_instance() -> None`

- **状态：** `beta`
- **描述：** DuckDB pool resume 后把本实例挂回进程单例（供 infra duck-type 调用）

### 领域服务（属性）

| 属性 | 说明 |
|------|------|
| `stock` | K 线、列表、指标、tag、财务等 |
| `macro` | 宏观序列 |
| `calendar` | 交易日历（CalendarService） |
| `index` | 指数 |
| `db_cache` | 仿真/工作台等缓存表 |
| `backup_restore` | 跨表备份与恢复 |
| `service` | `DataService` 容器（与上列属性同源） |

**举例：**

```python
from core.modules.data_manager import DataManager

dm = DataManager(is_verbose=True)
klines = dm.stock.kline.load("000001.SZ", term="daily", adjust="qfq")
open_dates = dm.calendar.load_open_dates("20240101", "20241231")
```

---

## contracts

| 符号 | 说明 |
|------|------|
| `BaseTableNames` | 与 `core/tables` schema.name 对齐的 `sys_*` 枚举（运行时以 discovery 为准） |
