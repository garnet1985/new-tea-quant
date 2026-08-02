# System Actions API 文档

**版本：** `0.2.0`  
**最低支持核心版本：** `>=0.4.2`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。  
> 所列门面入口须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `SystemActions`；类型从 [`contracts.py`](./contracts.py) 导入。实现位于 `cache_cleanup/`、`shortcuts/`（内部）。

---

## SystemActions

**描述：** 系统级操作门面 — `cache` / `pipeline` / `scaffold`

### cache

#### run

`SystemActions.cache.run(*, clear_db_cache=False, clear_backtest_results=False, clear_scan_results=False, clear_userspace_ntq=False) -> dict`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 按勾选项清理；pipeline 忙碌时返回 `error=pipeline_busy`

#### clear_workbench_db / clear_backtest_results / clear_scan_results / clear_strategy_results / clear_userspace_ntq

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 单项清理（devcli / 细粒度调用）

### pipeline

#### read_status

`SystemActions.pipeline.read_status() -> dict`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 返回 idle / busy 租约快照

#### lease

`SystemActions.pipeline.lease(*, kind, job_id, resource_key="", label="", domains=None) -> PipelineLease`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 构造上下文管理器；忙时 `acquire` 抛 `PipelineLeaseBusyError`
- **举例：**

```python
from core.infra.system_actions import SystemActions
from core.infra.system_actions.contracts import PipelineLeaseBusyError

try:
    with SystemActions.pipeline.lease(kind="tag_run", job_id="j1", resource_key="demo"):
        ...
except PipelineLeaseBusyError as exc:
    print(exc.active)
```

### scaffold

#### create_strategy / create_tag

`SystemActions.scaffold.create_strategy(raw_path: str) -> ScaffoldResult`  
`SystemActions.scaffold.create_tag(raw_path: str) -> ScaffoldResult`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 从模板复制并启用；失败抛 `ScaffoldError`

---

## contracts

| 符号 | 说明 |
|------|------|
| `ScaffoldError` / `ScaffoldResult` | 脚手架异常与结果 |
| `PipelineLeaseBusyError` / `PipelineLease` | 租约忙异常与上下文管理器 |
| `VALID_KINDS` | 合法 pipeline kind 集合 |
