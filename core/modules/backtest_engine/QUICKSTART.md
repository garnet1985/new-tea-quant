# Backtest Engine — 快速开始

**模块：** `modules.backtest_engine` · **版本：** `0.2.0`

## 最小示例（entity_based）

```python
from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import JobContext, RunCallbacks

def on_tick(ctx: JobContext, point: str, index: int) -> None:
    _ = (ctx, point, index)  # 业务按日推进

jobs = [
    {
        "id": "000001.SZ",
        "payload": {"entity_specified": [{"id": "000001.SZ"}]},
    }
]

result = BacktestEngine.entity_based.run(
    jobs,
    start="20240102",
    end="20240103",
    timeline=["20240102", "20240103"],
    task_name="demo",
    callbacks=RunCallbacks(on_tick=on_tick),
)
print(result.success, result.mode, result.completed_jobs)
```

**预期结果：** 返回 `RunResult`，`mode == "entity_based"`。空 `jobs` 时可不传 window，直接成功。

> 不要传 `execute_fn=`：引擎内置 worker，业务挂在 `RunCallbacks`（尤其 `on_tick` / `on_before_task_start`）。

## 下一步

- [API.md](./API.md)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)

```bash
python3 -m pytest core/modules/backtest_engine/__test__/test_api.py -q
```
