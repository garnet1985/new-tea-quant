# 测试用例 — `infra.db` / `core`

**覆盖版本：** `0.5.0`  
**本文件位置：** `core/__test__/`

## Scope

`DatabaseManager`、`SchemaManager`、`StorageRegistry` 单元测试。

## 边界

**负责：** 管理器初始化、DDL 委托、schema 加载、存储域注册  
**不负责：** 具体 engine 方言细节、迁移 plan 执行

| Case 文件 | 说明 |
|-----------|------|
| `test_db_manager.py` | DatabaseManager |
| `test_db_manager_ddl_api.py` | DDL API 委托 |
| `test_db_schema_manager.py` | SchemaManager |
| `test_storage_registry.py` | StorageRegistry |
