# JobPipeline API

**版本：** `0.2.0`（2026-06）

**失败语义：** `execute` 未捕获异常 → 仅 `DispatchResult.failures`；返回 `success=False` 的 dict → 仍触发 `on_result`。

```python
from core.infra.job_pipeline import (
    Job,
    JobContext,
    JobPipeline,
    JobPipelineSettings,
    ExecuteMode,
    ExecutionBackend,
)
```

子模块（按需深入）：

| 路径 | 内容 |
|------|------|
| `pipeline/` | `JobPipeline`、`JobPipelineSettings`、hooks |
| `runtime/` | `create_job_executor`、`ProcessJobExecutor` |
| `profile/` | `WorkerProbe`、`WorkerProfiles`、`profile_dispatch_config` |
| `types.py` | `Job`、`JobReport`、`DispatchResult` 等 |

---

## JobPipeline

```python
def execute(context: JobContext) -> Any: ...

dispatcher = JobPipeline(
    settings=JobPipelineSettings(...),
    execute=execute,
    on_result=callback,             # (JobReport, RunProgress) -> None
    on_release=optional_cleanup,    # (JobContext) -> None
    executor=mock_executor,         # 仅测试注入
)
result = dispatcher.run(jobs, run_name="tag:scenario_x")
```

### `JobContext`（子进程入参）

| 字段 | 说明 |
|------|------|
| `job_id` | 当前 dispatch job |
| `payload` | 业务数据；含 `_job_id` |
| `run_name` | 本次 run 标签 |

### `DispatchResult`

| 字段 | 说明 |
|------|------|
| `total` | 输入 job 数 |
| `completed` | execute+report 成功数 |
| `failed` | 失败数 |
| `failures` | `JobFailure` 列表 |
| `elapsed_seconds` | 耗时 |
| `run_name` | 本次 run 标签 |

---

## JobPipelineSettings

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
| `reserve_cores` | `1` | auto 时为 OS 保留核数 |
| `max_parallel_jobs_cap` | `None` | auto 时 ProcessPool 同时 in-flight job 数上限 |

---

## WorkerProbe

```python
WorkerProbe.resolve("auto", reserve_cores=1, cap=8) -> int
```

---

## 类型

| 符号 | 说明 |
|------|------|
| `Job` | `job_id`, `payload` |
| `JobContext` | 传给 `execute` 的 job 作用域 |
| `JobReport` | Worker 返回 |
| `RunProgress` | `finished`, `total`, `ok`, `fail` |
| `JobFailurePhase` | `EXECUTE`, `REPORT` |
