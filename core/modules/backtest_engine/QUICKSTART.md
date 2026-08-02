# Backtest Engine — 快速开始

**模块：** `modules.backtest_engine` · **版本：** `0.4.0`

## 最小示例（entity_based）

```python
from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import JobContext, RunCallbacks

def execute_fn(ctx: JobContext) -> dict:
    return {"success": True, "job_id": ctx.job_id}

jobs = [{"id": "000001.SZ", "payload": {"entity_specified": [{"id": "000001.SZ"}]}}]

result = BacktestEngine.entity_based.run(
    jobs,
    execute_fn=execute_fn,
    task_name="demo",
    callbacks=RunCallbacks(on_task_result=lambda r, p: None),
)
print(result.success, result.completed_jobs)
```

**预期结果：** 空或有效 jobs 时返回 `RunResult`，`mode == "entity_based"`。

## 下一步

- [API.md](./API.md)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)

```bash
NTQ_TESTS_ENABLED=1 python -m pytest core/modules/backtest_engine/__test__/test_api.py -q
```
