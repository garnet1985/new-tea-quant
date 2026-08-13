# Task Guard API 文档

**版本：** `0.2.0`  
**最低支持核心版本：** `>=0.4.2`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `TaskGuard`；类型从 [`contracts.py`](./contracts.py) 导入，或经 `TaskGuard.types`。实现位于 [`core/`](./core/)。

---

## TaskGuard

**描述：** 长任务互斥守卫（忙闲查询 + 租约）

### read_status

`TaskGuard.read_status() -> dict`

- **类型：** `static`
- **状态：** `beta`
- **描述：** 返回 idle / busy 快照（文件：`userspace/.ntq/runtime/task_guard_active.json`）

### lease

`TaskGuard.lease(*, kind, job_id, resource_key="", label="", domains=None) -> TaskLease`

- **类型：** `static`
- **状态：** `beta`
- **描述：** 构造上下文管理器；`kind` 须在 `VALID_KINDS`；忙时 `acquire` 抛 `TaskLeaseBusyError`
- **举例：**

```python
from core.infra.task_guard import TaskGuard

try:
    with TaskGuard.lease(kind="tag_run", job_id="j1", resource_key="demo"):
        ...
except TaskGuard.types.TaskLeaseBusyError as exc:
    print(exc.active)
```

### types

**描述：** 与 `contracts` 同源（`VALID_KINDS`、`TaskLeaseBusyError`；`TaskLease` 懒加载）

---

## contracts

| 符号 | 说明 |
|------|------|
| `TaskLeaseBusyError` / `TaskLease` | 租约忙异常与上下文管理器（后者懒加载） |
| `VALID_KINDS` | 合法 kind：`tag_run` / `strategy_scan` / `strategy_run` / `data_renew` |
