# 测试用例 — `modules.data_source`

**模块：** `modules.data_source`  
**覆盖版本：** `0.4.0`

## Scope

验证门面 `DataSourceManager` 公开逻辑（对齐 `API.md`）。

| 文件 | 说明 |
|------|------|
| `test_api.py` | 公开 API：导出、renew/resolve/list/execute 契约（`force_run`） |

## 实现测（不纳入公开索引）

| 文件 | 说明 |
|------|------|
| `test_manager_behavior.py` | Manager 内部行为 |
| `../core/base_class/__test__/test_data_source_handler.py` | BaseHandler |
| `../core/data_class/__test__/test_api_job.py` | ApiJob |
| `../core/service/date_range/__test__/test_date_range_helper.py` | 日期范围 |
| `../core/service/normalization/__test__/test_normalization_helper.py` | 标准化 |
| `../core/service/pipeline/__test__/test_*.py` | JobPipeline / runner / buffer |
| `../core/service/executor/__test__/test_*.py` | save batch / fetched helper |
| `../core/service/__test__/test_*.py` | rate limiter / sample pool |
| `../core/service/utils/__test__/test_stock_list_dimension_fields.py` | 维度字段 |
| `../core/catalog/__test__/test_freshness_probe.py` | freshness |
| `../core/dev/__test__/test_stock_pool_paths.py` | 样本池路径 |
