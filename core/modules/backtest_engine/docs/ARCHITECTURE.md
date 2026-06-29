# Backtest Scheduler 架构文档

**版本：** `0.1.0`

---

## 模块介绍

`modules.backtest_scheduler` 是 NTQ 的回测业务调度模块，理解回测语义（时间线/切片模式），为tag和strategy模块提供统一的调度能力。

---

## 模块目标

- 为回测任务提供合适的调度策略（QUEUE/BATCH）
- 理解回测业务语义（时间线/切片、枚举/价格因子）
- 提供Dispatch规划功能（entities_per_job、max_workers优化）
- 与Python标准库执行器配合（ProcessPoolExecutor）

---

## 模块职责与边界

**职责（In scope）**

- 回测业务调度（时间线/切片模式）
- 队列填池策略（QUEUE/BATCH）
- on_result回调、JobContext封装
- Dispatch规划（基于内存/时间约束优化并发）
- 为tag/strategy提供统一调度接口

**边界（Out of scope）**

- 不实现底层执行器（使用Python标准库ProcessPoolExecutor）
- 不负责数据源调度（data_source有独立的scheduler）
- 不替代MQ分布式调度（未来可迁移）

---

## 依赖说明

- Python标准库：`concurrent.futures`（ProcessPoolExecutor）
- `infra.project_context`：获取配置（worker.json）
- 不依赖已废弃的`infra.worker`（多进程部分）

---

## 工作拆分

- `core/scheduler.py`：调度器核心（从job_pipeline迁移）
- `core/dispatch_planner.py`：Dispatch规划（从worker迁移）
- `core/dispatch_time_planner.py`：时间规划（从worker迁移）
- `core/types.py`：类型定义（JobResult、JobStatus等）

---

## 架构/流程图

```text
业务层（tag/strategy）
    ↓ 调用
BacktestScheduler（业务调度层）
    ├─ 理解回测语义（时间线/切片）
    ├─ 队列填池策略（QUEUE/BATCH）
    ├─ Dispatch规划（优化并发）
    ↓ 调用
Python标准库ProcessPoolExecutor
```

---

## 调度逻辑说明

### QUEUE模式（默认）

- 低延迟流水线
- 动态填池（max_workers + prefetch_ahead）
- 完成即补

### BATCH模式

- 控峰值内存
- 批间串行执行
- checkpoint友好

### Dispatch规划

- 基于内存约束：`resolve_dispatch_plan`（entities_per_job、memory_budget_mb）
- 基于时间约束：`resolve_time_dispatch_plan`（sec_per_entity、sec_per_job_overhead）
- 自动优化并发度和批次大小

---

## 与其他模块的关系

### 使用模块

- **modules.tag**：Tag回测（时间线/切片）
- **modules.strategy**：Strategy回测（枚举/价格因子）

### 与infra的区别

- **infra层**：纯执行（ProcessPoolExecutor），不理解业务语义
- **modules层**：业务调度，理解回测语义

### 与data_source的区别

- **backtest_scheduler**：时间线/切片、进程池
- **data_source scheduler**：依赖拓扑、线程池（独立实现）

---

## 未来扩展

### MQ迁移路径

```python
# 当前
scheduler = LocalScheduler()

# 未来
scheduler = MQScheduler(broker_url='amqp://localhost')
```

业务代码改2行即可。

---

## 相关文档

- [详细设计](./DESIGN.md)
- [API文档](./API.md)
- [设计决策](./DECISIONS.md)