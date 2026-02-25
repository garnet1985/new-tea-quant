# Worker 模块 API 文档

按「描述、函数签名、参数、输出、示例」列出 Worker 模块中**应用/基础设施代码会直接使用的入口**；内部 helper 和抽象基类不列入。架构与设计见 `architecture.md` / `decisions.md`，快速上手见 `overview.md`。

---

## 传统 Worker 接口（ProcessWorker / MultiThreadWorker）

### ProcessWorker（构造函数）

**描述**：基于 `multiprocessing` 的多进程任务执行器，适合 CPU 密集或混合型任务。支持 Batch / 队列两种执行模式，并内置进度统计和日志输出。

**函数签名**：`ProcessWorker(max_workers: Optional[int] = None, execution_mode: ExecutionMode = ExecutionMode.QUEUE, batch_size: Optional[int] = None, job_executor: Optional[Callable] = None, enable_monitoring: bool = True, timeout: float = 300.0, is_verbose: bool = False, debug: bool = False, start_method: str = "spawn")`

**参数（摘选）**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `max_workers` | `int \| None` | 最大并行进程数；`None` 时使用 CPU 核数 |
| `execution_mode` | `ExecutionMode` | 执行模式：`BATCH` 或 `QUEUE` |
| `batch_size` | `int \| None` | Batch 模式时每批大小；默认使用 CPU 核数 |
| `job_executor` | `Callable` | 任务执行函数，签名约定为 `func(payload) -> Any` |
| `timeout` | `float` | 单个任务超时时间（秒） |
| `is_verbose` | `bool` | 是否打印详细日志 |

**输出**：无（构造实例）

**Example**：

```python
from core.infra.worker import ProcessWorker, ProcessExecutionMode

def run_job(payload):
    return payload["x"] + payload["y"]

worker = ProcessWorker(
    max_workers=None,
    execution_mode=ProcessExecutionMode.QUEUE,
    job_executor=run_job,
    is_verbose=True,
)
```

---

### ProcessWorker.run_jobs

**描述**：执行一批任务，支持单次或分批调用，并返回统计信息。

**函数签名**：`ProcessWorker.run_jobs(jobs: Optional[List[Dict[str, Any]]] = None, total_jobs: Optional[int] = None) -> Dict[str, Any]`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `jobs` | `List[Dict[str, Any]] \| None` | 任务列表，每个任务形如 `{"id": str, "payload": Any}` 或 `{"id": str, "data": Any}` |
| `total_jobs` | `int \| None` | 总任务数（分批执行时用于正确计算进度） |

**输出**：`Dict[str, Any]` —— 含 `total_jobs`、`completed_jobs`、`failed_jobs`、`total_duration` 等统计字段。

**Example**：

```python
jobs = [{"id": f"job_{i}", "payload": {"x": i, "y": 1}} for i in range(100)]
stats = worker.run_jobs(jobs)
results = worker.get_results()
```

---

### ProcessWorker.get_results / get_successful_results / get_failed_results

**描述**：获取任务执行结果列表，或只获取成功/失败的结果。

**函数签名**：

- `ProcessWorker.get_results() -> List[JobResult]`  
- `ProcessWorker.get_successful_results() -> List[JobResult]`  
- `ProcessWorker.get_failed_results() -> List[JobResult]`

**输出**：`List[JobResult]` —— 每个结果包含 `job_id`、`status`、`result`、`error`、`duration` 等。

---

### ProcessWorker.print_stats / reset

**描述**：打印运行统计信息，或重置执行器状态（清空任务、结果和统计信息）。

**函数签名**：

- `ProcessWorker.print_stats() -> None`  
- `ProcessWorker.reset() -> None`

---

### ProcessWorker.resolve_max_workers（推荐配合 ConfigManager 使用）

**描述**：根据模块任务类型（CPU/IO/Mixed）和预留核心数自动计算合适的 worker 数量，内部会通过 `ConfigManager.get_module_config()` 读取 Worker 配置。

