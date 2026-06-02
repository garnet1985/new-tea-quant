# JobDispatcher API

**版本：** `0.5.0`（2026-06）

```python
from core.infra.job_dispatcher import (
    Job,
    JobDispatcher,
    JobDispatchSettings,
    ExecuteMode,
    ExecutionBackend,
)
```

---

## JobDispatcher

```python
dispatcher = JobDispatcher(
    settings=JobDispatchSettings(...),
    execute=worker_fn,              # Callable[[dict], Any]
    on_result=callback,             # (JobReport, RunProgress) -> None
    to_executable_job=optional_fn,  # (Job) -> Job | None 跳过
    on_release=optional_cleanup,    # (PreparedJob) -> None
    executor=mock_executor,         # 仅测试注入
)
result = dispatcher.run(jobs, run_name="tag:scenario_x")
```

### `DispatchResult`

| 字段 | 说明 |
|------|------|
| `total` | 输入 job 数 |
| `completed` | execute+report 成功数 |
| `failed` | 各阶段失败数 |
| `failures` | `JobFailure` 列表 |
| `elapsed_seconds` | 耗时 |
| `run_name` | 本次 run 标签 |

---

## JobDispatchSettings

| 字段 | 默认 | 说明 |
|------|------|------|
| `worker` | `PROCESS` | `process` \| `thread` |
| `execute_mode` | `QUEUE` | `queue` \| `batch` \| `elastic` |
| `max_workers` | `"auto"` | `"auto"` 或正整数 |
| `batch_size` | `10` | BATCH 每批 job 数 |
| `prefetch_ahead` | `2` | QUEUE ready 窗口 |
| `ready_queue_limit` | `None` | 默认 `max_workers + prefetch_ahead` |
| `continue_on_failure` | `True` | `False` 时首个失败后 cancel |
| `start_method` | `"spawn"` | 进程池 context |
| `reserve_cores` | `2` | auto 时为 OS 保留核数 |
| `max_workers_cap` | `None` | auto 结果上限 |

---

## WorkerProbe

```python
WorkerProbe.resolve("auto", reserve_cores=1, cap=8) -> int
# auto = mp.cpu_count() - reserve_cores
```

不读 `module_name` / `worker.json`。内存限流仅 ELASTIC（未实现）。

---

## 工厂

```python
create_job_executor(settings, execute=fn) -> JobExecutor
```

由 `JobDispatcher` 内部调用；测试可注入 mock `JobExecutor`。

---

## 类型

| 符号 | 说明 |
|------|------|
| `Job` | `job_id`, `payload` |
| `JobReport` | Worker 返回 |
| `RunProgress` | `finished`, `total`, `ok`, `fail` |
| `JobFailurePhase` | `TO_EXECUTABLE`, `EXECUTE`, `REPORT` |
| `PreparedJob` | 内部 prepare 结果（advanced） |
| `DataRef` | spill 路径预留 |
