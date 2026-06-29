# 正确架构重构方案

**核心原则**：职责归属决定位置，不是稳定优先

---

## 问题诊断

### 1. Worker模块的意义问题

**当前状态**：
- ProcessWorker.run_jobs已废弃（多进程执行移到JobPipeline）
- MultiThreadWorker没人用（DataSource直接用JobPipeline线程池）
- 只剩下：Dispatch规划函数、类型定义

**问题**：
- 如果多进程功能已废弃，Worker模块的意义在哪？
- Dispatch规划函数理解回测语义，不属于infra层
- Worker模块应该完全重新定位

### 2. JobPipeline定位问题

**当前状态**：
- 在infra层，但包含业务调度逻辑
- DataSource用JobPipeline（THREAD）
- Strategy/Tag用JobPipeline（PROCESS）

**问题**：
- JobPipeline理解业务语义（QUEUE/BATCH策略）
- 不属于infra层，应该在modules层
- 应该重命名为scheduler（因为不止回测用）

### 3. DataSource多线程问题

**当前状态**：
- 用JobPipeline（THREAD）进行bundle调度
- async_bridge用ThreadPoolExecutor(max_workers=1)

**问题**：
- 如果多进程可以直接用Python的，多线程为什么不能？
- 如果将来data_source需要并行，需要scheduler吗？

---

## 正确架构方案

### 方案1: Worker模块完全废弃（激进）

**理由**：
- 多进程执行功能已废弃
- 多线程执行没人用
- Dispatch规划函数应该在scheduler模块

**迁移计划**：
```
infra.worker（废弃）
├─ dispatch_planner.py → modules.scheduler.dispatch_planner.py
├─ dispatch_time_planner.py → modules.scheduler.dispatch_time_planner.py
├─ process_worker.py
│  ├─ JobResult → modules.scheduler.types.py
│  ├─ JobStatus → modules.scheduler.types.py
│  └─ ProcessWorker → 完全删除
└─ Worker Facade → 删除
```

**优点**：
- 架构清晰
-职责明确

**缺点**：
- 需要修改所有导入路径（strategy/tag/data_source）
- 需要大量测试验证

---

### 方案2: Worker模块极简保留（保守）

**理由**：
- 保留极少的通用基础设施
- 不包含业务逻辑

**保留内容**：
```
infra.worker（极简版）
├─ types.py
│  ├─ JobResult（通用类型）
│  ├─ JobStatus（通用类型）
└─ （不包含Dispatch规划、不包含执行器）
```

**迁移内容**：
```
modules.scheduler
├─ dispatch_planner.py（从worker迁移）
├─ dispatch_time_planner.py（从worker迁移）
└─ scheduler.py（从job_pipeline迁移）
```

**优点**：
- 类型定义确实是通用的（不理解业务语义）
- 迁移风险较小

**缺点**：
- Worker模块意义仍然有限（只剩类型定义）

---

### 方案3: 统一Scheduler模块（推荐）

**理由**：
- JobPipeline本质是业务调度器
- DataSource也用它（不止回测用）
- 应该在modules层，叫scheduler

**架构**：
```
modules.scheduler（统一调度模块）
├─ scheduler.py（JobPipeline核心）
├─ dispatch_planner.py（Dispatch规划）
├─ dispatch_time_planner.py（时间规划）
├─ types.py（JobResult/JobStatus）
└─ strategy/
    ├─ queue_strategy.py
    └─ batch_strategy.py
```

**定位**：
- 业务调度层（不属于infra）
- 理解业务语义（QUEUE/BATCH、时间线/切片）
- 为多个业务模块提供调度能力（回测、数据源）

**infra层清理**：
```
infra.worker → 完全删除
infra.job_pipeline → 迁移到modules.scheduler
```

**迁移影响**：
- strategy：导入路径改为modules.scheduler
- tag：导入路径改为modules.scheduler
- data_source：导入路径改为modules.scheduler

---

## DataSource多线程分析

### 当前使用：

```python
# data_source/service/pipeline/runner.py
from core.infra.job_pipeline import JobPipeline
JobPipeline(
    worker=ExecutionBackend.THREAD,
    execute_mode=ExecuteMode.QUEUE
)
```

