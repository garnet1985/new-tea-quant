# Backtest Scheduler 模块（`modules.backtest_scheduler`）

## 模块定位

**业务调度层**，不属于infra层。

职责：
- 理解回测业务语义（时间线/切片模式）
- 队列填池策略（QUEUE/BATCH）
- on_result回调、JobContext封装
- Dispatch规划（entities_per_job、max_workers）
- 指挥Python标准库执行器工作

## 与infra的区别

- **Python标准库**：纯粹的执行器（ProcessPoolExecutor），不理解业务语义
- **modules.backtest_scheduler**：业务调度层，理解回测语义，编排任务

## 使用模块

- **modules.tag**：Tag回测（时间线/切片）
- **modules.strategy**：Strategy回测（枚举/价格因子）

## 迁移计划

从 `infra.job_pipeline` 和 `infra.worker` 迁移而来：

**Phase 1: 创建空壳模块** ← 当前
- 创建modules.backtest_scheduler目录
- 定义模块定位和职责

**Phase 2: 迁移dispatch规划**
- infra.worker.dispatch_planner → modules.backtest_scheduler.dispatch_planner
- infra.worker.dispatch_time_planner → modules.backtest_scheduler.dispatch_time_planner
- 修改tag/strategy导入路径

**Phase 3: 迁移类型定义**
- infra.worker.JobResult → modules.backtest_scheduler.types.JobResult
- infra.worker.JobStatus → modules.backtest_scheduler.types.JobStatus
- 修改tag/strategy导入路径

**Phase 4: 迁移job_pipeline核心**
- infra.job_pipeline核心逻辑 → modules.backtest_scheduler.scheduler
- 修改tag/strategy导入路径

**Phase 5: 废弃infra层**
- 删除infra.worker多进程部分
- 删除infra.job_pipeline（迁移完成）

## 未来扩展

支持MQ迁移：
- LocalScheduler（当前，ProcessPoolExecutor）
- MQScheduler（未来，RabbitMQ/Kafka）

## 目录结构（待实现）

```text
core/modules/backtest_scheduler/
├── module_info.yaml
├── README.md
├── __init__.py
├── scheduler.py              # 调度器核心（从job_pipeline迁移）
├── dispatch_planner.py       # Dispatch规划（从worker迁移）
├── dispatch_time_planner.py  # 时间规划（从worker迁移）
├── types.py                  # 类型定义（从worker迁移）
├── strategy/                 # 调度策略
│   ├── queue_strategy.py
│   └── batch_strategy.py
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN.md
    └── API.md
```

## 调度逻辑对比

| 特性 | backtest_scheduler | data_source_scheduler（未来） |
|------|-------------------|------------------------------|
| 执行顺序 | 时间线/切片 | 依赖拓扑排序 |
| 并行策略 | Queue/Batch | bundle并行 |
| 执行池 | ProcessPoolExecutor | ThreadPoolExecutor |
| 特殊逻辑 | Dispatch规划 | retry、依赖注入 |
| 使用模块 | tag/strategy | 仅data_source |

**设计原则**：
- 调度逻辑不同，不应该强行合并
- 各自专注自己的领域

## 相关文档

- [最终架构决策](../../docs/FINAL_ARCHITECTURE_DECISION.md)
- [正确架构重构方案](../../docs/CORRECT_ARCHITECTURE_REFACTOR.md)