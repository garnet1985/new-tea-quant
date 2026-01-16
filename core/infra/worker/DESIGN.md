# Worker 模块设计文档

## 📋 概述

Worker 模块是项目的通用任务执行器，提供多进程和多线程两种执行方式，支持模块化架构，可以根据任务特性选择最适合的执行策略。

## 🎯 设计目标

1. **多执行方式支持**：支持多进程（CPU密集型）和多线程（IO密集型）
2. **模块化架构**：可插拔的组件设计，易于扩展
3. **内存感知调度**：根据内存使用情况动态调整 batch size
4. **资源管理**：完善的资源管理和错误处理
5. **易于使用**：简洁的 API，自动化的配置

## 🏗️ 架构设计

### 核心组件

#### 1. Executor（执行器）

**职责**：负责"如何并发执行一批 jobs"

**实现**：
- `ProcessExecutor` - 多进程执行器（CPU密集型）
- `MultiThreadExecutor` - 多线程执行器（IO密集型）

**接口**：`run_jobs(jobs: List[Job]) -> List[JobResult]`

#### 2. Queue / JobSource（任务源）

**职责**：负责 job 的产生与顺序

**实现**：
- `ListJobSource` - 简单列表任务源

**接口**：`get_batch(size: int) -> List[Job]`, `has_more() -> bool`

#### 3. Monitor（监控器）

**职责**：观测指标，提供可观测性

**实现**：
- `MemoryMonitor` - 内存监控器

**接口**：`get_stats() -> Dict`, `get_warnings() -> List[str]`

#### 4. Scheduler（调度器）

**职责**：基于监控数据和配置策略，动态调整参数

**实现**：
- `MemoryAwareScheduler` - 内存感知调度器

**接口**：`get_next_batch_size() -> int`, `update_after_batch(...) -> None`

#### 5. Aggregator（聚合器）

**职责**：将单个 JobResult 聚合成全局视图

**实现**：
- `SimpleAggregator` - 简单聚合器

**接口**：`add_result(result: JobResult) -> None`, `get_summary() -> Dict`

#### 6. ErrorHandler（错误处理器）

**职责**：统一处理 job 级别的异常

**实现**：
- `SimpleErrorHandler` - 简单错误处理器

**接口**：`handle_error(job: Job, error: Exception) -> ErrorAction`

#### 7. Orchestrator（编排器）

**职责**：组合所有组件，提供统一的高级 API

**接口**：`run(jobs: List[Job]) -> Dict[str, Any]`

### 向后兼容的 Worker

为了保持向后兼容，模块还提供了传统的 Worker 接口：

- **ProcessWorker** - 多进程执行器（CPU密集型）
- **MultiThreadWorker** - 多线程执行器（IO密集型，原 FuturesWorker）

## 🔄 数据流

### 传统 Worker 流程

```
业务代码
  ↓
ProcessWorker / MultiThreadWorker
  ↓
执行任务（多进程/多线程）
  ↓
返回结果
```

### 模块化架构流程

```
业务代码
  ↓
Orchestrator
  ↓
JobSource (获取任务)
  ↓
Scheduler (决定 batch size)
  ↓
Executor (执行任务)
  ↓
Monitor (监控资源)
  ↓
Aggregator (聚合结果)
  ↓
ErrorHandler (处理错误)
  ↓
返回结果
```

## 🎨 设计模式

### 1. 策略模式（Strategy Pattern）

**目的**：根据任务类型选择不同的执行策略

**实现**：
- `ProcessExecutor` vs `MultiThreadExecutor`
- `QUEUE` vs `BATCH` 执行模式

### 2. 观察者模式（Observer Pattern）

**目的**：监控执行状态和资源使用

**实现**：`Monitor` 组件监控内存、CPU 等指标

### 3. 适配器模式（Adapter Pattern）

**目的**：统一不同执行器的接口

**实现**：`Executor` 基类定义统一接口，各执行器实现具体逻辑

### 4. 组合模式（Composite Pattern）

**目的**：组合多个组件提供高级功能

**实现**：`Orchestrator` 组合所有组件

## ⚡ 性能优化

### 1. 内存感知调度

`MemoryAwareScheduler` 根据进程内存使用情况动态调整 batch size：
- 内存使用高 → 减小 batch size
- 内存使用低 → 增大 batch size

### 2. 自动 Worker 数量计算

`ProcessWorker.resolve_max_workers()` 根据任务类型和 CPU 核心数自动选择最佳并行数：
- CPU 密集型：物理核心数 - 预留
- IO 密集型：逻辑核心数 - 预留 + 1
- 混合型：逻辑核心数 - 预留

### 3. 资源管理

- 进程/线程池管理
- 数据库连接池
- 内存监控和限制

## 🔐 安全性设计

### 1. 资源限制

- 最大 worker 数量限制（防止过度并行）
- 内存使用监控（防止 OOM）
- 任务超时控制

### 2. 错误处理

- 完善的异常捕获
- 错误重试机制
- 失败任务记录

### 3. 进程/线程安全

- 线程锁保护共享资源
- 进程间数据序列化
- 信号处理（优雅退出）

## 📦 模块职责划分

### core/infra/worker（基础设施层）

- `ProcessWorker` / `MultiThreadWorker` - 传统 Worker 接口
- `executors/` - 执行器模块
- `queues/` - 任务源模块
- `monitors/` - 监控器模块
- `schedulers/` - 调度器模块
- `aggregators/` - 聚合器模块
- `error_handlers/` - 错误处理器模块
- `orchestrator.py` - 编排器

### 使用场景

- **策略枚举**：使用 `ProcessWorker` 并行枚举多只股票
- **数据获取**：使用 `MultiThreadWorker` 并行获取 API 数据
- **内存敏感场景**：使用 `MemoryAwareScheduler` 控制内存使用

## 🔮 未来扩展

### 1. 更多执行器

- 异步执行器（asyncio）
- 分布式执行器（多机）

### 2. 更多监控器

- CPU 监控器
- 网络监控器
- 性能监控器

### 3. 更多调度策略

- 优先级调度
- 负载均衡调度
- 成本感知调度

## 📝 设计决策记录

### 为什么支持两种执行方式？

**决策**：同时支持多进程和多线程

**原因**：
1. CPU 密集型任务需要多进程绕过 GIL
2. IO 密集型任务使用多线程更高效
3. 不同场景需要不同的执行策略

### 为什么采用模块化架构？

**决策**：将 Worker 拆分为多个可插拔组件

**原因**：
1. 职责清晰：每个组件只负责一个功能
2. 易于扩展：可以独立扩展某个组件
3. 易于测试：每个组件可以独立测试
4. 灵活组合：可以根据需求组合不同组件

### 为什么保留传统 Worker 接口？

**决策**：保留 `ProcessWorker` 和 `MultiThreadWorker`

**原因**：
1. 向后兼容：现有代码可以继续使用
2. 简单场景：对于简单场景，传统接口更易用
3. 渐进迁移：可以逐步迁移到模块化架构
