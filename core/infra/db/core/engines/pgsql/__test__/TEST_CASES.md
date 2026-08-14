# 测试用例 — `infra.db` / `core/engines/pgsql`

**覆盖版本：** `0.5.0`  
**本文件位置：** `core/engines/pgsql/__test__/`

## Scope

PostgreSQL engine（server-style connector 契约）单元测试。

## 边界

**负责：** `engines/pgsql`  
**不负责：** MySQL 专属行为（→ `engines/mysql/__test__`）

## Scenario：pgsql_engine

| Case 文件 | 说明 |
|-----------|------|
| `test_server_engine.py` | PgsqlEngine mock：table_operator / load / count / replace / flush |
