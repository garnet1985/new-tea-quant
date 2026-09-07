# 测试用例 — `infra.db` / `core/table_queriers`

**版本：** `0.3.1`  
**本文件位置：** `core/table_queriers/__test__/`

## Scope

`DbBaseModel` 表模型基类。

## 边界

**负责：** `db_base_model`  
**不负责：** BatchOperation 队列（见 `services/__test__`）

| Case 文件 | 说明 |
|-----------|------|
| `test_db_base_model.py` | DbBaseModel |
