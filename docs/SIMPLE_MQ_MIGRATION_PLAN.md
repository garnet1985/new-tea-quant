# 最简MQ迁移方案

**核心思想**：不需要抽象接口层，直接替换调度实现

---

## 为什么不需要抽象接口层？

**原因**：
- JobPipeline（BacktestScheduler）职责很重：理解业务语义、队列管理、回调
- 如果抽象接口层，需要重新实现所有功能
- MQ本身就有调度能力，不需要中间层

---

## 最简迁移方案：直接替换

### 当前架构（轻量级）

```python
# 业务代码直接使用
from core.infra.job_pipeline import JobPipeline

pipeline = JobPipeline(
    execute=execute_fn,
    on_result=on_result_fn,
    max_workers="auto"
)
pipeline.run(jobs)
```

### 未来架构（MQ）

```python
# 业务代码直接使用MQ
import pika
from core.modules.backtest.mq_runner import MQBacktestRunner

runner = MQBacktestRunner(
    broker_url="amqp://localhost",
    execute=execute_fn,
    on_result=on_result_fn,
    queue_name="backtest_tasks"
)
runner.run(jobs)
```

**关键设计**：
- `MQBacktestRunner`封装MQ的发布/订阅逻辑
- 业务代码只需要：创建runner + run(jobs)
- 不需要中间的BacktestScheduler抽象层

---

## 实施步骤（最简化）

### Step 1: 当前不动（轻量级）

- JobPipeline继续在infra层
- 业务代码继续使用JobPipeline
- 不需要重构

### Step 2: 未来需要MQ时

**创建MQ runner**：
```python
# modules/backtest/mq_runner.py
class MQBacktestRunner:
    def __init__(self, broker_url, execute, on_result, queue_name):
        self.connection = pika.BlockingConnection(...)
        self.execute = execute
        self.on_result = on_result
        self.queue_name = queue_name

    def run(self, jobs):
        # 发布任务到MQ
        for job in jobs:
            self.publish_task(job)

        # 监听结果队列
        self.listen_results()
```

**业务代码修改**：
```python
# 当前
pipeline = JobPipeline(...)
pipeline.run(jobs)

# 未来（MQ）
runner = MQBacktestRunner(...)
runner.run(jobs)
```

---

## 为什么这样设计最简单？

### 优点：

1. **不需要抽象接口层**
   - MQ本身就是调度层
   - 不需要中间的BacktestScheduler抽象
   - 减少一层抽象，降低复杂度

2. **迁移成本低**
   - 业务代码只需要改2行：
     - 创建runner（1行）
     - run(jobs)（1行）
   - 不需要重构整个架构

3. **符合实际需求**
   - 当前用户：轻量级，不需要MQ
   - 未来用户：MQ分布式，需要专业配置
   - 不需要"中间层"来兼容两者

---

## Worker模块定位（最终结论）

```
infra.worker：
├─ dispatch_planner.py    ← Dispatch规划（核心功能）
│   ├─ resolve_dispatch_plan
│   ├─ resolve_memory_budget_mb
│
├─ dispatch_time_planner.py  ← 时间规划
│   ├─ resolve_time_dispatch_plan
│
├─ process_worker.py      ← 已废弃，但保留类型
│   ├─ JobResult（类型定义）
│   ├─ JobStatus（类型定义）
│   └─ ProcessWorker（已废弃，保留向后兼容导入）
│
└─ Worker Facade          ← 提供快捷访问
    ├─ resolve_dispatch_plan
    ├─ resolve_time_dispatch_plan
    └─ DispatchPlan/TimeDispatchPlan类型
```

**定位**：
- 不是执行层（ProcessPoolExecutor足够）
- 是辅助工具模块（Dispatch规划 + 类型定义）

---

## 最终架构（最简）

```text
业务层（tag/strategy）
    ↓ 直接调用
┌─────────────┬─────────────┐
│ 当前        │ 未来        │
│ JobPipeline │ MQRunner    │
│ (轻量级)    │ (分布式)    │
└─────────────┴─────────────┘
    ↓ 调用
ProcessPoolExecutor / MQ Broker

辅助工具：infra.worker（Dispatch规划 + 类型定义）
```

**不需要中间的抽象层！**

---

## 总结

**最简方案**：
- 不创建抽象BacktestScheduler接口层
- 当前：继续用JobPipeline（轻量级）
- 未来：直接用MQRunner（分布式）
- 迁移：业务代码改2行即可

**Worker定位**：
- 辅助工具模块（Dispatch规划 + 类型定义）
- 不是执行层（Python标准库足够）

**优点**：
- 当前用户：轻量级，下载即用
- 未来用户：MQ分布式，专业配置
- 迁移成本：极低（改2行代码）