**函数签名**：`ProcessWorker.resolve_max_workers(max_workers: Union[str, int], module_name: str) -> int`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `max_workers` | `str \| int` | `"auto"` 表示自动计算，或显式指定数字 |
| `module_name` | `str` | 模块名称，用于 worker 配置（如 `"OpportunityEnumerator"`） |

**输出**：`int` —— 实际使用的 worker 数量。

---

### MultiThreadWorker（构造函数）

**描述**：基于 `ThreadPoolExecutor` 的轻量级多线程任务执行器，适合 IO 密集型任务或轻量并发场景。

**函数签名**：`MultiThreadWorker(max_workers: int = 5, execution_mode: ExecutionMode = ExecutionMode.PARALLEL, job_executor: Optional[Callable] = None, enable_monitoring: bool = True, timeout: float = 30.0, is_verbose: bool = False, debug: bool = False)`

**输出**：无（构造实例）

**Example**：

```python
from core.infra.worker import MultiThreadWorker, ThreadExecutionMode

def fetch_url(url: str) -> str:
    # 伪代码：实际可使用 requests 等库
    return f"content of {url}"

worker = MultiThreadWorker(
    max_workers=20,
    execution_mode=ThreadExecutionMode.PARALLEL,
    job_executor=fetch_url,
    is_verbose=True,
)

jobs = [{"id": f"url_{i}", "data": f"https://example.com/{i}"} for i in range(100)]
stats = worker.run_jobs(jobs)
results = worker.get_results()
```

---

## 模块化执行器与任务源

### ProcessExecutor（多进程执行器）

**描述**：新的模块化架构下的多进程执行器，是对 `ProcessWorker` 的轻量封装，便于与 `Orchestrator` 组合使用。

**函数签名**：`ProcessExecutor(max_workers: Optional[int] = None, execution_mode: ExecutionMode = ExecutionMode.QUEUE, job_executor: Optional[Callable] = None, is_verbose: bool = False)`

**输出**：`ProcessExecutor` 实例，实现 `Executor` 接口。

**Example**：

```python
from core.infra.worker import ProcessExecutor

def run_job(payload):
    return payload["x"] * 2

executor = ProcessExecutor(
    max_workers=None,
    job_executor=run_job,
    is_verbose=True,
)

jobs = [{"id": str(i), "data": {"x": i}} for i in range(100)]
results = executor.run_jobs(jobs)
```

---

### ProcessExecutor.run_jobs

**描述**：执行一批任务并返回 `JobResult` 列表，内部通过 `ProcessWorker.run_jobs` 完成。

**函数签名**：`ProcessExecutor.run_jobs(jobs: List[Dict[str, Any]], total_jobs: Optional[int] = None) -> List[JobResult]`

---

### ListJobSource

**描述**：简单的列表任务源，从预加载的 Python 列表中按批次提供任务。

**函数签名**：`ListJobSource(jobs: List[Any])`

**常用方法**：

- `ListJobSource.get_batch(size: int) -> List[Any]` —— 获取一批任务  
- `ListJobSource.has_more() -> bool` —— 是否还有任务  
- `ListJobSource.total_count() -> int` —— 任务总数  
- `ListJobSource.reset() -> None` —— 重置游标  

**Example**：

```python
from core.infra.worker import ListJobSource

job_source = ListJobSource(jobs=list(range(100)))
batch = job_source.get_batch(10)
```

---

## 内存监控与调度

### MemoryMonitor（内存监控器）

**描述**：监控当前进程 RSS 内存使用情况，估算每个任务的内存占用，并提供简要告警信息。

**函数签名**：`MemoryMonitor(memory_budget_mb: float, baseline_rss_mb: Optional[float] = None)`

**常用方法**：

- `MemoryMonitor.update(... ) -> None` —— 更新监控状态（通常由调度器调用）  
- `MemoryMonitor.get_stats() -> Dict[str, Any]` —— 获取当前内存统计  
- `MemoryMonitor.get_warnings() -> List[str]` —— 获取告警列表  
- `MemoryMonitor.export_snapshot() -> Dict[str, Any]` —— 导出监控快照  

