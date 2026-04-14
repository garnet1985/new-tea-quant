# Worker 模块 API 文档

本文档采用统一 API 条目格式。仅覆盖对外导出、且上层常用入口；细粒度协议见各子目录实现与 `multi_process/README.md` / `multi_thread/README.md`。

---

## TaskType

### 函数名
`TaskType`（枚举）

- 状态：`stable`
- 描述：任务特性，用于 `ProcessWorker.calculate_workers` / `resolve_max_workers('auto')` 与 Worker 配置。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：枚举类；成员：`CPU_INTENSIVE`、`IO_INTENSIVE`、`MIXED`。

---

## ProcessWorker

### 函数名
`ProcessWorker.calculate_workers(task_type: TaskType, reserve_cores: int = 2) -> int`

- 状态：`stable`
- 描述：按任务类型与预留核数建议进程数（至少 1）。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `task_type` | `TaskType` | 必填 |
| `reserve_cores` (可选) | `int` | 默认 `2` |

- 返回值：`int`

---

### 函数名
`ProcessWorker.resolve_max_workers(max_workers: Union[str, int], module_name: str) -> int`

- 状态：`stable`
- 描述：`max_workers=='auto'` 时从 `ConfigManager.get_module_config(module_name)` 取 `task_type`/`reserve_cores` 并调用 `calculate_workers`；否则 `_validate_workers` 限制上界。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `max_workers` | `str | int` | `'auto'` 或正整数 |
| `module_name` | `str` | 与 worker 配置中模块名一致 |

- 返回值：`int`

---

### 函数名
`ProcessWorker.__init__(max_workers: Optional[int] = None, execution_mode: ExecutionMode = QUEUE, batch_size: Optional[int] = None, job_executor: Optional[Callable] = None, enable_monitoring: bool = True, timeout: float = 300.0, is_verbose: bool = False, debug: bool = False, start_method: str = "spawn")`

- 状态：`stable`
- 描述：多进程执行器；`ExecutionMode` 对外导出名为 `ProcessExecutionMode`。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `max_workers` (可选) | `Optional[int]` | 默认 `None` 等价 `cpu_count()`；否则与 `cpu_count` 取 min |
| `execution_mode` (可选) | `ProcessExecutionMode` | `BATCH` / `QUEUE` |
| `batch_size` (可选) | `Optional[int]` | 仅 BATCH；默认 `cpu_count()` |
| `job_executor` (可选) | `Optional[Callable]` | 单 job 执行函数 |
| `enable_monitoring` (可选) | `bool` | 默认 `True` |
| `timeout` (可选) | `float` | 秒；默认 `300` |
| `is_verbose` (可选) | `bool` | 默认 `False` |
| `debug` (可选) | `bool` | 默认 `False` |
| `start_method` (可选) | `str` | `spawn` / `fork` / `forkserver` |

- 返回值：`ProcessWorker` 实例

---

### 函数名
`ProcessWorker.set_job_executor(job_executor: Callable) -> None`

- 状态：`stable`
- 描述：设置任务执行函数。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `job_executor` | `Callable` | 必填 |

- 返回值：`None`

---

### 函数名
`ProcessWorker.add_job(job_id: str, job_payload: Any) -> None`

- 状态：`stable`
- 描述：追加单任务到内部队列。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `job_id` | `str` | 必填 |
| `job_payload` | `Any` | 必填 |

- 返回值：`None`

---

### 函数名
`ProcessWorker.add_jobs(jobs: List[Dict[str, Any]]) -> None`

- 状态：`stable`
- 描述：批量追加；`payload` 或 `data` 作为负载。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `jobs` | `List[Dict]` | 每项需含 `id` |

- 返回值：`None`

---

### 函数名
`ProcessWorker.run_jobs(jobs: Optional[List[Dict[str, Any]]] = None, total_jobs: Optional[int] = None) -> Dict[str, Any]`

- 状态：`stable`
- 描述：执行队列中任务（或传入的 `jobs`）；返回含统计信息的字典（字段以实现为准）。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `jobs` (可选) | `Optional[List[Dict]]` | 传入则装入队列 |
| `total_jobs` (可选) | `Optional[int]` | 部分模式用于进度 |

- 返回值：`Dict[str, Any]`

---

### 函数名
`ProcessWorker.print_stats() -> None`

- 状态：`stable`
- 描述：打印执行统计。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`None`

---

## MultiThreadWorker

### 函数名
`MultiThreadWorker.__init__(max_workers: int = 5, execution_mode: ExecutionMode = PARALLEL, job_executor: Optional[Callable] = None, enable_monitoring: bool = True, timeout: float = 30.0, is_verbose: bool = False, debug: bool = False)`

