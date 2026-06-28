# 架构重构提案：Worker vs Backtest Pipeline vs MQ迁移

**日期：** 2026-06-28
**状态：** 提案阶段

---

## 问题诊断

### 当前架构问题

1. **职责边界不清晰**
   - worker特指多进程/多线程执行，不应包含业务调度
   - ProcessWorker.run_jobs已废弃，但功能被JobPipeline吸收，导致混淆

2. **job_pipeline定位错误**
   - 不属于infra层，更像业务module层
   - 是worker的上层调度者，负责分配、指挥worker工作
   - 理解回测语义（时间线/切片），应该叫"backtest pipeline"

3. **MQ迁移路径不清楚**
   - 当前架构没有抽象接口
   - 无法轻易替换调度实现

---

## 三层架构设计

### Layer 1: Infra执行层

**职责**：
- 纯粹的多进程/多线程执行器
- 不理解业务语义
- 只负责：submit、shutdown、stats、监控

**定位**：
- infra.worker模块
- 通用基础设施，不依赖业务

**API设计**：
```python
class ProcessExecutor:
    """纯粹的进程池执行器"""

    def submit(self, task: Callable, *args, **kwargs) -> Future:
        """提交单个任务"""
        pass

    def submit_batch(self, tasks: List[Callable]) -> List[Future]:
        """批量提交任务"""
        pass

    def shutdown(self, wait: bool = True):
        """关闭执行器"""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        pass
```

**特点**：
- 不包含队列填池、回调等调度逻辑
- 纯粹的执行器，类似标准库的ProcessPoolExecutor包装

---

### Layer 2: 业务调度层

**职责**：
- 理解回测业务语义（时间线/切片）
- 队列填池策略（QUEUE/BATCH）
- on_result回调、JobContext封装
- 指挥worker执行

**定位**：
- modules.backtest.pipeline（重命名）
- 业务模块层，不属于infra

**抽象接口设计（关键）**：
```python
class BacktestScheduler(ABC):
    """回测调度器抽象接口"""

    @abstractmethod
    def schedule_tasks(
        self,
        tasks: List[Task],
        on_result: Callable[[Result], None],
        strategy: SchedulingStrategy,
    ) -> ScheduleResult:
        """调度任务执行"""
        pass

    @abstractmethod
    def shutdown(self):
        """关闭调度器"""
        pass
```

**实现方式1：轻量级（当前）**
```python
class LocalBacktestScheduler(BacktestScheduler):
    """本地调度器 - 基于ProcessExecutor"""

    def __init__(self):
        self.executor = ProcessExecutor()

    def schedule_tasks(self, tasks, on_result, strategy):
        # QUEUE/BATCH策略实现
        if strategy == SchedulingStrategy.QUEUE:
            return self._schedule_queue(tasks, on_result)
        elif strategy == SchedulingStrategy.BATCH:
            return self._schedule_batch(tasks, on_result)

    def _schedule_queue(self, tasks, on_result):
        # 实现QUEUE模式：动态填池
        futures = []
        for task in tasks:
            future = self.executor.submit(task)
            future.add_done_callback(lambda f: on_result(f.result()))
            futures.append(future)
        return futures
```

**实现方式2：MQ（未来）**
```python
class MQBacktestScheduler(BacktestScheduler):
    """MQ调度器 - 基于RabbitMQ/Kafka"""

    def __init__(self, broker_url: str):
        self.connection = pika.BlockingConnection(pika.URLParameters(broker_url))
        self.channel = self.connection.channel()

    def schedule_tasks(self, tasks, on_result, strategy):
        # 发布任务到MQ
        for task in tasks:
            self.channel.basic_publish(
                exchange='backtest',
                routing_key='tasks',
                body=json.dumps(task.to_dict())
            )

        # 设置回调队列监听结果
        self.channel.basic_consume(
            queue='results',
            on_message_callback=lambda ch, method, props, body: on_result(json.loads(body))
        )
```

**特点**：
- 通过抽象接口，可以轻易替换实现
- 当前用轻量级LocalBacktestScheduler
- 未来用MQBacktestScheduler，无需修改业务代码

---

### Layer 3: 业务层

