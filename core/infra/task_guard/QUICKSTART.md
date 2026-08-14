# Task Guard — 快速开始

**模块：** `infra.task_guard` · **版本：** `0.2.0`

```python
from core.infra.task_guard import TaskGuard

status = TaskGuard.read_status()
assert "busy" in status

with TaskGuard.lease(kind="tag_run", job_id="demo-1", resource_key="demo/x"):
    assert TaskGuard.read_status()["busy"] is True
```

```bash
python3 -m pytest core/infra/task_guard/__test__/test_api.py -q
```
