# Database 模块单元测试

**架构版本：** `0.3.0`（Engine 挂载）

测试集中在 `core/infra/db/__test__/`，与源码同包；默认使用 **Mock**，不依赖真实数据库。

## 目录结构（与源码对应）

```text
core/infra/db/
├── db_manager.py
├── schema_manager.py
├── migrate_manager.py
├── storage_registry.py
├── engines/                    # mysql | pgsql | duckdb + _shared
├── migration/                  # diff / plan / execute（由 migrate_manager 门面调用）
├── table_queriers/
│   ├── db_base_model.py
│   └── services/               # BatchOperation, BatchWriteQueue
└── __test__/
    ├── test_db_manager.py
    ├── test_db_manager_ddl_api.py
    ├── test_db_schema_manager.py
    ├── test_schema_parser.py
    ├── test_config_parse.py
    ├── test_storage_registry.py
    ├── test_db_base_model.py
    ├── test_batch_write_queue.py
    ├── test_ddl_executor.py
    ├── test_engine_settings.py
    ├── test_engines_skeleton.py
    ├── test_server_engine.py
    ├── test_duckdb_engine.py
    ├── test_duckdb_domain_catalog.py
    ├── test_duckdb_wal_policy.py
    ├── test_duckdb_wal_policy_helpers.py
    ├── test_schema_migration.py
    ├── test_migration_runner.py
    ├── test_migration_history.py
    ├── test_plan_prune.py
    └── test_updater_migration_spawn.py
```

已删除、**无**对应测试目录：`connection_management/`、`table_management/`、`table_queriers/adapters/`、`helpers/`。

## 运行测试

```bash
# 项目根目录 — 全量 db 包测试
pytest core/infra/db/__test__/ -v

# 单文件
pytest core/infra/db/__test__/test_db_manager.py -v

# 单用例
pytest core/infra/db/__test__/test_db_manager.py::TestDatabaseManager::test_init_with_config -v
```

## 测试分组说明

| 文件前缀 / 主题 | 覆盖对象 |
|-----------------|----------|
| `test_db_manager*` | `DatabaseManager` 初始化、DDL API、默认实例 |
| `test_db_schema_manager`, `test_schema_parser` | `SchemaManager`、各 engine `schema_parser` |
| `test_config_parse`, `test_engine_settings` | `parse_database_config`、`EngineConfigMeta` |
| `test_storage_registry` | `StorageRegistry`、DuckDB 域注册 |
| `test_db_base_model` | `DbBaseModel`、`row_sql` 工具 |
| `test_batch_write_queue` | `BatchWriteQueue`（mysql/pgsql） |
| `test_*engine*`, `test_server_engine` | Engine 骨架、connector 契约 |
| `test_duckdb_*` | DuckDB 域目录、WAL、`wal_policy` |
| `test_schema_migration`, `test_migration_*`, `test_plan_prune` | `migration/` 管线 |
| `test_migration_runner` | `migrate_manager` CLI |
| `test_updater_migration_spawn` | updater 子进程集成（轻量） |
| `test_ddl_executor` | `engines._shared.ddl_executor` |

## 编写约定

1. 测试类：`Test{Subject}`；方法：`test_{behavior}`
2. 优先 Mock connector / engine，避免 CI 依赖外部 MySQL/PostgreSQL/DuckDB 文件
3. 新增 engine 行为时，在对应 `test_*engine*` 或 backend 专项文件中补用例

## 相关文档

- [../docs/API.md](../docs/API.md)
- [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
- [../README.md](../README.md)