**职责**：
- tag/strategy的具体业务逻辑
- 使用业务调度层编排任务

**示例**：
```python
# 当前使用（轻量级）
scheduler = LocalBacktestScheduler()
scheduler.schedule_tasks(tasks, on_result, SchedulingStrategy.QUEUE)

# 未来使用（MQ）
scheduler = MQBacktestScheduler(broker_url='amqp://localhost')
scheduler.schedule_tasks(tasks, on_result, SchedulingStrategy.QUEUE)
```

**特点**：
- 业务代码不需要修改
- 只需要替换scheduler实现

---

## 迁移路径设计

### Phase 1: 当前架构（轻量级）

```text
业务层（tag/strategy）
    ↓ 调用
LocalBacktestScheduler（modules.backtest.pipeline）
    ↓ 调用
ProcessExecutor（infra.worker）
    ↓ 调用
Python标准库ProcessPoolExecutor
```

**优点**：
- 无需外部依赖
- 下载即用
- 轻量级

---

### Phase 2: 混合架构（可选）

```text
业务层（tag/strategy）
    ↓ 根据配置选择
┌─────────────┬─────────────┐
│ Local       │ MQ          │
│ Scheduler   │ Scheduler   │
└─────────────┴─────────────┘
    ↓ 调用
ProcessExecutor / MQ Broker
```

**优点**：
- 用户可以选择轻量级或MQ
- 通过配置切换
- 不修改业务代码

---

### Phase 3: 纯MQ架构（企业级）

```text
业务层（tag/strategy）
    ↓ 调用
MQBacktestScheduler
    ↓ 发布任务
MQ Broker（RabbitMQ/Kafka）
    ↓ 分发
独立Worker进程（分布式）
```

**优点**：
- 分布式执行
- 横向扩展
- 高可用

---

## 具体实施步骤

### Step 1: 重命名和重新定位

**job_pipeline → backtest.pipeline**
- 移动位置：infra.job_pipeline → modules.backtest.pipeline
- 重命名：JobPipeline → BacktestScheduler
- 明确定位：业务调度层，不属于infra

### Step 2: 抽象调度接口

**创建抽象接口**：
```python
# modules/backtest/pipeline/scheduler_interface.py
class BacktestScheduler(ABC):
    @abstractmethod
    def schedule_tasks(...)
```

### Step 3: 实现轻量级版本

**LocalBacktestScheduler**：
- 基于当前JobPipeline代码
- 实现抽象接口
- 保持轻量级特性

### Step 4: Worker模块清理

**infra.worker**：
- 恢复ProcessExecutor职责（纯粹执行器）
- 不包含业务调度逻辑
- 提供清晰的执行API

### Step 5: 业务层适配

**修改调用代码**：
```python
# 当前
from core.infra.job_pipeline import JobPipeline
pipeline = JobPipeline(...)

# 改为
from core.modules.backtest.pipeline import LocalBacktestScheduler
scheduler = LocalBacktestScheduler(...)
```

---

## MQ迁移示例（用户视角）

### 当前使用（无MQ）

```python
# userspace/backtest_config.yaml
scheduler:
  type: local  # 轻量级调度器
  max_workers: auto
  execute_mode: queue
```

### 未来使用（MQ）

```python
# userspace/backtest_config.yaml
scheduler:
  type: mq  # MQ调度器
  broker_url: amqp://localhost:5672
  queue_name: backtest_tasks
```

**业务代码不需要修改**：
```python
# 业务代码
scheduler = create_scheduler_from_config(config)  # 自动选择实现
scheduler.schedule_tasks(tasks, on_result, strategy)
```

---

## 总结

**核心思想**：
1. **清晰分层**：infra执行层 + 业务调度层
2. **抽象接口**：方便替换调度实现
3. **轻量级优先**：当前无需外部依赖
4. **迁移友好**：未来可轻易切换到MQ

**关键收益**：
- 当前用户：下载即用，轻量级
- 专业用户：可选MQ，分布式
- 开发者：清晰分层，易维护

**下一步**：
1. 确认架构方案
2. 重命名job_pipeline → backtest.pipeline
3. 创建抽象调度接口
4. 实现LocalBacktestScheduler
5. 清理worker模块职责