# 测试用例 — `modules.data_manager`

**模块：** `modules.data_manager`  
**覆盖版本：** `0.4.0`

## Scope

验证门面 `DataManager` 公开逻辑（对齐 `API.md`）。

| 文件 | 说明 |
|------|------|
| `test_api.py` | 公开 API：导出、领域属性、`get_table`、contracts（`force_run`） |

## 实现测（不纳入公开索引）

| 文件 | 说明 |
|------|------|
| `test_data_manager_concurrent_init.py` | 单例并发 initialize |
| `../core/data_services/calendar/__test__/test_calendar_service.py` | 交易日历 |
| `../core/data_services/stock/__test__/test_kline_load_output.py` | K 线 load 输出 |
| `../core/data_services/stock/sub_services/__test__/test_list_service_*.py` | 列表/抽样/存活 |
| `../core/data_services/stock/sub_services/__test__/test_corporate_finance_ann_date.py` | 财报公告日 |
