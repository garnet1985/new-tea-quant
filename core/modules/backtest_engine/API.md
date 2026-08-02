# Backtest Engine API 文档

**版本：** `0.4.0`  
**最低支持核心版本：** `>=0.4.0`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `BacktestEngine`；类型从 [`contracts.py`](./contracts.py) 导入。

---

## BacktestEngine

**描述：** 回测 Facade（entity_based / slice_based 调度）

### run

`BacktestEngine.run(mode, jobs, execute_fn=None, *, performance=None, task_name="", callbacks=None, enable_progress_display=True, ...)`

- **类型：** `class`
- **状态：** `beta`
- **描述：** 统一入口，按 mode 分发

### entity_based.run / slice_based.run

- **类型：** `static`
- **状态：** `beta`
- **描述：** 各模式 probe → plan → execute → monitor

**参数（keyword_only）：**

| 名 | 类型 | 说明 |
|----|------|------|
| `performance` | `Optional[dict]` | 应用方 dispatch 配置 |
| `task_name` | `str` | 展示/追踪名 |
| `callbacks` | `Optional[RunCallbacks]` | 钩子集合 |
| `enable_progress_display` | `bool` | CMD 进度输出 |

**返回：** `BacktestEngine.RunResult`

**举例：**

```python
from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import JobContext, RunCallbacks

def execute_fn(ctx: JobContext) -> dict:
    return {"success": True}

result = BacktestEngine.entity_based.run(
    [{"id": "j1", "payload": {"entity_specified": [{"id": "000001.SZ"}]}}],
    execute_fn=execute_fn,
    callbacks=RunCallbacks(on_task_result=lambda r, p: None),
)
```

---

## contracts

| 符号 | 说明 |
|------|------|
| `BacktestJob` | job dataclass（id + payload） |
| `JobContext` | 单次 job 执行上下文 |
| `RunCallbacks` | on_task_result / on_release / on_tick 等 |
| `RunProgress` / `JobReport` | 进度与结果报告 |
| `Timeline` | 日历推进辅助（slice 路径） |

Job 校验规则见 `BacktestJob.validate_many(jobs, mode=...)`：entity_based 需 `entity_specified`；slice_based 需 `entity_ids` + `timeline_point_count`。
