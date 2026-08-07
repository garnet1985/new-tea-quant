# 测试用例 — `infra.db` / `core/engines/shared`

**覆盖版本：** `0.5.0`  
**本文件位置：** `core/engines/shared/__test__/`

## Scope

跨 backend 无方言分支的 **helper unit**（config_parse、DDL、row_sql、query_rows、introspection）。  
本目录有 UT 即可；**不索引业务 Scenario**（业务见模块根 `__test__/TEST_CASES.md`）。

## 边界

**负责：** `engines/shared` 工具函数正确性  
**不负责：** Engine 编排、公开门面契约
