# 测试用例 — `infra.db` / `core/engines/mysql`

**覆盖版本：** `0.5.0`  
**本文件位置：** `core/engines/mysql/__test__/`

## Scope

MySQL engine（含 server-style connector 契约）单元测试。

## 边界

**负责：** `engines/mysql`  
**不负责：** PostgreSQL 专属行为

| Case 文件 | 说明 |
|-----------|------|
| `test_server_engine.py` | MysqlEngine mock 契约 |
