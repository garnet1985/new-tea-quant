# Database 模块 API 文档

**版本：** `0.3.0`（Engine 挂载架构，2026-06）

业务代码优先使用 `from core.infra.db import ...`；infra 内部按职责使用 `engines._shared.*`、`schema_manager`、`migrate_manager` 等子模块。总览见 [ARCHITECTURE.md](./ARCHITECTURE.md)、[DESIGN.md](./DESIGN.md)。

---

## 包导出（`core.infra.db`）

| 符号 | 说明 |
|------|------|
| `DatabaseManager` | 统一入口，挂载一个 backend Engine |
| `DbBaseModel` | 单表 CRUD / 导入导出 |
| `StorageRegistry`, `STORAGE_DOMAINS` | 表 → `storage_domain`（DuckDB 路由） |
| `Field` | 列类型定义（`engines._shared.fields`） |
| `DbEngineAbc`, `DbTableAbc` | Engine / 表操作抽象 |
| `EngineConfigMeta`, `build_engine_meta`, `create_engine` | 配置元信息与工厂 |
| `BatchOperation`, `BatchWriteQueue` | 批量 SQL 与 mysql/pgsql 写队列 |

未从包根导出、按需直接 import：`SchemaManager`、`MigrationManager`、`parse_database_config`、`dialect`、`row_sql` 等（见下文）。

---

## DatabaseManager

按 `database_type` 挂载 **一个** Engine（`mysql` | `postgresql` | `duckdb`）。初始化后通过 `db.engine` 或本类转发方法访问连接与表操作。

### 构造与生命周期

| 方法 / 属性 | 说明 | 版本 |
|-------------|------|------|
| `DatabaseManager(config=None, is_verbose=False)` | `config` 缺省则 `ConfigManager.load_database_config()`，经 `parse_database_config` 校验 | `0.3.0` |
| `initialize()` | `create_engine` → `rebuild_storage_registry` →（duckdb）`rebuild_table_file_map` → `engine.initialize()`；`schema_manager` 与 engine 共享 | `0.3.0` |
| `close()` | 关闭 engine、写队列/写管道 | `0.3.0` |
| `set_default` / `get_default` / `reset_default` | 进程内默认实例 | `0.2.0` |

### 属性

| 属性 | 说明 |
|------|------|
| `config` | 解析后的数据库配置 dict |
| `engine` | `DbEngineAbc` 实例（`initialize` 后非空） |
| `engine_meta` | `EngineConfigMeta` |
| `schema_manager` | `SchemaManager`（加载 `core/tables`、建表编排） |
| `storage_registry` | `StorageRegistry` |
| `database_type` | `postgresql` \| `mysql` \| `duckdb` |
| `is_duckdb` | 是否 DuckDB backend |
| `adapter` | 当前 engine 的主 connector（duckdb 为主域 `data`） |

### 查询与连接

| 方法 | 说明 | 版本 |
|------|------|------|
| `execute_sync_query(query, params=None, domain=None)` | 同步查询，返回 `List[Dict]`；duckdb 可指定 `domain` | `0.3.0` |
| `execute_sync_query_for_table(table_name, query, params=None)` | 按表路由域（duckdb） | `0.3.0` |
| `get_connection()` | 连接上下文管理器 | `0.2.0` |
| `transaction()` | 事务上下文 | `0.2.0` |
| `get_sync_cursor(domain=None)` | `DatabaseCursor` 上下文 | `0.3.0` |
| `get_sync_cursor_for_table(table_name)` | 按表选域（duckdb） | `0.3.0` |
| `connection_factory_for_table(table_name)` | 供 `SchemaManager.create_table` 等使用 | `0.3.0` |

### Schema 与表

| 方法 | 说明 | 版本 |
|------|------|------|
| `register_table(table_name, schema)` | 注册策略等自定义表；更新 `storage_registry` | `0.3.0` |
| `create_registered_tables()` | 创建已注册表 | `0.3.0` |
| `create_all_base_tables()` | 加载 `core/tables` 并建表 | `0.3.0` |
| `create_table(schema)` / `drop_table(table_name)` | DDL | `0.3.0` |
| `load_schema_from_python(schema_file)` | 加载单个 `schema.py` | `0.3.0` |
| `is_table_exists(table_name)` | 表是否存在 | `0.2.0` |
| `get_table_schema` / `get_table_fields` | 读 schema 元数据 | `0.2.0` |
| `rebuild_storage_registry()` | 从 `core/tables` 重建域映射 | `0.3.0` |

### DuckDB 专有

| 方法 | 说明 | 版本 |
|------|------|------|
| `get_table_domain(table_name)` | 解析 `storage_domain` | `0.3.0` |
| `duckdb_file_map_for_table(table_name)` | 域 + 配置路径 + 绝对路径 | `0.3.0` |
| `adapter_for_table(table_name)` | 该表所在域的 connector | `0.3.0` |
| `checkpoint_duckdb(domains=None)` | WAL CHECKPOINT | `0.3.0` |

### 批量写入

| 方法 | 说明 | 版本 |
|------|------|------|
| `queue_write(table_name, data_list, unique_keys, callback=None)` | mysql/pgsql 队列；duckdb 走 WritePipeline | `0.2.0` |
| `flush_writes(table_name=None)` | 刷盘 | `0.2.0` |
| `wait_for_writes(timeout=30.0)` | 等待队列/管道 | `0.2.0` |
| `get_write_stats()` | 写入统计 | `0.2.0` |
| `get_stats()` | 实例与 engine 状态 | `0.2.0` |

