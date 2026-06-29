# Backtest Scheduler 设计文档

**版本：** `0.1.0`

---

## 设计原则

### 职责归属原则

调度逻辑属于业务层，因为：
- 理解回测语义（时间线/切片）
- 不属于infra基础设施层
- 应该在modules层

### Python标准库优先

- ProcessPoolExecutor足够好，不需要自定义包装
- 不重复造轮子
- 降低复杂度

### 调度逻辑分离原则

- backtest_scheduler：时间线/切片、进程池
- data_source scheduler：依赖拓扑、线程池（独立）
- 不强行合并（逻辑不同）

---

## 核心组件设计

### 1. Scheduler核心

**职责**：
- 队列填池策略（QUEUE/BATCH）
- on_result回调机制
- JobContext封装
- 任务编排

**接口设计**：
```python
class BacktestScheduler:
    def schedule(
        self,
        tasks: List[Task],
        on_result: Callable[[Result], None],
        strategy: SchedulingStrategy
    ) -> ScheduleResult:
        """调度任务执行"""
        pass

    def shutdown(self):
        """关闭调度器"""
        pass
```

---

### 2. Dispatch Planner

**职责**：
- 基于内存约束规划并发（entities_per_job、memory_budget_mb）
- 基于时间约束规划并发（sec_per_entity、sec_per_job_overhead）
- 自动优化批次大小和worker数量

**核心函数**：
```python
def resolve_dispatch_plan(
    total_entities: int,
    measured_mb_per_entity: Optional[float]
) -> DispatchPlan:
    """基于内存预算规划entities_per_job和max_workers"""
    pass

def resolve_time_dispatch_plan(
    total_entities: int,
    sec_per_entity: float,
    sec_per_job_overhead: float
) -> TimeDispatchPlan:
    """基于时间约束规划entities_per_job和max_workers"""
    pass
```

---

### 3. 类型定义

**核心类型**：
```python
@dataclass
class DispatchPlan:
    entities_per_job: int
    max_workers: int
    memory_budget_mb: float
    prefetch_ahead: int
    ...

@dataclass
class JobResult:
    job_id: str
    status: JobStatus
    result: Optional[Any]
    error: Optional[Exception]

class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

---

## 调度策略设计

### QUEUE策略

**流程**：
```text
1. 启动时确定max_workers（auto或配置）
2. 动态填池：
   - 提交任务到ProcessPoolExecutor
   - 监听Future完成
   - 触发on_result回调
   - 补充新任务（保持in-flight数量）
3. 所有任务完成后shutdown
```

**特点**：
- 低延迟（任务完成立即补充）
- 高吞吐（持续填池）
- 内存友好（prefetch_ahead控制）

---

### BATCH策略

**流程**：
```text
1. 按批次prepare任务
2. 串行执行每批：
   - 提交整批任务
   - 等待整批完成
   - checkpoint
3. 进入下一批
```

**特点**：
- 控峰值内存（批间串行）
- checkpoint友好（每批后可持久化）
- 稳定性高（内存可控）

---

## Dispatch规划算法

### 内存驱动规划

**算法逻辑**：
```text
1. 获取系统可用内存
2. 计算memory_budget_mb（可用内存 - memory_floor_mb）
3. 计算entities_per_job：
   - 如果有measured_mb_per_entity：budget / mb_per_entity
   - 否则：启发式规则（5-50）
4. 计算max_workers：min(cpu_count - reserve_cores, dispatch_jobs)
```

**关键参数**：
- memory_floor_mb：系统保底空闲内存（1GB）
- worker_memory_fraction：可用内存占比（0.85）
- entities_per_job ∈ [5, 50]：实验优化值

---

### 时间驱动规划

**算法逻辑**：
```text
1. 计算wall time公式：T(W) = O + ceil(N/W)*C
   - O：job overhead（固定开销）
   - N：total entities
   - W：workers
   - C：sec_per_entity
2. 在W ∈ [1, Wmax]上最小化T(W)
3. 特殊情况：
   - N*C < O：主进程单batch（run_in_main_process=True）
```

---

## 数据流设计

```text
┌─────────────────────────────────────┐
│ tag/strategy（业务层）               │
│ ├─ 构建任务列表                       │
│ ├─ 定义execute函数                   │
│ ├─ 定义on_result回调                 │
└─────────────────────────────────────┘
         ↓ 调用
┌─────────────────────────────────────┐
│ BacktestScheduler                    │
│ ├─ Dispatch规划                      │
│ │  ├─ 计算entities_per_job           │
│ │  ├─ 计算max_workers                │
│ │  └─ 优化并发度                     │
│ ├─ 队列填池                          │
│ │  ├─ QUEUE：动态填池                │
│ │  ├─ BATCH：批次执行                │
│ ├─ 回调处理                          │
│ │  ├─ 监听Future完成                 │
│ │  ├─ 触发on_result                  │
│ └─────────────────────────────────────┘
         ↓ 调用
┌─────────────────────────────────────┐
│ ProcessPoolExecutor                  │
│ ├─ submit任务                        │
│ ├─ execute（子进程）                 │
│ ├─ 返回Future                        │
└─────────────────────────────────────┘
```

---

## 性能优化设计

### 内存优化

- entities_per_job动态调整（5-50）
- prefetch_ahead控制预加载
- memory_budget_mb预算控制

### 时间优化

- worker数量自动优化（wall time最小化）
- 避免过度并行（O > N*C时单进程）
- 动态调度（QUEUE模式）

---

## 错误处理设计

### 任务失败处理

```python
class JobResult:
    status: JobStatus
    error: Optional[Exception]
```

- FAILED状态记录错误
- on_result回调可处理失败
- 不影响其他任务执行

---

## 配置设计

### worker.json配置

```json
{
  "enumerator": {
    "max_workers": "auto",
    "entities_per_job": "auto",
    "execute_mode": "queue",
    "prefetch_ahead": 1
  }
}
```

---

## 相关文档

- [架构说明](./ARCHITECTURE.md)
- [API文档](./API.md)
- [设计决策](./DECISIONS.md)