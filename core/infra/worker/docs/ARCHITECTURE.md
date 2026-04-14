# Worker 架构文档

**版本：** `0.2.0`

---

## 模块介绍

`infra.worker` 提供 NTQ 的通用并发执行能力：传统 **ProcessWorker** / **MultiThreadWorker** 直接跑任务队列，以及 **Orchestrator** 串联执行器、任务源、监控、调度、聚合与错误处理。

---

## 模块目标

- 为 CPU 密集与 I/O 密集任务分别提供合适的并行模型（进程 vs 线程）。
- 通过 `TaskType` 与配置驱动 `resolve_max_workers`，减少手写并发数。
- 支持内存感知批调度与可插拔组件，便于扩展与单测。

---

## 模块职责与边界

**职责（In scope）**

- 多进程/多线程任务提交、执行、统计与基础信号清理。
- 模块化流水线：`Executor` 执行 batch，`JobSource` 提供任务，`Scheduler`/`Monitor` 调节批次，`Aggregator` 汇总。
- 与 `project_context` 配置集成（模块级 Worker 参数）。

**边界（Out of scope）**

- 不实现业务任务逻辑（job 内容由调用方提供）。
- 不负责持久化任务队列或分布式调度。
- 不替代操作系统级进程/容器编排。

---

## 依赖说明

- `infra.project_context`：自动解析 `max_workers='auto'` 时使用 `ConfigManager.get_module_config`。
- 可选：`psutil`（内存监控与旧版 `MemoryAwareBatchScheduler` 等路径）。

---

## 工作拆分

- `multi_process/process_worker.py`：`ProcessWorker`、`ExecutionMode`/`JobStatus`/`JobResult`（导出为 `ProcessExecutionMode` 等）。
- `multi_process/task_type.py`：`TaskType`（CPU/IO/Mixed）。
- `multi_thread/futures_worker.py`：`MultiThreadWorker` 与线程侧 `ExecutionMode`/`JobStatus`/`JobResult`。
- `executors/`、`queues/`、`monitors/`、`schedulers/`、`aggregators/`、`error_handlers/`：可插拔协议与默认实现。
- `orchestrator.py`：组装组件并 `run()`。
- `memory_aware_scheduler.py`：旧版内存感知批调度（兼容）；新实现见 `schedulers/`。

---

## 架构/流程图

```text
传统: 调用方 -> ProcessWorker / MultiThreadWorker -> run_jobs -> 统计

组件化: JobSource -> Scheduler(可选) -> Executor -> JobResult*
        -> Aggregator / Monitor / ErrorHandler（可选）
        Orchestrator.run() 驱动上述循环
```

---

## 相关文档

- [详细设计](./DESIGN.md)
- [API](./API.md)、[决策记录](./DECISIONS.md)
