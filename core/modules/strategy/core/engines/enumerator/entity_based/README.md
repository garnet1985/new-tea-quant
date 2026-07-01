# entity_based 流程

## 职责边界（Strategy vs BacktestEngine）

| 层 | 负责 |
|----|------|
| **BacktestEngine.entity_based** | 多 job 并行、dispatch probe、worker 进程池 |
| **Strategy（本目录）** | 单股 timeline：hooks、scan、opportunity CSV |

```
resolver/jobs.py      → 每股一 job
pipeline.py           → BacktestEngine.entity_based.run + execute_fn
                        RunCallbacks.on_job_init / on_job_release
worker.py             → execute_fn 入口（消费 context.init）
job_init.py           → on_job_init：批量装载 + 建 cursor
executor.py           → execute：逐 bar 跑 hook（不再读 DB）
execute_payload.py    → 入参 dataclass
execute_result.py     → 返回值 dataclass
context/data.py       → EntityBasedDataContext
```

## 子进程数据流

```
BacktestEngine 子进程
  1. RunCallbacks.on_job_init   ← 批量装载 + DataCursor
  2. execute_fn (worker.run)    ← 只截取 + hook
  3. RunCallbacks.on_job_release
```

settings 须显式声明 `simulation.execution_mode: entity_based`。
