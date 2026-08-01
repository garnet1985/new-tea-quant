# Backtest Engine — 架构

**模块：** `modules.backtest_engine` · **版本：** 0.3.0

---

## 定位

回测调度 Facade：对 tag / strategy 提供统一的 **probe → plan → execute → monitor** 流水线。业务语义（打 tag、枚举、价格因子等）在 `execute_fn` 内；engine 只管并发、内存预算与执行编排。

---

## 职责边界

| In scope | Out of scope |
|----------|--------------|
| 两种执行模式（entity_based / slice_based） | 业务计算与入库 |
| Job 契约校验、dispatch 规划、探针 | 读取 global `worker.json` dispatch |
| ProcessPool（entity）/ 主进程 orchestrator（slice） | 数据源任务调度 |
| `RunCallbacks`、内置进度、`RunResult` | 用户 settings 中的 performance 覆盖 |

---

## 分层结构

```text
┌─────────────────────────────────────────────────────────┐
│  tag / strategy（应用层）                                 │
│  jobs, execute_fn, dispatch.yaml → performance, callbacks │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  BacktestEngine（Facade）                                  │
│  run / entity_based / slice_based · RunResult              │
└──────────────────────────┬──────────────────────────────┘
                           │
         ┌─────────────────┴─────────────────┐
         ▼                                   ▼
┌─────────────────────┐           ┌─────────────────────┐
│ entity_based        │           │ slice_based         │
│ ExecutePipeline     │           │ ExecutePipeline     │
│ Planner / Probe     │           │ Planner / Probe     │
│ EntityExecutor      │           │ SliceExecutor       │
│ EntityRunMonitor    │           │ SliceRunMonitor     │
└──────────┬──────────┘           └──────────┬──────────┘
           │                                  │
           └──────────────┬───────────────────┘
                          ▼
              ┌───────────────────────┐
              │ core/shared           │
              │ jobs, types, context  │
              │ performance, progress │
              └───────────┬───────────┘
                          ▼
              ┌───────────────────────┐
              │ core.infra            │
              │ machine_capacity      │
              │ duckdb process pool   │
              └───────────────────────┘
```

---

## 目录结构

```text
backtest_engine/
├── OVERVIEW.md              # 使用者快速入门
├── backtest_engine.py       # Facade
├── contracts.py             # 跨模块契约 re-export
├── api.yaml                 # API 契约
├── glossary.yaml            # 术语
├── module_info.yaml
├── core/
│   ├── shared/
│   │   ├── jobs.py          # BacktestJob 契约
│   │   ├── types.py         # JobContext, RunCallbacks, …
│   │   ├── context.py       # ExecutionContext（run 级）
│   │   ├── performance.py   # Entity/Slice BasedPerformance
│   │   ├── progress.py      # RunProgressReporter
│   │   ├── modes.py         # BacktestMode 枚举
│   │   ├── duckdb_executor_scope.py
│   │   └── base_planner.py
│   ├── entity_based/        # entity_based 实现
│   │   ├── execute_pipeline.py
│   │   ├── planner.py
│   │   ├── probe.py
│   │   ├── executor.py
│   │   ├── executor_duckdb.py
│   │   └── monitor.py
│   └── slice_based/         # slice_based 实现
│       ├── execute_pipeline.py
│       ├── planner.py
│       ├── probe.py
│       ├── executor.py
│       ├── executor_duckdb.py
│       └── monitor.py
├── docs/
│   ├── ARCHITECTURE.md
│   └── DECISIONS.md
└── __test__/
    ├── test_cases.yaml
    └── test_*.py
```

---

## 执行流程

两种模式共用：**validate → plan → monitor setup → execute → RunResult**。

### entity_based

1. **Plan**：`MachineInfo` 取容量 → 可选 dispatch probe → `DispatchPlan`（`max_workers`, `entities_per_job`, batches）
2. **Execute**：`ProcessPoolExecutor` + QUEUE 填池（完成 1 补 1）；子进程调用 `execute_fn(JobContext)`
3. **Monitor**：按 job 采样 RSS/耗时，动态调整 in-flight 上限

### slice_based

1. **Plan**：slice probe → reader/compute/queue 规划 → `SliceDispatchPlan`
2. **Execute**：**无外层 ProcessPool**；主进程调用 `execute_fn`，内部 orchestrator 自管 reader/compute 子进程
3. **Monitor**：按 slice 样本聚合，内存压力时下调 preload

slice 细粒度进度：executor 向 payload 注入 `_engine_on_execute_unit_done`；orchestrator 每完成一个 slice 回调。

---

## 配置流

```text
EntityBasedPerformance.base()
    + profile_*_config()   # tag/strategy dispatch.yaml
    → resolve_entity_based_performance()
    → planner / executor

SliceBasedPerformance.base()
    + profile_*_calendar_slice_config()
    → resolve_slice_based_performance()
    → SliceBasedPerformance.resolve_for_planning()  # 解析 auto
```

用户 settings **不含** `performance`；业务选项（`dry_run`、`save_batch_size`）在应用层 `run_options` 处理。

---

## 进度

`RunProgressReporter`：prep 5% → plan 10% → execute 80% → finish 5%。

- 始终计算；`enable_progress_display` 仅控制 CMD 日志
- entity：每个 batch 完成 tick execute 段
- slice：orchestrator hook 按 slice 计数

---

## 公开 API 与内部实现

| 公开 | 内部（勿跨模块 import） |
|------|-------------------------|
| `BacktestEngine` | `EntityPlanner`, `SliceExecutor`, … |
| `contracts.*` | `core/entity_based/*`, `core/slice_based/*` |
| `BacktestJob`（`core/shared/jobs.py`） | `ExecutionContext` |

契约细节见根目录 `api.yaml` 与 `glossary.yaml`。

---

## 依赖

- `core.infra.machine_capacity` — CPU/内存预算
- `core.infra.db.core.engines.duckdb.process_pool_scope` — 可选 DuckDB 进程池包装
- Python `concurrent.futures.ProcessPoolExecutor`（entity_based 外层池）

---

## 相关文档

- [OVERVIEW.md](../OVERVIEW.md) — 使用者入门
- [DECISIONS.md](./DECISIONS.md) — 设计决策
- [api.yaml](../api.yaml) — API 契约