**Example**：

```python
from core.infra.worker import MemoryMonitor

monitor = MemoryMonitor(memory_budget_mb=4096.0)
stats = monitor.get_stats()
warnings = monitor.get_warnings()
```

---

### MemoryAwareScheduler（内存感知调度器）

**描述**：基于内存监控数据动态调整 batch 大小的调度器，可与 `Orchestrator` 一起使用，实现「既尽量用满资源，又避免 OOM」的执行策略。

**函数签名**：`MemoryAwareScheduler(jobs: List[Any], memory_budget_mb: float | str | None = "auto", warmup_batch_size: int | str = "auto", min_batch_size: int | str = "auto", max_batch_size: int | str = "auto", smooth_factor: float = 0.3, summary_weight: float = 0.2, monitor_interval: int = 5, log: Optional[logging.Logger] = None)`

**常用方法**：

- `iter_batches() -> Iterable[List[Any]]` —— 迭代批次任务（与 `Orchestrator` 配合）  
- `get_next_batch_size() -> int` —— 获取下一个批次大小  
- `update_after_batch(batch_size: int, batch_results: List[Any], finished_jobs: int) -> None` —— 在批次执行后更新状态  
- `get_progress() -> Dict[str, Any]` —— 获取进度信息（总任务数、已完成数、百分比等）  
- `get_memory_warning() -> Optional[str]` —— 获取当前内存告警（如有）  

**Example**（与 Orchestrator 一起使用）：

```python
from core.infra.worker import (
    Orchestrator,
    ProcessExecutor,
    ListJobSource,
    MemoryAwareScheduler,
)

jobs = [{"id": str(i), "data": i} for i in range(10000)]
job_source = ListJobSource(jobs)
scheduler = MemoryAwareScheduler(jobs)
executor = ProcessExecutor(job_executor=lambda x: x * 2)

orchestrator = Orchestrator(
    executor=executor,
    job_source=job_source,
    scheduler=scheduler,
)

result = orchestrator.run()
```

---

## Orchestrator（编排器）

### Orchestrator（构造函数）

**描述**：组合执行器、任务源、调度器、监控器、聚合器、错误处理器等组件，对外提供统一的高级执行 API。

**函数签名**：`Orchestrator(executor: Executor, job_source: JobSource, scheduler: Optional[Scheduler] = None, monitor: Optional[Monitor] = None, aggregator: Optional[Aggregator] = None, error_handler: Optional[ErrorHandler] = None)`

**参数（摘选）**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `executor` | `Executor` | 实际执行任务的执行器（如 `ProcessExecutor`） |
| `job_source` | `JobSource` | 任务源（如 `ListJobSource`） |
| `scheduler` | `Scheduler \| None` | 可选调度器（如 `MemoryAwareScheduler`） |
| `monitor` | `Monitor \| None` | 可选监控器（如 `MemoryMonitor`） |
| `aggregator` | `Aggregator \| None` | 结果聚合器 |
| `error_handler` | `ErrorHandler \| None` | 错误处理器 |

---

### Orchestrator.run

**描述**：执行所有任务，并返回包含原始结果列表和聚合摘要的字典。

**函数签名**：`Orchestrator.run() -> Dict[str, Any]`

**输出**：

```text
{
  "results": List[JobResult],  # 每个任务的执行结果
  "summary": Dict[str, Any],   # 聚合信息和监控统计
}
```

---

### Orchestrator.shutdown

**描述**：关闭执行器等组件，释放资源。通常在长时间运行的服务停止前调用；脚本模式下可省略。

**函数签名**：`Orchestrator.shutdown() -> None`

---

## 相关文档

- [Worker 概览](./overview.md)  
- [Worker 架构](./architecture.md)  
- [Worker 设计决策](./decisions.md)  

