# 测试用例 — `infra.utils`

**模块：** `infra.utils`  
**覆盖版本：** `0.2.0`

## Scope

验证门面 `Utils` 公开逻辑（对齐 `API.md`）。内部实现测放在对应 `core/*/__test__/`。

| 文件 | 说明 |
|------|------|
| `test_api.py` | 公开 API 契约（`force_run`） |
| `../core/date/__test__/test_date_utils.py` | 日期行为 |
| `../core/math/__test__/test_deterministic_random.py` | 确定性随机 |
| `../core/markdown/__test__/test_markdown_mgr.py` | Markdown 模版填充 |
