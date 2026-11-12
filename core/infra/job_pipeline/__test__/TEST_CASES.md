# Job Pipeline — 测试用例

**版本：** `0.1.0`

| 用例 | 文件 | 说明 |
|------|------|------|
| `test_facade_importable` | `test_api.py` | 包根可导入，公开入口存在 |
| `test_acquire_release_roundtrip` | `test_registry_store.py` | lease 占槽 / 释放；忙则 busy |
| `test_stale_pid_is_cleared` | `test_registry_store.py` | 死 pid 的 running 槽被丢弃 |
| `test_request_cancel_running` | `test_registry_store.py` | cancel → `cancel_requested` / `is_cancel_requested` |
