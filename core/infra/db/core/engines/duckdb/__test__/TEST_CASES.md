# 测试用例 — `infra.db` / `core/engines/duckdb`

**覆盖版本：** `0.5.0`  
**本文件位置：** `core/engines/duckdb/__test__/`

## Scope

DuckDB engine、存储域目录、WAL/checkpoint、worker 池协作等 **包内业务行为**。  
wal_policy helpers 等纯工具有 UT 即可，不在本文逐条索引。

## 边界

**负责：** `engines/duckdb` 包内行为  
**不负责：** 跨模块业务（Tag/Strategy）；公开门面见根 `test_api.py`

## Scenario：duckdb_engine

| Case 文件 | 说明 |
|-----------|------|
| `test_duckdb_engine.py` | DuckdbEngine 挂载与表操作路由 |
| `test_duckdb_domain_catalog.py` | 域目录 / 表文件地图 |
| `test_duckdb_wal_policy.py` | WAL 损坏恢复策略 |
| `test_duckdb_connector_threading.py` | 单连接并发查询 |
| `test_process_pool_scope_release.py` | 主进程句柄释放 |
| `test_process_pool_scope_job_pipeline.py` | 与 job pipeline 协作判定 |
