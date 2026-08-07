# 测试用例 — `infra.db`（模块根）

**模块：** `infra.db`  
**覆盖版本：** `0.5.0`  
**本文件位置：** `__test__/`

---

## Scope

验证门面 `Db` 与 `contracts`（`test_api.py`），以及少量跨包子集成（`test_integration_*.py`）。  
包内实现单测在各 `core/**/__test__/`。

## 边界

**负责**

- 包根仅导出 `Db`
- `Db` 各命名空间与 `contracts` 类型面
- 跨多个内部包、仍属本模块的集成行为

**不负责**

- 单包细单测（见 `core/**/__test__`）
- updater 编排（见 `setup/updater/__test__`）

**允许的测试类型（本目录）：** `api` · `integration`

---

## Scenario：facade_and_contracts

| Case | 文件 | 说明 |
|------|------|------|
| `test_facade_exported_only` | `test_api.py` | `__all__ == ["Db"]` |
| `test_manager_namespace` | `test_api.py` | manager |
| `test_migration_namespace` | `test_api.py` | migration + snapshot path |
| `test_engine_namespace` | `test_api.py` | engine.build_meta / create |
| `test_duckdb_namespaces` | `test_api.py` | worker_pool / wal 面 |
| `test_worker_pool_should_apply_behavior` | `test_api.py` | off/on/auto 判定 |
| `test_worker_pool_install_config_overlay` | `test_api.py` | overlay env → RO 配置 |
| `test_wal_checkpoint_defaults` | `test_api.py` | WAL checkpoint 默认与覆盖 |
| `test_sql_and_rows_namespaces` | `test_api.py` | sql / rows |
| `test_contracts_symbols` | `test_api.py` | contracts 无游离工厂 |

## Scenario：integration

| Case 文件 | 说明 |
|-----------|------|
| `test_integration_schema_parser.py` | parsers + factory + SchemaManager |
| `test_integration_schema_migration.py` | schema_manager + migration diff/plan |
| `test_integration_decimal_contract.py` | row_sql + duckdb + batch 标量契约 |
