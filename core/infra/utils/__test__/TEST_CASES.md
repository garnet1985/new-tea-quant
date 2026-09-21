# 测试用例 — `infra.utils`

**模块：** `infra.utils`  
**版本：** `0.2.2`  
## Scope

验证门面 `Utils` 公开逻辑（对齐 `API.md`）。内部实现测放在对应 `core/*/__test__/`。

| 文件 | 说明 |
|------|------|
| `test_api.py` | 公开 API 契约（`force_run`） |
| `../core/date/__test__/test_date_utils.py` | 日期行为 |
| `../core/locale/__test__/test_locale_utils.py` | `is_china` 时区地名，不含东八区 |
| `../core/pkg_index/__test__/test_pkg_index.py` | pip / npm 国内镜像与官方源 |
| `../core/math/__test__/test_deterministic_random.py` | 确定性随机 |
| `../core/markdown/__test__/test_markdown_mgr.py` | Markdown 模版填充 |
