# Backtest Engine — 使用概览

**模块：** `modules.backtest_engine` · **版本：** 0.3.0

面向 **tag / strategy 等业务模块** 的回测调度 Facade。业务层提供 jobs 与 `execute_fn`；engine 负责探针、规划、并发执行与监控。

---

## 快速开始

```python
from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import JobContext, RunCallbacks, RunProgress
from core.modules.backtest_engine.core.shared.performance import resolve_entity_based_performance

# 应用方 dispatch 配置（见 tag/settings/dispatch.yaml 等）
from core.modules.tag.settings.worker_profile import profile_tag_entity_timeline_config

def execute_fn(ctx: JobContext) -> dict:
    # 子进程 / 主进程内执行单 job 逻辑
    return {"success": True, "job_id": ctx.job_id}

jobs = [{"id": "000001.SZ", "payload": {"entity_id": "000001.SZ"}}]

result = BacktestEngine.entity_based.run(
    jobs,
    execute_fn,
    performance=resolve_entity_based_performance(profile_tag_entity_timeline_config()),
    task_name="tag:demo",
    callbacks=RunCallbacks(on_result=lambda report, progress: None),
    enable_progress_display=True,
)

print(result.success, result.completed_jobs, result.elapsed_seconds)
```

统一入口也可使用 `BacktestEngine.run(mode=..., jobs=..., execute_fn=...)`。

---

## 两种执行模式

| 模式 | API | 适用场景 |
|------|-----|----------|
| **entity_based** | `BacktestEngine.entity_based.run` | 每个 entity（或 entity batch）独立并行；无 slice 内 cross-entity 编排 |
| **slice_based** | `BacktestEngine.slice_based.run` | 按日历 open_dates 切片；slice 内多 entity 经 reader/compute 管道交互 |

选用依据：**entity 是否在 slice 边界内发生编排交互**（见 `glossary.yaml`）。

内部实现包：`core/entity_based/`、`core/slice_based/`（与公开模式名一致）。

---

## 你需要提供什么

| 输入 | 说明 |
|------|------|
| **jobs** | `[{"id": str, "payload": dict}, ...]`，或用 `BacktestJob.from_dict` |
| **execute_fn** | `(JobContext) -> dict`，probe 与正式执行共用同一函数 |
| **performance** | 应用方 dispatch 配置 merge engine base 后的 dict（见下文） |
| **task_name** | 展示名，写入进度日志与 `JobContext` |
| **callbacks** | 可选 `RunCallbacks(on_result=..., on_release=...)` |
| **enable_progress_display** | 是否在 CMD 打印 engine 进度（进度始终计算） |

---

## 你不需要关心什么

- probe、plan、batch 切分、进程池 / orchestrator 编排
- 内存与并发 auto 解析（`MachineInfo`，来自 `core.infra.machine_capacity`）
- DuckDB process pool scope（performance 字段控制）

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
resolve_entity_based_performance(profile_tag_entity_timeline_config())
```

---

## Job 契约

**entity_based** payload 需包含单 entity 键（如 `entity_id` / `stock_id`）或 batch 路径 `jobs: [...]`。

**slice_based** payload 需包含 `open_dates` 与 bulk entity 键（如 `entity_ids`）。

校验：`BacktestJob.validate_many(jobs, mode=...)`，facade 在 run 前 fail-fast。

---

## 回调与结果

**RunCallbacks**

- `on_result(report, progress)` — 每个 job/batch 完成（主进程）
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

不要跨模块 import `core/entity_based/*`、`core/slice_based/*` 等内部路径。

---

## 集成方

| 模块 | 典型入口 |
|------|----------|
| tag | `run_tag_timeline_via_backtest_engine`, `run_tag_sliced_via_backtest_engine` |
| strategy | `run_*_via_backtest_engine`（enum / price / scanner） |

---

## 进一步阅读

| 文档 | 内容 |
|------|------|
| [api.yaml](./api.yaml) | API 契约（参数、类型、示例） |
| [glossary.yaml](./glossary.yaml) | 术语表 |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | 架构与目录 |
| [docs/DECISIONS.md](./docs/DECISIONS.md) | 设计决策 |
| [__test__/test_cases.yaml](./__test__/test_cases.yaml) | 单元测试用例索引 |
