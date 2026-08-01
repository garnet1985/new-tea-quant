# 测试用例 — `infra.db` / `core/engines/duckdb`

**覆盖版本：** `0.5.0`  
**本文件位置：** `core/engines/duckdb/__test__/`

## Scope

DuckDB engine、域目录、WAL、connector 线程、process_pool_scope。

## 边界

**负责：** `engines/duckdb` 包内行为  
**不负责：** 跨模块业务（Tag/Strategy）；公开门面见根 `test_api.py`

| Case 文件 | 说明 |
|-----------|------|
| `test_duckdb_engine.py` | DuckdbEngine |
| `test_duckdb_domain_catalog.py` | domain catalog |
| `test_duckdb_wal_policy.py` | WAL / checkpoint |
| `test_duckdb_wal_policy_helpers.py` | wal_policy helpers |
| `test_duckdb_connector_threading.py` | connector 线程 |
| `test_process_pool_scope_release.py` | 主进程句柄释放 |
| `test_process_pool_scope_job_pipeline.py` | job pipeline 协作 |
