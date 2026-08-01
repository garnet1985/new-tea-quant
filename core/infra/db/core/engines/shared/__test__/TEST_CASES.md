# 测试用例 — `infra.db` / `core/engines/shared`

**覆盖版本：** `0.5.0`  
**本文件位置：** `core/engines/shared/__test__/`

## Scope

跨 backend 无方言分支 helper：config_parse、DDL、row_sql、query_rows、schema_introspection。

## 边界

**负责：** `engines/shared` 纯工具  
**不负责：** 具体 Engine 编排

| Case 文件 | 说明 |
|-----------|------|
| `test_config_parse.py` | parse_database_config |
| `test_schema_introspection.py` | 列 introspection |
| `test_row_sql_write.py` | row_sql 写路径 |
| `test_query_rows.py` | query_rows 标量契约 |
| `test_ddl_executor.py` | ddl_executor |
