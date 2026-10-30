# Job Pipeline — 快速开始

**模块：** `infra.job_pipeline` · **版本：** `0.1.0`

只读面可用；`submit` 尚未实现。设计见 [docs/DESIGN.md](./docs/DESIGN.md)。

```python
from core.infra.job_pipeline import JobPipeline

job = JobPipeline.get_running_job()  # None 或快照 dict
jobs = JobPipeline.list_jobs()       # [] 或 [running]
# JobPipeline.submit({...})  → NotImplementedError
```

```bash
python3 -m pytest core/infra/job_pipeline/__test__/test_api.py -q
```