### 为什么不能直接用Python多线程？

**原因**：
- DataSource需要**业务调度逻辑**（bundle执行、on_result回调）
- 不是纯多线程执行（需要队列填池、回调机制）
- JobPipeline提供的正是业务调度能力

### 未来并行化：

如果data_source需要并行（多个handler并行抓取）：
- 仍然需要scheduler（队列填池、依赖管理）
- 只是从串行调度改为并行调度
- 不需要单独的pipeline

**结论**：
- DataSource多线程不是直接用ThreadPoolExecutor
- 需要业务调度逻辑（JobPipeline提供）
- 应该用modules.scheduler（统一调度模块）

---

## 最终推荐方案

**方案3: 统一Scheduler模块**

### 理由：

1. **架构正确性**：
   - scheduler是业务调度层，应该在modules层
   - 不止回测用，DataSource也用

2. **职责清晰**：
   - infra层：纯执行（ProcessPoolExecutor/ThreadPoolExecutor）
   - modules.scheduler：业务调度（QUEUE/BATCH、回调）
   - 业务层：具体业务逻辑

3. **未来扩展**：
   - MQ迁移：直接替换scheduler实现
   - DataSource并行：scheduler提供并行调度策略

### 实施步骤：

**Phase 1: 创建modules.scheduler**
```bash
core/modules/scheduler/
├─ module_info.yaml
├─ README.md
├─ __init__.py
├─ scheduler.py（空壳，未来迁移job_pipeline）
├─ dispatch_planner.py（空壳，未来迁移worker）
└─ types.py（空壳，未来迁移类型）
```

**Phase 2: 迁移dispatch规划**
- dispatch_planner.py → modules.scheduler
- dispatch_time_planner.py → modules.scheduler
- 修改导入路径（strategy/tag）

**Phase 3: 迁移类型定义**
- JobResult/JobStatus → modules.scheduler.types

**Phase 4: 迁移job_pipeline**
- JobPipeline核心 → modules.scheduler.scheduler
- 修改导入路径（strategy/tag/data_source）

**Phase 5: 废弃infra层**
- infra.worker → 完全删除
- infra.job_pipeline → 完整迁移到modules.scheduler

---

## 迁移后的架构

```text
┌─────────────────────────────────────┐
│ modules（业务层）                     │
│ ├─ strategy                         │
│ ├─ tag                              │
│ ├─ data_source                      │
│ └─ scheduler（业务调度层）            │
│    ├─ scheduler.py（核心调度器）      │
│    ├─ dispatch_planner.py          │
│    ├─ dispatch_time_planner.py     │
│    ├─ types.py                     │
│    └─ strategy/                    │
│       ├─ queue_strategy.py         │
│       └─ batch_strategy.py         │
└─────────────────────────────────────┘
         ↓ 调用
┌─────────────────────────────────────┐
│ Python标准库（执行层）                 │
│ ├─ ProcessPoolExecutor              │
│ ├─ ThreadPoolExecutor               │
└─ （无自定义包装）                     │
└─────────────────────────────────────┘
```

**未来MQ迁移**：
```
modules.scheduler
├─ scheduler.py → 本地调度器（ProcessPoolExecutor）
└─ mq_scheduler.py → MQ调度器（RabbitMQ）
```

业务代码切换：
```python
# 当前
scheduler = LocalScheduler()

# 未来
scheduler = MQScheduler(broker_url=...)
```

---

## 总结

**核心决策**：

1. **Worker模块完全废弃**
   - 多进程功能已废弃
   - Dispatch规划迁移到scheduler
   - 类型定义迁移到scheduler

2. **JobPipeline迁移到modules.scheduler**
   - 是业务调度层，应该在modules层
   - 不止回测用，DataSource也用

3. **DataSource多线程**
   - 不是纯多线程执行
   - 需要业务调度逻辑
   - 应该用modules.scheduler

**原则**：正确性胜过稳定性，不打补丁

**下一步**：开始Phase 1（创建modules.scheduler空壳）