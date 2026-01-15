# Worker 模块化架构设计

## 目录结构

```
worker/
├── __init__.py                    # 统一导出接口
├── README.md                      # 总体说明
│
├── executors/                     # 执行器模块
│   ├── __init__.py
│   ├── base.py                    # Executor 基类/接口
│   ├── futures_executor.py        # 多线程执行器（原 FuturesWorker, 现 MultiThreadExecutor）
│   └── process_executor.py        # 多进程执行器（原 ProcessWorker）
│
├── queues/                        # 队列/任务源模块
│   ├── __init__.py
│   ├── base.py                    # JobSource 基类/接口
│   ├── list_source.py             # 简单列表任务源
│   └── generator_source.py        # 惰性生成任务源（未来）
│
├── monitors/                      # 监控器模块
│   ├── __init__.py
│   ├── base.py                    # Monitor 基类/接口
│   ├── memory_monitor.py          # 内存监控器
│   └── performance_monitor.py     # 性能监控器（未来）
│
├── schedulers/                    # 调度器/控制器模块
│   ├── __init__.py
│   ├── base.py                    # Scheduler 基类/接口
│   └── memory_aware_scheduler.py  # 内存感知调度器（从 memory_aware_scheduler.py 拆分）
│
├── aggregators/                   # 聚合器模块
│   ├── __init__.py
│   ├── base.py                    # Aggregator 基类/接口
│   └── simple_aggregator.py       # 简单聚合器
│
├── error_handlers/                # 错误处理器模块
│   ├── __init__.py
│   ├── base.py                    # ErrorHandler 基类/接口
│   └── simple_error_handler.py    # 简单错误处理器
│
└── orchestrator.py                # 编排器（组合所有组件）
```

## 组件职责

### 1. Executor（执行器）
- **职责**：负责"如何并发执行一批 jobs"
- **接口**：`run_jobs(jobs: List[Job]) -> List[JobResult]`
- **实现**：
  - `FuturesExecutor`（多线程）
  - `ProcessExecutor`（多进程）

### 2. Queue / JobSource（任务源）
- **职责**：负责 job 的产生与顺序
- **接口**：`get_batch(size: int) -> List[Job]`, `has_more() -> bool`
- **实现**：
  - `ListJobSource`（简单列表）
  - `GeneratorJobSource`（惰性生成，未来）

### 3. Monitor（监控器）
- **职责**：观测指标，提供可观测性
- **接口**：`get_stats() -> Dict`, `get_warnings() -> List[str]`
- **实现**：
  - `MemoryMonitor`（内存监控）
  - `PerformanceMonitor`（性能监控，未来）

### 4. Scheduler（调度器）
- **职责**：基于监控数据和配置策略，动态调整参数
- **接口**：`get_next_batch_size() -> int`, `update_after_batch(...) -> None`
- **实现**：
  - `MemoryAwareScheduler`（内存感知调度）

### 5. Aggregator（聚合器）
- **职责**：将单个 JobResult 聚合成全局视图
- **接口**：`add_result(result: JobResult) -> None`, `get_summary() -> Dict`
- **实现**：
  - `SimpleAggregator`（简单聚合）

### 6. ErrorHandler（错误处理器）
- **职责**：统一处理 job 级别的异常
- **接口**：`handle_error(job: Job, error: Exception) -> ErrorAction`
- **实现**：
  - `SimpleErrorHandler`（简单错误处理）

### 7. Orchestrator（编排器）
- **职责**：组合所有组件，提供统一的高级 API
- **接口**：`run(jobs: List[Job]) -> Dict[str, Any]`

## 迁移计划

### Phase 1: 创建基础接口和目录结构
1. 创建所有目录和 `__init__.py`
2. 定义基类/接口（`base.py` 文件）

### Phase 2: 拆分现有代码
1. `FuturesWorker` -> `MultiThreadWorker`（类名）
2. `FuturesExecutor` -> `MultiThreadExecutor`（执行器）
2. `ProcessWorker` -> `executors/process_executor.py`
3. `MemoryAwareBatchScheduler` 拆分：
   - Monitor 部分 -> `monitors/memory_monitor.py`
   - Scheduler 部分 -> `schedulers/memory_aware_scheduler.py`

### Phase 3: 实现新组件
1. `queues/list_source.py` - 简单列表任务源
2. `aggregators/simple_aggregator.py` - 简单聚合器
3. `error_handlers/simple_error_handler.py` - 简单错误处理器

### Phase 4: 创建编排器
1. `orchestrator.py` - 组合所有组件的高级 API

### Phase 5: 更新调用方
1. 更新 `OpportunityEnumerator` 使用新的模块化 API
2. 更新 `__init__.py` 导出

## 向后兼容

由于用户说"不用向前兼容"，我们可以直接重构，但建议：
- 在 `__init__.py` 中保留旧的导入路径（标记为 deprecated）
- 提供迁移指南
