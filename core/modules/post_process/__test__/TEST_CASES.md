# 测试用例 — `modules.post_process`

**模块：** `modules.post_process`  
**版本：** `0.3.2`  

## Scope

验证门面 `PostProcess` 与 contracts 公开逻辑（对齐 `API.md`）。

| 文件 | 说明 |
|------|------|
| `test_api.py` | 公开 API 契约；目录摘要；presenter adapter / post_process 可加载与执行（`force_run`） |

## Cases

| Case | 文件 | 覆盖 |
|------|------|------|
| `test_facade_export` | `test_api.py` | 包根仅导出 PostProcess |
| `test_component_apis` | `test_api.py` | Adapter 发现 / 校验 / 摘要 API |
| `test_post_process_apis` | `test_api.py` | PostProcessor 发现 / 写入 / 执行 API |
| `test_catalog_summaries` | `test_api.py` | summarize / list_*_summaries |
| `test_presenter_adapter_and_post_process_available` | `test_api.py` | presenter 可加载且 enabled |
| `test_build_and_run_presenter_post_process` | `test_api.py` | build_session + run_enabled |
| `test_contracts` | `test_api.py` | Opportunity / Session 协议 |
