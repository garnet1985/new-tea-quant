# 测试用例 — `infra.db` / `core/table_queriers/services`

**覆盖版本：** `0.5.0`  
**本文件位置：** `core/table_queriers/services/__test__/`

## Scope

批量写入：`BatchOperation`、`BatchWriteQueue`。

## 边界

**负责：** `services/` 包  
**不负责：** Engine 级写管道（DuckDB write_pipeline）

| Case 文件 | 说明 |
|-----------|------|
| `test_batch_operation.py` | BatchOperation |
| `test_batch_write_queue.py` | BatchWriteQueue |
