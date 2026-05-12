# Worker（`infra.worker`）

为上层模块提供**多进程**（`ProcessWorker`）与**多线程**（`MultiThreadWorker`）任务执行能力，以及 **Executor / JobSource / Monitor / Scheduler / Aggregator / ErrorHandler + `Orchestrator`** 的可插拔组合。

## 适用场景

- CPU 密集：枚举、批量计算、多核并行（多进程）。
- I/O 密集：请求、文件、数据库访问（线程池）。
- 需要按内存动态调节 batch、或自定义任务源与错误策略时，使用模块化组件与 `Orchestrator`。

## 快速定位

```text
core/infra/worker/
├── module_info.yaml
├── multi_process/          # ProcessWorker、TaskType
├── multi_thread/           # MultiThreadWorker
├── executors/ queues/ monitors/ schedulers/ aggregators/ error_handlers/
├── orchestrator.py
├── memory_aware_scheduler.py
├── __test__/
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN.md
    ├── API.md
    └── DECISIONS.md
```

## 快速开始

```python
from core.infra.worker import (
    ProcessWorker,
    ProcessExecutionMode,
    ProgressReportConfig,
    ProgressReportMode,
)

worker = ProcessWorker(
    max_workers=None,
    execution_mode=ProcessExecutionMode.QUEUE,
    job_executor=my_fn,
    on_job_done=None,  # 可选：每个 job 完成后回调（成功/失败都触发）
    progress_report_config=ProgressReportConfig(
        mode=ProgressReportMode.EVERY_PROGRESS_INTERVAL,
        interval_pct=5,
    ),
    is_main_process_used_if_single_worker=True,  # 默认：max_workers=1 时走主进程
    is_verbose=True,
)
stats = worker.run_jobs(jobs)
worker.print_stats()
```

运行测试（仓库根目录）：

```bash
python3 -m pytest core/infra/worker/__test__/ -q
```

## 模块依赖

- `infra.project_context`：`ProcessWorker.resolve_max_workers('auto', …)` 通过 `ConfigManager.get_module_config` 读取任务类型与预留核数。

## 当前实现说明（代码对齐）

- `ProcessExecutionMode` / `ThreadExecutionMode` 等为各子模块 `ExecutionMode` 的**导出别名**（见 `__init__.py`）。
- `ProcessWorker` 在 `execution_mode=QUEUE` 且 `max_workers=1` 时默认使用主进程串行执行，不创建子进程。
- `ProcessWorker` 支持 `on_job_done` 回调，在每个 job 完成时回传当前进度快照（成功/失败都算完成）。
- `ProcessWorker` 支持 `ProgressReportConfig`：按 `every_job_done` / `every_sec_interval` / `every_progress_interval` 控制日志频率（或关闭）。
- `MemoryAwareBatchScheduler`（根目录 `memory_aware_scheduler.py`）为兼容旧用法保留；新代码优先 `schedulers.MemoryAwareScheduler` 与 `Orchestrator`。
- 包级 `__version__` 来自 `core.system.get_version()`。

## 相关文档

- `docs/ARCHITECTURE.md`
- `docs/DESIGN.md`
- `docs/API.md`
- `docs/DECISIONS.md`
- `multi_process/README.md`、`multi_thread/README.md`（子模块补充说明）