---

## DbEngineAbc / Engine 工厂

| 符号 | 说明 |
|------|------|
| `build_engine_meta(raw_config, is_verbose=False)` | 合并配置 → `EngineConfigMeta`（含 `MysqlSettings` / `PgsqlSettings` / `DuckdbSettings`、`BatchWriteSettings`） |
| `create_engine(meta)` | 返回 `MysqlEngine` / `PgsqlEngine` / `DuckdbEngine` |
| `engine.table_operator(table_name)` | 单表 CRUD（`DbTableAbc`） |
| `engine.schema_manager` | 与 `DatabaseManager.schema_manager` 同一实例 |

业务层**不应**直接依赖各 engine 的 `connector`，除非维护 infra 本身。

---

## SchemaManager（`schema_manager.py`）

| 职责 | 方法示例 |
|------|----------|
| 加载 `core/tables/**/schema.py` | `load_all_schemas`, `load_schema_from_python` |
| DDL 生成（委托 `engines/*/schema_parser`） | `generate_create_table_sql`, `generate_add_column_sql` |
| 建表 | `create_table`, `create_table_with_indexes`, `create_all_tables` |
| 注册表 | `register_table`, `create_registered_tables` |

`core/tables` 下 schema 须含 `update_key`、`storage_domain`（见 [README.md](../README.md)）。

---

## MigrationManager（`migrate_manager.py`）

升级编排门面；实现位于 `migration/`。CLI：

```bash
PYTHONPATH=<repo_root> python -m core.infra.db.migrate_manager plan --pre-mirror-snapshot <path>
PYTHONPATH=<repo_root> python -m core.infra.db.migrate_manager apply --pre-mirror-snapshot <path> [--result-json <path>]
```

| 静态方法 | 说明 |
|----------|------|
| `default_snapshot_path(repo_root)` | 默认 pre-mirror 快照路径 |
| `load_snapshot(path)` / `load_current_schemas(...)` | 旧版 / 当前期望 schema |
| `build_plan(old, new, database_type=..., db=...)` | diff + `ExecutionPlan` |
| `run(pre_mirror_snapshot, ...)` | `MigrationRunResult`；`apply=False` 仅 plan |

Updater 子进程入口：`setup/updater/helper.spawn_database_migration_cli`。

---

## DbBaseModel（`table_queriers/db_base_model.py`）

单表模型；已 `initialize` 时读写优先转发 `engine.table_operator(table_name)`。

常用方法：`count`, `is_exists`, `load`, `load_one`, `load_paginated`, `insert_many`, `upsert_many`, `delete`, `delete_all`，以及表级 `create_table` / `drop_table`、CSV 导入导出等（见源码与 `__test__/test_db_base_model.py`）。

构造：`DbBaseModel(table_name, db=None)`，`db` 默认 `DatabaseManager.get_default()`。

---

## 内部领域模块（`engines/_shared`）

供 infra 与少量工具脚本使用，**非**包根导出：

| 模块 | 职责 |
|------|------|
| `config_parse` | `parse_database_config` |
| `dialect` | 方言归一、标识符引用、`sql_qualify_table_name` |
| `sql_identifiers` | `quote_ddl_identifier` |
| `row_sql` | `to_columns_and_values`, `to_upsert_params`, NaN 清洗 |
| `cursor` | `DatabaseCursor` |
| `query_executor` | `DbQueryExecutor` Protocol |
| `fields` | `Field` 及子类 |
| `batch_write_settings` | mysql/pgsql 写队列配置 |

DuckDB 专有：`engines.duckdb.paths.resolve_duckdb_db_path`、`engines.duckdb.wal_policy`。

---

## 示例

```python
from core.infra.db import DatabaseManager, DbBaseModel

db = DatabaseManager()
db.initialize()
DatabaseManager.set_default(db)

rows = db.execute_sync_query(
    "SELECT * FROM sys_stock_list WHERE code = %s",
    ("000001.SZ",),
)

model = DbBaseModel("sys_stock_list")
n = model.count("code = %s", ("000001.SZ",))
```

DuckDB 按表查询：

```python
rows = db.execute_sync_query_for_table(
    "sys_tag_definition",
    "SELECT * FROM sys_tag_definition LIMIT 10",
)
db.checkpoint_duckdb()
```

---

## 已移除（v0.3.0 勿引用）

- `ConnectionManager`、`TableManager`
- `table_queriers/adapters/`、`DatabaseAdapterFactory`、`BaseDatabaseAdapter`
- `core.infra.db.helpers`、`DBHelper` 门面
- `python -m core.infra.db.migrate`（改为 `migrate_manager`）
- Connector 别名 `MySQLAdapter` / `PostgreSQLAdapter` / `DuckDBAdapter`

---

## 相关文档

- [../README.md](../README.md)
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [DESIGN.md](./DESIGN.md)
- [storage-domains.md](./storage-domains.md)
- [DECISIONS.md](./DECISIONS.md)
- [../engines/ARCHITECTURE.md](../engines/ARCHITECTURE.md)
- [../__test__/README.md](../__test__/README.md)
