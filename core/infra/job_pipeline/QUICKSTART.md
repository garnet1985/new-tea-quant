# Job Pipeline — 快速开始

**模块：** `infra.job_pipeline` · **版本：** `0.1.0`

**最低支持核心版本：** `>=0.6.0`

只读、入队、互斥与协作取消均已可用。设计见 [docs/DECISIONS.md](./docs/DECISIONS.md)；完整契约见 [API.md](./API.md)。

```python
from core.infra.job_pipeline import JobPipeline

# BFF 启动时注册一次（kind → start_now）
# JobPipeline.register_handler("tag_run", handler)

job = JobPipeline.get_running_job()  # None 或快照（可挂 progress 摘要）
jobs = JobPipeline.list_jobs()       # running（0～1）+ pending

# 公开入口：空闲开跑，忙则入队
out = JobPipeline.submit({
    "kind": "tag_run",
    "resource_key": "demo/x",
    "label": "Tag demo/x",
    "payload": {"tag_key": "demo/x"},
})

# 后台循环内协作取消
if JobPipeline.is_cancel_requested(job_id):
    ...

# launcher finally
JobPipeline.notify_job_finished()
```

```bash
python3 -m pytest core/infra/job_pipeline -q
```
