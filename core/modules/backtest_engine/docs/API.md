# Backtest Scheduler API文档

**版本：** `0.1.0`

---

## 高层API

### BacktestScheduler

**用途**：回测任务调度器，理解回测语义

**用法**：
```python
from core.modules.backtest_scheduler import BacktestScheduler

scheduler = BacktestScheduler(
    execute_mode="queue",
    max_workers="auto",
    worker_profile="enumerator"
)

result = scheduler.run(
    tasks=[task1, task2, ...],
    on_result=callback_fn
)
```

---

### resolve_dispatch_plan

**用途**：基于内存约束规划并发度

**参数**：
- `total_entities: int` - 总任务数量
- `measured_mb_per_entity: Optional[float]` - 每个任务内存占用（MB）

**返回**：`DispatchPlan`对象

**用法**：
```python
from core.modules.backtest_scheduler import resolve_dispatch_plan

plan = resolve_dispatch_plan(
    total_entities=100,
    measured_mb_per_entity=2.5
)

print(f"entities_per_job={plan.entities_per_job}")
print(f"max_workers={plan.max_workers}")
```

---

### resolve_time_dispatch_plan

**用途**：基于时间约束规划并发度

**参数**：
- `total_entities: int` - 总任务数量
- `sec_per_entity: float` - 每个任务执行时间（秒）
- `sec_per_job_overhead: float` - job固定开销（秒）

**返回**：`TimeDispatchPlan`对象

**用法**：
```python
from core.modules.backtest_scheduler import resolve_time_dispatch_plan

plan = resolve_time_dispatch_plan(
    total_entities=100,
    sec_per_entity=0.5,
    sec_per_job_overhead=1.0
)

print(f"run_in_main_process={plan.run_in_main_process}")
```

---

## 类型定义

### DispatchPlan

**用途**：Dispatch规划结果类型

**字段**：
```python
@dataclass
class DispatchPlan:
    entities_per_job: int      # 每个job包含的entity数量
    max_workers: int           # 最大worker数量
    prefetch_ahead: int        # 预加载ahead数量
    dispatch_jobs: int         # 总job数量
    memory_budget_mb: float    # 内存预算（MB）
    memory_floor_mb: float     # 内存保底（MB）
    mb_per_entity: float       # 每个entity内存占用（MB）
```

---

### TimeDispatchPlan

**用途**：时间规划结果类型

**字段**：
```python
@dataclass
class TimeDispatchPlan:
    entities_per_job: int      # 每个job包含的entity数量
    max_workers: int           # 最大worker数量
    dispatch_jobs: int         # 总job数量
    run_in_main_process: bool  # 是否在主进程执行
    sec_per_entity: float      # 每个entity执行时间（秒）
    sec_per_job_overhead: float # job固定开销（秒）
    estimated_wall_sec: float  # 预估wall time（秒）
```

---

### JobResult

**用途**：任务执行结果类型

**字段**：
```python
@dataclass
class JobResult:
    job_id: str                # 任务ID
    status: JobStatus          # 任务状态
    result: Optional[Any]      # 执行结果
    error: Optional[Exception] # 错误信息
```

---

### JobStatus

**用途**：任务状态枚举

**值**：
```python
class JobStatus(Enum):
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消
```

---

## 调度策略

### QUEUE模式

**特点**：动态填池，低延迟

**配置**：
```python
scheduler = BacktestScheduler(
    execute_mode="queue",
    max_workers=4,
    prefetch_ahead=1
)
```

---

### BATCH模式

**特点**：批次执行，控内存

**配置**：
```python
scheduler = BacktestScheduler(
    execute_mode="batch",
    batch_size=10
)
```

---

## 完整示例

### Tag回测示例

```python
from core.modules.backtest_scheduler import (
    BacktestScheduler,
    resolve_dispatch_plan,
    JobResult
)

# 1. Dispatch规划
plan = resolve_dispatch_plan(
    total_entities=len(stock_ids),
    measured_mb_per_entity=2.5
)

# 2. 构建任务
tasks = [
    {"id": stock_id, "payload": {...}}
    for stock_id in stock_ids
]

# 3. 定义回调
def on_result(result: JobResult):
    if result.status == "completed":
        save_tag_data(result.result)
    else:
        logger.error(f"Task failed: {result.error}")

# 4. 执行调度
scheduler = BacktestScheduler(
    execute_mode="queue",
    max_workers=plan.max_workers,
    entities_per_job=plan.entities_per_job
)

scheduler.run(tasks, on_result)
```

---

### Strategy回测示例

```python
from core.modules.backtest_scheduler import resolve_time_dispatch_plan

# 时间规划
plan = resolve_time_dispatch_plan(
    total_entities=len(stock_ids),
    sec_per_entity=0.5,  # 每股0.5秒
    sec_per_job_overhead=1.0  # job开销1秒
)

if plan.run_in_main_process:
    # 单进程执行
    for stock_id in stock_ids:
        result = simulate_stock(stock_id)
        process_result(result)
else:
    # 多进程执行
    scheduler = BacktestScheduler(max_workers=plan.max_workers)
    scheduler.run(tasks, on_result)
```

---

## 配置参考

### worker.json配置

```json
{
  "enumerator": {
    "max_workers": "auto",
    "entities_per_job": "auto",
    "execute_mode": "queue",
    "prefetch_ahead": 1,
    "memory_floor_mb": 2048,
    "worker_memory_fraction": 0.85
  },
  "price_factor": {
    "max_workers": "auto",
    "execute_mode": "queue"
  }
}
```

---

## 相关文档

- [架构说明](./ARCHITECTURE.md)
- [设计细节](./DESIGN.md)
- [设计决策](./DECISIONS.md)