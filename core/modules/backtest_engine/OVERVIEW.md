# Backtest Engine — 使用概览

主要业务功能有 3 个：

- **调度任务**：使用探针的方式决定怎么组装任务能更有效率完成回测（不同模式组装方式不同）
- **推进回测**：按照时序推进回测
- **性能监控**：监控运行，保证稳定，同时记录核心运行效率，找到改进空间

**数据加载不在引擎内** 回测引擎的数据来源可能不同，可能是db计算数据，可能是一些时序的计算结果（比如策略枚举器的结果），因此，为了更广泛的使用方式，回测引擎主要功能将聚焦在调度（效率），推进（回测核心），性能（系统不要奔溃和如何优化）3个点上，数据需要使用方注入

主要回测有 2 个模式：

**模式1: entity_based**：把所有 entity（比如股票）通过任务调度分成多个组，每个 entity 通过自己的时间轴前进，entity 之间的时间轴不统一也不需要统一。适合于 entity 之间没有相互依赖的情景。

**典型例子**：当股票达到自己 RSI 一个低点的时候视作一次机会，股票只需要知道自己的数据，和别的股票无关。

**模式2: slice_based**：所有 entity 通过统一时间轴推进，时钟同步前进。适合于 entity 之间互相依赖的情景。

**典型例子**：每个月取交易量最大的 10 个股票投资——需要对统一时间段内排序，各股票依赖彼此交易量。

## 快速开始

```python
from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import JobContext, RunCallbacks, RunProgress
from core.modules.backtest_engine.core.performance.settings import (
    resolve_entity_based_performance,
)

# 应用方 dispatch 配置（见 tag/settings/dispatch.yaml 等）
from core.modules.tag.settings.worker_profile import profile_tag_entity_based_config

def execute_fn(ctx: JobContext) -> dict:
    # 子进程 / 主进程内执行单 job 逻辑
    return {"success": True, "job_id": ctx.job_id}

jobs = [{"id": "000001.SZ", "payload": {"entity_id": "000001.SZ"}}]

result = BacktestEngine.entity_based.run(
    jobs,
    execute_fn=execute_fn,
    performance=resolve_entity_based_performance(profile_tag_entity_based_config()),
    task_name="tag:demo",
    callbacks=RunCallbacks(on_task_result=lambda report, progress: None),
    enable_progress_display=True,
)

print(result.success, result.completed_jobs, result.elapsed_seconds)
```

统一入口也可使用 `BacktestEngine.run(mode=..., jobs=..., execute_fn=...)`。  
日历推进路径用 `timeline_hooks_factory=`（与 `execute_fn` 二选一）。

---

## 两种执行模式

| 模式 | API | 适用场景 |
|------|-----|----------|
| **entity_based** | `BacktestEngine.entity_based.run` | 每个 entity（或 entity batch）独立并行；无 slice 内 cross-entity 编排 |
| **slice_based** | `BacktestEngine.slice_based.run` | 按日历 open_dates 切片；slice 内多 entity 经 reader/compute 管道交互 |

选用依据：**entity 是否在 slice 边界内发生编排交互**（见 `glossary.yaml`）。

内部实现包：`core/schedule/entity_based/`、`core/schedule/slice_based/`、`core/timeline/`、`core/performance/`。

---

## 你需要提供什么

| 输入 | 说明 |
|------|------|
| **jobs** | `[{"id": str, "payload": dict}, ...]`，或用 `BacktestJob.from_dict` |
| **execute_fn** 或 **timeline_hooks_factory** | 二选一：opaque 执行，或日历 hooks 工厂 |
| **performance** | 应用方 dispatch 配置 merge engine base 后的 dict（见下文） |
| **task_name** | 展示名，写入进度日志与 `JobContext` |
| **callbacks** | 可选；含 `on_before_task_start`（数据面注入）等 |
| **enable_progress_display** | 是否在 CMD 打印 engine 进度（进度始终计算） |

---

## 你不需要关心什么

- probe、plan、batch 切分、进程池 / orchestrator 编排
- 内存与并发 auto 解析（`MachineInfo`，来自 `core.infra.machine_capacity`）
- DuckDB process pool scope（performance 字段控制）
- 如何从 DB/shm 装 Contract（使用方 `JobBundleLoader` / 自备数据）

---

## performance 与 dispatch 配置

```
engine base defaults（EntityBasedPerformance / SliceBasedPerformance）
    → merge 应用方 dispatch 配置
    → validate + resolve（facade 入口一次完成）
    → run
```

- **应用方**在模块内维护 `settings/dispatch.yaml`（性能基准调优，用户不可改）
- **engine 不读** global `worker.json` 的 dispatch 段
- **禁止** `settings["performance"]` 传入 engine；业务字段用 `update_mode`、`run_options` 等

示例（tag timeline）：

```python
resolve_entity_based_performance(profile_tag_entity_based_config())
```

---

## Job 契约

**entity_based** payload 须含非空 ``entity_specified``（``List[{id}]``）；不允许 ``entity_id`` / ``stock_id`` 等别名。

**slice_based** payload 须含非空 ``entity_ids`` 与正整数 ``timeline_point_count``；全量 points 不进 payload，worker 从全局 ``trade.calendar`` 解析。

校验：`BacktestJob.validate_many(jobs, mode=...)`，facade 在 run 前 fail-fast。

---

## 回调与结果

**RunCallbacks**

- `on_before_task_start(context) → init` — 使用方装载数据面（写入 `job_context.init`）
- `on_after_task_complete(context)` — task 收尾（如 flush）
- `on_task_result(report, progress)` — 每个 job/batch 完成（主进程）
- `on_release(report)` — entity_based 专用，batch 资源释放

**RunResult**

- `success`, `total_jobs`, `completed_jobs`, `failed_jobs`, `elapsed_seconds`
- `job_results`, `plan`, `monitor_stats`

---

## 进度

engine 内置四阶段进度（prep 5% / plan 10% / execute 80% / finish 5%）。

- **entity_based**：每个 batch 完成更新 execute 段
- **slice_based**：orchestrator 每完成一个 slice 通过 `_engine_on_execute_unit_done` hook 上报

CMD 输出示例：

```
任务：tag:demo entity_based 执行总进度：42%
任务：tag:demo entity_based 回测进度：17/42，执行总进度：42%
```

---

## 公开 import 边界

```python
from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import (
    BacktestJob,
    JobContext,
    JobReport,
    RunCallbacks,
    RunProgress,
)
```

数据装载：

```python
from core.modules.strategy.core.services.entity_loader.job_bundle_loader import (
    JobBundleLoader,
)
```

不要跨模块 import `core/schedule/*` 等内部路径。

---

## 集成方

| 模块 | 典型入口 |
|------|----------|
| tag | `run_tag_timeline_via_backtest_engine`, `run_tag_sliced_via_backtest_engine` |
| strategy | enumerator pipeline / price / portfolio（经 BE 调度；各自负责数据面） |

---

## 进一步阅读

| 文档 | 内容 |
|------|------|
| [api.yaml](./api.yaml) | API 契约（参数、类型、示例） |
| [glossary.yaml](./glossary.yaml) | 术语表 |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | 架构与目录 |
| [docs/DECISIONS.md](./docs/DECISIONS.md) | 设计决策 |
| [__test__/test_cases.yaml](./__test__/test_cases.yaml) | 单元测试用例索引 |
