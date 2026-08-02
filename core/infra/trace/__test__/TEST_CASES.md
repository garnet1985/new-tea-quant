# 测试用例 — `infra.trace`

**模块：** `infra.trace`  
**覆盖版本：** `0.2.0`

## Scope

验证门面 `Trace` 与本地队列 / 同意行为（对齐 `API.md`）。

| 文件 | 说明 |
|------|------|
| `test_api.py` | 公开 API 契约（`force_run`） |
| `test_queue.py` | 队列与 sanitize |
| `test_consent.py` | 同意读写 |
| `test_ask_permission.py` | 询问入口 |
