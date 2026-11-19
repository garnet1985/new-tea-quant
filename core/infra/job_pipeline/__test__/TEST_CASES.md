# 测试用例 — JobPipeline 公开 API

**模块：** `infra.job_pipeline` · **版本：** `0.1.0`

**最低支持核心版本：** `>=0.6.0`

**本文件位置：** `__test__/`

---

## Scope

验证模块根 `API.md` 中 `JobPipeline` 公开入口的契约行为。

## 边界

**负责**

- Facade 可导入与公开方法存在
- 只读面、lease、入队 / submit、取消、recover / abandon、handler 注册与泵队列

**不负责**

- BFF / FED HTTP 与 UI
- `infra.progress` 内部正确性（仅作可选 fixture）

**允许的测试类型（本目录）：** `api` · 包内单测（`test_registry_store.py`）

---

## Scenario：Facade 与只读面

对应 API：`get_running_job` / `has_running_job` / `list_jobs` / `get_job` / `running_lease`

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_facade_importable` | `test_api.py` | 包根导出与公开入口可调用 |
| `test_running_lease_and_read_apis` | `test_api.py` | lease 占槽 / 忙则 busy；读面一致 |
| `test_get_running_job_not_stale_within_wall_clock` | `test_api.py` | 无 Progress 的 2h 长跑不误标 stale |
| `test_acquire_release_roundtrip` | `test_registry_store.py` | lease 往返（包内） |
| `test_stale_pid_is_cleared` | `test_registry_store.py` | 死 pid 读面丢弃（包内） |
| `test_old_started_at_alone_is_not_stale_within_12h` | `test_registry_store.py` | started_at 兜底策略（包内） |
| `test_stale_when_progress_heartbeat_old` | `test_registry_store.py` | Progress 久未写入 → stale（包内） |

---

## Scenario：入队 / submit / handler

对应 API：`register_handler` / `enqueue` / `submit` / `advance` / `notify_job_finished`

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_register_handler_rejects_empty_kind` | `test_api.py` | 空 kind 拒绝 |
| `test_enqueue_submit_cancel_pending` | `test_api.py` | enqueue + cancel pending |
| `test_submit_idle_calls_handler` | `test_api.py` | 空闲 submit 调 handler |
| `test_submit_busy_enqueues` | `test_api.py` | 忙则入队 |
| `test_notify_job_finished_advances` | `test_api.py` | notify → advance 泵队 |

---

## Scenario：取消 / 恢复 / 放弃

对应 API：`cancel` / `is_cancel_requested` / `recover` / `abandon`

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_cancel_running_sets_flag` | `test_api.py` | running cancel → cancel_requested |
| `test_recover_dead_pid_and_advance` | `test_api.py` | 死 pid recover 并泵 pending |
| `test_abandon_releases_running` | `test_api.py` | abandon 清槽 |
| `test_request_cancel_running` | `test_registry_store.py` | cancel 标志（包内） |
| `test_recover_dead_pid_advances_queue` | `test_registry_store.py` | recover 泵队（包内） |
