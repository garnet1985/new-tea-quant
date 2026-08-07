# System Actions API 文档

**版本：** `0.2.0`  
**最低支持核心版本：** `>=0.4.2`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。  
> 所列门面入口须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `SystemActions`；类型从 [`contracts.py`](./contracts.py) 导入，或经 `SystemActions.types`。实现位于 [`core/`](./core/)。

---

## SystemActions

**描述：** 系统级操作门面 — `cache` / `pipeline` / `scaffold` / `types`

### cache

#### run

`SystemActions.cache.run(*, clear_db_cache=False, clear_backtest_results=False, clear_scan_results=False, clear_userspace_ntq=False) -> dict`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 按勾选项清理；未选 → `nothing_selected`；pipeline 忙碌 → `pipeline_busy`

#### clear_workbench_db

`SystemActions.cache.clear_workbench_db() -> int`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 清空 workbench 快照表；返回删除行数

#### clear_backtest_results / clear_scan_results

`SystemActions.cache.clear_backtest_results(*, strategy_names=None) -> int`  
`SystemActions.cache.clear_scan_results(*, strategy_names=None) -> int`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 分别删除 `results/simulations/` 与 `results/scan/`；返回删除目录数

#### clear_strategy_results

`SystemActions.cache.clear_strategy_results(*, strategy_names=None) -> int`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 删除整棵 `results/`（**含** simulations + scan）；细粒度请用上面两项

#### clear_userspace_ntq

`SystemActions.cache.clear_userspace_ntq() -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 删除 `userspace/.ntq/`（不触碰仓库根 `.ntq/`）

### pipeline

#### read_status

`SystemActions.pipeline.read_status() -> dict`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 返回 idle / busy 租约快照（文件：`userspace/.ntq/runtime/pipeline_active.json`）

#### lease

`SystemActions.pipeline.lease(*, kind, job_id, resource_key="", label="", domains=None) -> PipelineLease`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 构造上下文管理器；`kind` 须在 `VALID_KINDS`；忙时 `acquire` 抛 `PipelineLeaseBusyError`
- **举例：**

```python
from core.infra.system_actions import SystemActions

try:
    with SystemActions.pipeline.lease(kind="tag_run", job_id="j1", resource_key="demo"):
        ...
except SystemActions.types.PipelineLeaseBusyError as exc:
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

### types

**描述：** 与 `contracts` 同源（`Kind`、`VALID_KINDS`、`ScaffoldError`、`ScaffoldResult`、`PipelineLeaseBusyError`；`PipelineLease` 懒加载）

---

## contracts

| 符号 | 说明 |
|------|------|
| `ScaffoldError` / `ScaffoldResult` | 脚手架异常与结果 |
| `PipelineLeaseBusyError` / `PipelineLease` | 租约忙异常与上下文管理器（后者懒加载） |
| `VALID_KINDS` / `Kind` | 合法 pipeline kind |
