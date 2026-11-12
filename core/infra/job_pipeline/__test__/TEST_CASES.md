# Job Pipeline — 测试用例

**版本：** `0.1.0`

| 用例 | 文件 | 说明 |
|------|------|------|
| `test_facade_importable` | `test_api.py` | 包根可导入，公开入口存在 |
| `test_acquire_release_roundtrip` | `test_registry_store.py` | lease 占槽 / 释放；忙则 busy |
| `test_stale_pid_is_cleared` | `test_registry_store.py` | 死 pid 的 running 槽被丢弃 |
| `test_request_cancel_running` | `test_registry_store.py` | cancel → `cancel_requested` / `is_cancel_requested` |
| `test_recover_dead_pid_advances_queue` | `test_registry_store.py` | 死 pid 清槽并泵 pending |
| `test_old_started_at_alone_is_not_stale_within_12h` | `test_registry_store.py` | 无 Progress 的长跑不因 2h 误标 |
| `test_stale_when_progress_heartbeat_old` | `test_registry_store.py` | Progress 久未写入 → stale；abandon |
