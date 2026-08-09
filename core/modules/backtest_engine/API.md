# Backtest Engine API 文档

**版本：** `0.4.0`  
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
| `JobContext` | 单次 task 作用域 |
| `RunCallbacks` | `on_tick` / `on_before_task_start` / `on_task_result` 等 |
| `RunProgress` / `JobReport` | 进度与单 job 报告 |
| `Timeline` / `TimelineInput` | 日历轴发布与读取 |

Job 校验：`BacktestJob.validate_many(jobs, mode=...)` — entity_based 需 `entity_specified`；slice_based 需 `entity_ids` + `timeline_point_count`。
