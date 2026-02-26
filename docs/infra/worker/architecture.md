# Worker 架构文档

**版本：** 1.0  
**日期：** 2026-01-XX  
**状态：** 生产环境使用中

---

## 📋 目录

1. [设计背景](#设计背景)
2. [核心设计思想](#核心设计思想)
3. [整体架构](#整体架构)
4. [核心组件与职责](#核心组件与职责)
5. [运行时 Workflow](#运行时-workflow)
6. [使用模式](#使用模式)
7. [扩展与演进](#扩展与演进)
8. [重要决策记录 (Decisions)](#重要决策记录-decisions)

---

## 设计背景

### 问题背景

在引入 Worker 模块之前，项目中存在以下问题：

1. **并发模型分散**：
   - 各模块各自使用 `ThreadPoolExecutor` / `ProcessPoolExecutor` / `multiprocessing`
   - 难以统一监控、调试和优化
2. **CPU vs IO 选择不清晰**：
   - 有的 CPU 密集任务用线程，有的 IO 密集任务用进程
   - 容易出现性能不佳甚至资源浪费
3. **内存不可控**：
   - 没有统一的 batch 和内存控制策略，大量任务并发时容易 OOM
4. **缺乏模块化**：
   - 监控、调度、错误处理、聚合逻辑分散在业务代码中，难以重用

### 设计目标

1. **统一并发基础设施**：所有并发执行都通过 Worker 模块完成
2. **任务类型驱动**：根据任务是 CPU 密集还是 IO 密集，选择合适执行方式
3. **内存感知**：提供内存感知调度，避免 OOM，同时尽量用满资源
4. **模块化架构**：监控 / 调度 / 聚合 / 错误处理等通过可插拔组件实现
5. **易用优先**：提供简单易用的传统 Worker 接口，并逐步引导向模块化 Orchestrator

---

## 核心设计思想

### 1. 传统 Worker vs 模块化 Orchestrator

- **传统 Worker（ProcessWorker / MultiThreadWorker）**：
  - 面向业务开发者，提供简单的「给我 jobs，我帮你并发执行」接口
  - 内部封装 executor / queue / stats 等细节

- **模块化 Orchestrator**：
  - 面向高级用例和 infra 开发者
  - 将执行器、任务源、监控、调度、聚合、错误处理解耦为独立组件
  - 支持灵活组合和单元测试

### 2. 任务类型驱动的执行策略

通过 `TaskType` 明确标注任务特性：

- `CPU_INTENSIVE`：大量纯计算，建议多进程
- `IO_INTENSIVE`：大量网络 / 磁盘 IO，建议多线程
- `MIXED`：混合场景，策略折中

Worker 内部根据 `TaskType` 和 CPU 核数推导合理的 `max_workers`：

- CPU 密集：接近物理核心数
- IO 密集：可高于核心数

### 3. 内存感知调度

- 使用 `MemoryMonitor` 监控当前进程内存占用
- `MemoryAwareScheduler` 根据内存水位调整每次取出的 batch size：
  - 内存充裕 → 增大 batch，提升吞吐
  - 内存逼近阈值 → 减小 batch，避免 OOM

### 4. 可回退、可观测

- 提供 stats / 日志输出来观测：
  - job 数量、失败率、执行时间分布
  - 内存使用趋势
- 设计上允许部分组件用简化实现（如无监控 / 固定 batch），方便在资源紧张环境中降级运行

---

## 整体架构

### 目录视角

```text
core/infra/worker/
├── multi_process/              # 传统多进程 Worker
├── multi_thread/               # 传统多线程 Worker
├── executors/                  # 执行器（Executor）
├── queues/                     # 任务源（JobSource）
├── monitors/                   # 监控器（Monitor）
├── schedulers/                 # 调度器（Scheduler）
├── aggregators/                # 聚合器（Aggregator）
├── error_handlers/             # 错误处理器（ErrorHandler）
└── orchestrator.py             # Orchestrator：编排器
```

### 组件关系图

```text
                      ┌──────────────────────┐
                      │      业务代码         │
                      └─────────┬────────────┘
                                │
                         Orchestrator
                                │
        ┌───────────────────────┼────────────────────────┐
        ▼                       ▼                        ▼
   JobSource                Scheduler                 Executor
 (queues.*)             (schedulers.*)           (executors.*)
        │                       ▲                        │
        │                       │                        │
        ▼                       │                        ▼
     Jobs batch           Monitor (monitors.*)      JobResults
                                │                        │
                                ▼                        ▼
                          Aggregator               ErrorHandler
                         (aggregators.*)        (error_handlers.*)
```

---

## 核心组件与职责

### 1. Executor（执行器）

- **职责**：决定「一批 jobs 如何并发执行」
- **主要实现**：
  - `ProcessExecutor`：使用多进程池执行，适合 CPU 密集
  - `FuturesExecutor`（MultiThreadExecutor）：使用线程池执行，适合 IO 密集
- **关键接口**：
  - `run_jobs(jobs: List[Job]) -> List[JobResult]`

### 2. JobSource / Queue（任务源）

- **职责**：统一任务来源与分批策略
- **实现**：
  - `ListJobSource`：从内存中的 list 拉取任务
- **关键接口**：
  - `get_batch(size: int) -> List[Job]`
  - `has_more() -> bool`

### 3. Monitor（监控器）

- **职责**：观测执行过程中的关键指标
- **实现**：
  - `MemoryMonitor`：监控当前进程内存占用，输出统计与告警
- **关键接口**：
  - `get_stats() -> Dict[str, Any]`
  - `get_warnings() -> List[str]`

### 4. Scheduler（调度器）

- **职责**：根据监控与策略动态决定 batch 大小等参数
- **实现**：
  - `MemoryAwareScheduler`：根据最大内存阈值、当前使用量等调整下一批任务大小
- **关键接口**：
  - `get_next_batch_size() -> int`
  - `update_after_batch(batch_stats: Dict[str, Any]) -> None`

### 5. Aggregator（聚合器）

- **职责**：从单个 JobResult 聚合出全局统计 / 汇总结果
- **实现**：
  - `SimpleAggregator`：汇总成功 / 失败数量、耗时统计等
- **关键接口**：
  - `add_result(result: JobResult) -> None`
  - `get_summary() -> Dict[str, Any]`

### 6. ErrorHandler（错误处理器）

- **职责**：统一处理 job 级别的异常
- **实现**：
  - `SimpleErrorHandler`：记录错误、决定是否跳过 / 重试等
- **关键接口**：
  - `handle_error(job: Job, error: Exception) -> ErrorAction`

### 7. Orchestrator（编排器）

- **职责**：组合以上所有组件，对外提供高级 `run()` 接口

**典型使用**：

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

## 运行时 Workflow

### 1. 传统 Worker（ProcessWorker / MultiThreadWorker）

```text
业务代码
  ↓
ProcessWorker / MultiThreadWorker
  ↓
内部封装：线程池 / 进程池 + stats 收集
  ↓
返回执行统计（成功数 / 失败数 / 耗时等）
```

- 适合直接「给我一批 jobs，我帮你并发跑」的简单场景
- 内存控制相对简单（固定 batch / 固定并发数）

### 2. 模块化 Orchestrator

```text
1. 初始化所有组件（Executor / JobSource / Monitor / Scheduler / Aggregator / ErrorHandler）
2. Orchestrator 主循环：
   a. 向 Scheduler 请求下一批 batch 大小
   b. 从 JobSource 拉取对应数量的 jobs
   c. 调用 Executor.run_jobs 同时执行这一批 jobs
   d. Monitor 记录本批执行的资源使用情况
   e. Aggregator 累积每个 JobResult
   f. ErrorHandler 处理执行中的异常
   g. Scheduler 根据本批 stats 更新内部状态
3. JobSource 无任务后结束循环，返回 Aggregator 汇总结果
```

---

## 使用模式

### 模式一：直接使用传统 Worker

适合大多数简单批处理场景：

```python
from core.infra.worker import ProcessWorker, ProcessExecutionMode

worker = ProcessWorker(
    max_workers=None,
    execution_mode=ProcessExecutionMode.QUEUE,
    job_executor=my_cpu_task,
    is_verbose=True,
)

stats = worker.run_jobs(jobs)
worker.print_stats()
```

### 模式二：使用 Orchestrator 组合组件

适合需要：

- 精细控制 batch 策略
- 自定义监控 / 聚合 / 错误处理
- 统一封装为基础设施服务

参考前文 Orchestrator 示例代码。

---

## 扩展与演进

短期内的扩展方向：

- 新增更多 Monitor（CPU / 网络 / 自定义指标）
- 新增更多 Scheduler 策略（优先级调度、负载均衡等）
- 抽象 Job / JobResult 类型，方便与策略 / 数据源等模块对接

长期规划：

- 异步执行器（基于 asyncio）
- 分布式执行器（跨多台机器）

---

## 重要决策记录 (Decisions)

Worker 模块的关键设计决策详见：`architecture/infra/worker/decisions.md`，包括：

1. 为什么同时保留多进程和多线程两种执行方式
2. 为什么引入模块化 Orchestrator，而不是在单个 Worker 里堆所有功能
3. 为什么采用内存感知调度，而不是简单的「固定并发数 + 固定 batch」

