# Updater API 文档

**版本：** `0.1.0`  
**最低支持核心版本：** `>=0.4.1`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。  
> 所列门面入口须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `Updater`；类型从 [`contracts.py`](./contracts.py) 导入，或经 `Updater.types`。实现位于 [`core/`](./core/)。  
**边界：** 升级流水线在运行时 `userspace/system/updater/` 执行（源码 `core/orchestrator/`）。本门面提供扩展点与 `runtime.sync_orchestrator`，不提供 `Updater.upgrade.run()`。

**CLI：** `python -m core.infra.updater.core.post_upgrade run`（内部调用 `Updater.post_upgrade.run`）

---

## Updater

**描述：** 升级门面 — `data_scripts` / `post_upgrade` / `runtime` / `types`

### data_scripts

#### register / get / list / run

`Updater.data_scripts.register(action_id: str, *, description: str = "")` → 装饰器  
`Updater.data_scripts.get(action_id: str) -> RegisteredMigrationScript | None`  
`Updater.data_scripts.list() -> dict[str, RegisteredMigrationScript]`  
`Updater.data_scripts.run(db, action_id: str, *, context: dict | None = None) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`（Facade 封装 `0.5.0`）
- **描述：** DB 迁移数据脚本注册与执行；未注册时 `run` 抛 `KeyError`
- **举例：**

```python
from core.infra.updater import Updater

@Updater.data_scripts.register("demo_backfill", description="demo")
def _demo(db, context: dict) -> None:
    ...

Updater.data_scripts.run(db, "demo_backfill")
```

### post_upgrade

#### register / get / list / run

`Updater.post_upgrade.register(action_id: str, *, description: str = "")` → 装饰器  
`Updater.post_upgrade.get(action_id: str) -> RegisteredPostUpgradeAction | None`  
`Updater.post_upgrade.list() -> list[RegisteredPostUpgradeAction]`  
`Updater.post_upgrade.run(repo_root: Path, *, context: dict | None = None) -> PostUpgradeRunResult`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`（Facade 封装 `0.5.0`）
- **描述：** 升级收尾动作；内置 `sync_userspace_updater`。测试清空注册表且不加载内置时 `run` 返回 `skipped=True`

### runtime

#### sync_orchestrator

`Updater.runtime.sync_orchestrator(dest: Path) -> list[str]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 将 `core/orchestrator/` 运行时文件拷到 `dest`（通常 `userspace/system/updater`）。不含 `__test__`。

### types

**描述：** `RegisteredMigrationScript` / `RegisteredPostUpgradeAction` / `PostUpgradeRunResult` / `MigrationScriptFn` / `PostUpgradeFn`

---

## contracts

| 符号 | 说明 |
|------|------|
| `RegisteredMigrationScript` / `MigrationScriptFn` | 数据脚本条目与函数类型 |
| `RegisteredPostUpgradeAction` / `PostUpgradeFn` | 收尾动作条目与函数类型 |
| `PostUpgradeRunResult` | 收尾执行结果 |
