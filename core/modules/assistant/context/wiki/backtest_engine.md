---
title: 回测引擎
aliases:
  - backtest engine
  - timeline
  - scheduling
  - pipeline
summary: NTQ的无业务回测核心引擎，自带探针和任务调度功能。
---

# 回测引擎：BacktestEngine

## 定位

`BacktestEngine` 是 NTQ 的**回测调度门面**。它不读业务数据、不做策略判断——它负责时间轴构建、任务调度、并行执行和资源监控。

策略和 Tag 系统都通过 BacktestEngine 执行实际计算。

## 门面

```python
from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import RunCallbacks, JobContext

# entity_based 模式
result = BacktestEngine.entity_based.run(
    jobs,
    start="20240102",
    end="20240103",
    callbacks=RunCallbacks(on_tick=my_on_tick),
    task_name="demo",
)

# slice_based 模式
result = BacktestEngine.slice_based.run(
    jobs,
    start="20240102",
    end="20241231",
    callbacks=callbacks,
    task_name="backtest",
)
```

## 核心概念

| 概念           | 类              | 说明                                           |
| ------------ | -------------- | -------------------------------------------- |
| Timeline     | `Timeline`     | 模拟时间轴，支持 calendar/clock/event/custom 四种 kind |
| BacktestJob  | `BacktestJob`  | 任务合约，`{"id": str, "payload": dict}`          |
| RunCallbacks | `RunCallbacks` | 回调钩子集合（on\_tick、on\_task\_start 等）           |
| RunResult    | `RunResult`    | 运行结果，含模式、成功状态、作业计数、耗时、监控统计                   |

## 两种执行模式

### entity\_based（实体并行）

| 特征     | 说明                                             |
| ------ | ---------------------------------------------- |
| 并行模型   | `ProcessPoolExecutor` 按实体批次分配                  |
| 适用场景   | 无需跨实体切片协调的策略                                   |
| Worker | `TimelineWorkerExecute`，调用 `callbacks.on_tick` |
| 内存     | 每个进程独立加载窗口内数据                                  |

```
Jobs → 分配到 ProcessPool → 每个进程独立执行 Timeline → on_tick 回调
```

### slice\_based（切片并行）

| 特征     | 说明                                |
| ------ | --------------------------------- |
| 并行模型   | 按日历切片，每切片加载+计算                    |
| 适用场景   | 全窗口 per-entity 数据可能超过内存时          |
| Worker | `SliceWorkerExecute`              |
| 内存控制   | 动态调整 `preload_depth`，内存压力时降低预加载深度 |

### 不变量

slice\_based 的核心约束：**N 个正式切片 → 至少 N 次 per-entity 数据库加载**。禁止在任务启动时一次性加载全窗口数据。

## 内部管道：Probe → Plan → Execute → Monitor

```
validate → plan → monitor setup → execute → RunResult
```

### 1. Probe（探测）

- 检测机器容量（CPU 核数、可用内存）

- 可选的调度探测：用小量数据估算资源需求

- 输出 `DispatchPlan`

### 2. Plan（规划）

- 根据探测结果分配批次

- entity\_based：按实体数量分配到进程池

- slice\_based：规划切片宽度和 `preload_depth`

- 生成 `DispatchPlan`

### 3. Execute（执行）

- entity\_based：`ProcessPoolExecutor` 启动 Worker 进程

  - Worker 内：`TimelineWorkerExecute` 加载数据 → 调用 `on_tick`

- slice\_based：加载正式切片 → `SliceWorkerExecute` 计算

  - 监控内存，压力时降低 `preload_depth`

### 4. Monitor（监控）

- 采样每个 Job 的 RSS（内存）和耗时

- 动态调整在途工作量

- 输出监控统计到 `RunResult`

## Timeline

`Timeline` 是模拟时间轴，必须在 `run()` 之前通过 `set()` 或参数设置。

```python
timeline = Timeline()
timeline.set(start="20240102", end="20241231")
# kind 默认为 "calendar"，从 CalendarService 构建交易日点
```

### 时间轴构建规则

1. 显式 `timeline` 参数 → 直接使用这些日期点
2. 否则 → `CalendarService.load_open_dates(start, end)` 构建
3. 窗口通过 `data.json` 系统边界校验
4. 系统窗口 = `default_start_date` → `latest_completed_trading_date`

### Timeline kind

| kind       | 说明             |
| ---------- | -------------- |
| `calendar` | 按交易日推进（默认）     |
| `clock`    | 按时钟推进（分钟级，期货用） |
| `event`    | 按事件推进（非规则时间）   |
| `custom`   | 用户自定义时间点       |

### 共享内存传递

`Timeline.begin_run()` 发布时间轴：

1. 优先使用 SharedMemory
2. SharedMemory 不可用时，时间轴嵌入 Job 的 `payload.global`

Worker 进程从共享内存或 payload 中读取时间轴。

## RunCallbacks

| 钩子                         | 调用时机                     |
| -------------------------- | ------------------------ |
| `on_task_start(payload)`   | 任务开始，加载全局数据、构建状态         |
| `on_tick(job_context)`     | 每个时间点，执行业务逻辑（策略钩子在这里被调用） |
| `on_task_complete(result)` | 任务完成，返回统计信息              |

策略引擎实现 `RunCallbacks` 来桥接 BacktestEngine 和策略钩子。

## RunResult

```python
@dataclass
class RunResult:
    mode: str           # "entity_based" / "slice_based"
    success: bool
    job_count: int
    elapsed_seconds: float
    job_reports: List[dict]
    plan: dict          # DispatchPlan
    monitor_stats: dict # RSS/耗时采样
```

## 版本

BacktestEngine 自身不维护版本快照。引擎版本通过 `get_version()` 获取，记录在策略模拟的元数据中：

```python
# VersionMetaStore 记录
{
    "engine_version": str(get_version() or ""),
    ...
}
```

策略版本管理（`execute_fp`、`env_fp`、版本注册、pinning）由 `VersionMetaStore` 独立负责，不在 BacktestEngine 模块内。

## 与其他模块的关系

| 模块                  | 关系                                                  |
| ------------------- | --------------------------------------------------- |
| **strategy**        | 策略引擎实现 RunCallbacks，通过 BE 执行回测                      |
| **tag**             | per\_entity 标签通过 BE 的 entity\_based/slice\_based 执行 |
| **market\_profile** | 通过 CalendarService 构建 Timeline 时间轴                  |
| **data\_contract**  | Worker 进程通过 JobBundleLoader 签发数据合约                  |

## 边界

BacktestEngine 的设计边界：

| 做什么        | 不做什么     |
| ---------- | -------- |
| 时间轴构建和管理   | 读业务数据库   |
| 任务调度和并行执行  | 策略逻辑判断   |
| 资源监控和动态调整  | 版本管理和持久化 |
| 共享内存传递全局数据 | 报告生成     |

