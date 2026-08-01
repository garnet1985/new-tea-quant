# Database 模块单元测试

**架构版本：** `0.4.0`（实现位于 `core/`；门面 `Db`）

测试集中在 `core/infra/db/__test__/`（另有部分在 `core/engines/duckdb/__test__/`）。默认使用 **Mock**，不依赖真实数据库。  
契约测试见 [TEST_CASES.md](./TEST_CASES.md) 与 `test_api.py`。

## 目录结构（与源码对应）

```text
core/infra/db/
├── db.py / contracts.py      # 门面与契约
├── core/
│   ├── db_manager.py
│   ├── schema_manager.py
│   ├── migrate_manager.py
│   ├── storage_registry.py
│   ├── engines/              # mysql | pgsql | duckdb | shared | abc
│   ├── migration/
│   └── table_queriers/
└── __test__/
    ├── test_api.py
    ├── TEST_CASES.md
    └── test_*.py             # 实现向单测
```

## 运行测试

```bash
# 项目根目录 — 全量 db 包测试（refactor freeze 下多数需 force_run）
pytest core/infra/db/__test__/ -v

# 契约 / 门面
pytest core/infra/db/__test__/test_api.py -v

# 单文件
pytest core/infra/db/__test__/test_db_manager.py -v
```

## 测试分组说明

| 文件前缀 / 主题 | 覆盖对象 |
|-----------------|----------|
| `test_api` | 门面 `Db`、`contracts`、过渡期包根 re-export |
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
| `test_ddl_executor` | `engines.shared.ddl_executor` |

## 编写约定

1. 测试类：`Test{Subject}`；方法：`test_{behavior}`
2. 优先 Mock connector / engine，避免 CI 依赖外部 MySQL/PostgreSQL/DuckDB 文件
3. 新增 engine 行为时，在对应 `test_*engine*` 或 backend 专项文件中补用例

## 相关文档

- [../API.md](../API.md)
- [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
- [../README.md](../README.md)