- 状态：`stable`
- 描述：`ExecutionMode` 导出为 `ThreadExecutionMode`（`SERIAL`/`PARALLEL`）。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `max_workers` (可选) | `int` | 默认 `5` |
| `execution_mode` (可选) | `ThreadExecutionMode` | 默认并行 |
| `job_executor` (可选) | `Optional[Callable]` | 默认 `None` |
| `enable_monitoring` (可选) | `bool` | 默认 `True` |
| `timeout` (可选) | `float` | 默认 `30` |
| `is_verbose` (可选) | `bool` | 默认 `False` |
| `debug` (可选) | `bool` | 默认 `False` |

- 返回值：`MultiThreadWorker`

---

### 函数名
`MultiThreadWorker.set_job_executor(executor_func: Callable) -> None`

- 状态：`stable`
- 描述：设置执行函数。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `executor_func` | `Callable` | 必填 |

- 返回值：`None`

---

### 函数名
`MultiThreadWorker.add_job(job_id: str, job_data: Any) -> None`

- 状态：`stable`
- 描述：入队单任务。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `job_id` | `str` | 必填 |
| `job_data` | `Any` | 必填 |

- 返回值：`None`

---

### 函数名
`MultiThreadWorker.add_jobs(jobs: List[Dict[str, Any]]) -> None`

- 状态：`stable`
- 描述：批量入队。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `jobs` | `List[Dict]` | 必填 |

- 返回值：`None`

---

### 函数名
`MultiThreadWorker.run_jobs(jobs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]`

- 状态：`stable`
- 描述：执行线程侧任务并返回统计字典。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `jobs` (可选) | `Optional[List[Dict]]` | 可直接传入任务列表 |

- 返回值：`Dict[str, Any]`

---

## Orchestrator

### 函数名
`Orchestrator.__init__(executor: Executor, job_source: JobSource, scheduler: Optional[Scheduler] = None, monitor: Optional[Monitor] = None, aggregator: Optional[Aggregator] = None, error_handler: Optional[ErrorHandler] = None)`

- 状态：`stable`
- 描述：组合模块化组件；各参数为实现类实例。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `executor` | `Executor` | 必填 |
| `job_source` | `JobSource` | 必填 |
| `scheduler` (可选) | `Optional[Scheduler]` | 默认 `None` |
| `monitor` (可选) | `Optional[Monitor]` | 默认 `None` |
| `aggregator` (可选) | `Optional[Aggregator]` | 默认 `None` |
| `error_handler` (可选) | `Optional[ErrorHandler]` | 默认 `None` |

- 返回值：`Orchestrator`

---

### 函数名
`Orchestrator.run() -> Dict[str, Any]`

- 状态：`stable`
- 描述：按调度器/任务源循环执行，聚合与监控结果写入返回字典。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：含 `results`、`summary` 等键的字典。

---

## MemoryAwareBatchScheduler（兼容导出）

### 函数名
`MemoryAwareBatchScheduler`（类）

- 状态：`stable`
- 描述：根目录 `memory_aware_scheduler.py` 提供的旧版内存感知批调度；新代码优先 `schedulers.memory_aware_scheduler.MemoryAwareScheduler` 与 Orchestrator。
- 诞生版本：`0.2.0`
- params：

无（构造参数见源码与类 docstring）

- 返回值：实例

---

## 模块化组件（导出类一览）

以下类型由 `core.infra.worker` 包导出，构造参数与协议方法以各源文件为准：

| 导出名 | 说明 |
|--------|------|
| `Executor` / `MultiThreadExecutor` / `ProcessExecutor` | 执行一批 job |
| `JobSource` / `ListJobSource` | 任务源 |
| `Monitor` / `MemoryMonitor` | 监控 |
| `Scheduler` / `MemoryAwareScheduler` | 调度 batch 大小 |
| `Aggregator` / `SimpleAggregator` | 结果聚合 |
| `ErrorHandler` / `ErrorAction` / `SimpleErrorHandler` | 错误处理 |
| `JobResult` / `JobStatus`（executors 命名空间） | 与 executors 协议对齐的结果类型 |

## 示例

```python
from core.infra.worker import ProcessWorker, ProcessExecutionMode

def job_fn(payload):
    return payload

w = ProcessWorker(job_executor=job_fn, is_verbose=False)
w.add_job("1", {"x": 1})
w.run_jobs()
```

---

## 相关文档

- [架构总览](./ARCHITECTURE.md)
- [详细设计](./DESIGN.md)
- [决策记录](./DECISIONS.md)