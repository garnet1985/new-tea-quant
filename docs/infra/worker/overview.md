# Worker 模块概览

> **提示**：本文档提供 Worker 模块的快速上手视图。  
> 详细的设计理念、架构设计和决策记录请参考同目录下的 `architecture.md` 和 `decisions.md`。

## 📋 模块简介

Worker 模块位于 **Infra 层**，是系统的通用「任务并发执行器」，为上层模块提供统一的多进程 / 多线程执行能力。

**核心特性**：

- **统一并发模型**：上层只需要提供 jobs，具体用多进程还是多线程由 Worker 负责
- **任务类型驱动**：通过 `TaskType`（CPU/IO/Mixed）指导执行策略和并发度
- **内存感知调度**：内存监控 + 动态 batch 调整，尽量用满资源又避免 OOM
- **模块化架构**：Executor / JobSource / Monitor / Scheduler / Aggregator / ErrorHandler 可插拔

**与其他 Infra 模块的关系**：

- 与 `db`：`db` 负责连接和 SQL 执行，Worker 负责并发调度「要执行哪些任务」
- 与 `project_context`：Worker 通过配置系统获取并发相关参数（如模块任务配置）
- 与 `config`：并发策略（如 Worker 数量、预留核心数）可通过配置进行统一管理

---

## 📁 模块的目录结构

```text
core/infra/worker/
├── multi_process/              # 多进程执行器（传统接口）
│   ├── process_worker.py       # ProcessWorker 核心实现
│   ├── task_type.py            # 任务类型定义（CPU_INTENSIVE / IO_INTENSIVE / MIXED）
│   ├── example.py              # 使用示例
│   └── README.md               # 多进程模块说明
├── multi_thread/               # 多线程执行器（传统接口）
│   ├── futures_worker.py       # MultiThreadWorker 核心实现
│   ├── example.py              # 使用示例
│   └── README.md               # 多线程模块说明
├── executors/                  # Executor：真正执行 batch 的组件
├── queues/                     # JobSource：任务源
├── monitors/                   # Monitor：监控器（如内存监控）
├── schedulers/                 # Scheduler：调度器（如 MemoryAwareScheduler）
├── aggregators/                # Aggregator：结果聚合
├── error_handlers/             # ErrorHandler：错误处理
├── orchestrator.py             # Orchestrator：组合上述组件的编排器
├── memory_aware_scheduler.py   # 旧版内存感知调度器（向后兼容）
├── README.md                   # Worker 使用说明
└── DESIGN.md                   # Worker 设计文档（本架构文档源材料）
```

---

## 🚀 模块的使用方式（概览）

### 1. 传统 Worker（简单易用）

```python
from core.infra.worker import ProcessWorker, ProcessExecutionMode

worker = ProcessWorker(
    max_workers=None,  # 自动根据 CPU 核数和 TaskType 推导
    execution_mode=ProcessExecutionMode.QUEUE,
    job_executor=my_cpu_task,
    is_verbose=True,
)

stats = worker.run_jobs(jobs)
worker.print_stats()
```

```python
from core.infra.worker import MultiThreadWorker, ThreadExecutionMode

worker = MultiThreadWorker(
    max_workers=20,
    execution_mode=ThreadExecutionMode.PARALLEL,
    job_executor=my_io_task,
    is_verbose=True,
)

stats = worker.run_jobs(jobs)
```

### 2. 模块化 Orchestrator（高级用法）

适合需要自定义监控 / 调度 / 聚合的场景：

```python
from core.infra.worker import (
    Orchestrator,
    ProcessExecutor,
    ListJobSource,
    MemoryMonitor,
    MemoryAwareScheduler,
    SimpleAggregator,
    SimpleErrorHandler,
)

orchestrator = Orchestrator(
    executor=ProcessExecutor(max_workers=4),
    job_source=ListJobSource(jobs),
    monitor=MemoryMonitor(),
    scheduler=MemoryAwareScheduler(),
    aggregator=SimpleAggregator(),
    error_handler=SimpleErrorHandler(),
)

result = orchestrator.run()
```

---

## 📚 模块详细文档

- **[architecture.md](./architecture.md)**：架构文档，包含详细的技术设计、核心组件、运行时 Workflow
- **[decisions.md](./decisions.md)**：重要决策记录，包含设计决策和取舍

> **阅读建议**：先阅读本文档快速了解「Worker 模块是什么、能做什么」，  
> 再阅读 `architecture.md` 理解内部架构，最后阅读 `decisions.md` 了解设计决策背景。

