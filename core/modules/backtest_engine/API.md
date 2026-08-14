# Backtest Engine API 文档

**版本：** `0.2.0`  
**最低支持核心版本：** `>=0.4.0`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `BacktestEngine`；类型从 [`contracts.py`](./contracts.py) 导入。实现位于 `core/`，禁止 deep-import。

---

## BacktestEngine

**描述：** 回测 Facade（entity_based / slice_based 调度）。业务逻辑经 `RunCallbacks` 注入；引擎内置 worker（`TimelineWorkerExecute` / `SliceWorkerExecute`），**不接受**外部 `execute_fn` 参数。

### set_timeline / clear_timeline

`BacktestEngine.set_timeline(timeline=None, *, start="", end="")`  
`BacktestEngine.clear_timeline()`

- **状态：** `beta`
- **描述：** 在 `run` / 探针前注入或清除 simulation window（及可选 points 覆盖）

### run

`BacktestEngine.run(mode, jobs, *, start="", end="", timeline=None, performance=None, task_name="", callbacks=None, enable_progress_display=True) -> RunResult`

- **状态：** `beta`
- **描述：** 统一入口；`mode` 为 `"entity_based"` / `"slice_based"` 或 `BacktestEngine.Mode`

### entity_based.run / slice_based.run

同 `run` 的 keyword 参数（无 `mode`），各自走 probe → plan → execute → monitor。

**参数：**

| 名 | 类型 | 说明 |
|----|------|------|
| `jobs` | `list[dict]` | `{"id", "payload"}`；空列表直接成功返回 |
| `start` / `end` | `str` | simulation window（YYYYMMDD）；有 jobs 时须就绪 |
| `timeline` | `list[str] \| None` | 可选开市日 points 覆盖 |
| `performance` | `Optional[dict]` | 应用方 dispatch 配置（merge engine base） |
| `task_name` | `str` | 展示/追踪名 |
| `callbacks` | `Optional[RunCallbacks]` | 生命周期钩子（含可选 `on_tick`） |
| `enable_progress_display` | `bool` | 是否打 CMD 进度日志 |

**返回：** `BacktestEngine.RunResult`

**举例：**

```python
from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import JobContext, RunCallbacks

def on_tick(ctx: JobContext, point: str, index: int) -> None:
    ...  # 业务按日推进

result = BacktestEngine.entity_based.run(
    [{"id": "j1", "payload": {"entity_specified": [{"id": "000001.SZ"}]}}],
    start="20240102",
    end="20240103",
    timeline=["20240102", "20240103"],
    task_name="demo",
    callbacks=RunCallbacks(on_tick=on_tick),
)
```

---

## contracts

| 符号 | 说明 |
|------|------|
| `BacktestJob` / `BacktestMode` | job 契约与模式枚举 |
| `JobContext` | 当前 task 作用域 |
| `RunCallbacks` | 见下节「RunCallbacks 生命周期」 |
| `LoadPerEntityWindowFn` | slice 按窗装数回调类型（数据面，非生命周期） |
| `RunProgress` / `JobReport` | 主进程收包进度与单 task/job 报告 |
| `Timeline` / `TimelineInput` | 日历轴发布与读取 |
| `EntityMonitorStats` / `WorkerTaskPerf` | 调度监控与 worker 性能快照类型 |
| `ENGINE_PERF_KEY` / `ENUM_PERF_KEY` | performance.json 键名常量 |

Job 校验：`BacktestJob.validate_many(jobs, mode=...)` — entity_based 需 `entity_specified`；slice_based 需 `entity_ids` + `timeline_point_count`。

**依赖说明：** slice_based 探针/预读装数由调用方经 `RunCallbacks.load_per_entity_window` 注入（如 strategy/tag 的 `JobBundleLoader.load_per_entity_window`）；BE 不依赖 `modules.strategy`。

### RunCallbacks 生命周期

BE **只提供时间点**；钩子名不暗示业务动作（settle / flush / 进度等）。业务在钩子内自行安排。

**Task** = run 内的 partial work（不是整个 run）。寄生主体：

| 模式 | Task 寄生主体 | `on_task_start` / `on_task_complete` |
|------|---------------|--------------------------------------|
| `entity_based` | 一个 worker 进程内的一次 ProcessPool 提交 | 每次提交各 1 次 |
| `slice_based` | 一片正式日历 slice 的 compute | 每片各 1 次 |

| 字段 | 哪边 | 何时 |
|------|------|------|
| `on_before_all_tasks_start` | 主 | plan 后、开跑前 |
| `on_task_start` | task 侧 | 该 task 开始前 |
| `on_tick` | task 侧 | 日历点推进 |
| `on_task_complete` | task 侧 | 该 task 结束后；可返回 `dict` 并入结果 |
| `on_receive_task_result` | 主 | 主进程收到**跨进程** task 结果后（entity）；slice 同进程默认**不调用** |
| `on_after_all_tasks_complete` | 主 | 全部 task 结束 |
| `load_per_entity_window` | 数据面 | slice 装数（非生命周期） |

```python
from core.modules.backtest_engine.contracts import JobContext, RunCallbacks

class DemoHooks:
    @classmethod
    def on_task_start(cls, ctx: JobContext):
        return {}

    @classmethod
    def on_tick(cls, ctx: JobContext, point: str, index: int) -> None:
        ...

    @classmethod
    def on_task_complete(cls, ctx: JobContext):
        return None

callbacks = RunCallbacks(
    on_task_start=DemoHooks.on_task_start,
    on_tick=DemoHooks.on_tick,
    on_task_complete=DemoHooks.on_task_complete,
)
```

---

## BacktestEngine.Performance

**状态：** `beta`  
**描述：** worker.json `job_pipeline` profile 与 performance 字典解析（跨模块入口；禁止 deep-import `core.performance`）。

| 符号 | 说明 |
|------|------|
| `Profiles` | profile id 常量（含 `TAG` / `ENUMERATOR` 等） |
| `resolve_entity_based(performance=None)` | 校验/补全 entity_based performance |
| `resolve_slice_based(performance=None)` | 校验/补全 slice_based performance |
| `resolve_entity_based_for_profile(worker_id, override=None)` | 按 profile 合并后再 resolve |
| `calendar_slice_config(worker_id)` | 该 profile 的 calendar-slice 默认 performance 片段 |

```python
from core.modules.backtest_engine import BacktestEngine

perf = BacktestEngine.Performance
performance = perf.resolve_entity_based_for_profile(perf.Profiles.TAG)
```
