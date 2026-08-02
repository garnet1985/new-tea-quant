# Update API 文档

**版本：** `0.5.0`  
**最低支持核心版本：** `>=0.4.1`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。  
> 所列门面入口须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `Update`；类型从 [`contracts.py`](./contracts.py) 导入。  
**边界：** 版本探测与升级编排在 `setup/updater/`，不在本模块。

**CLI：** `python -m core.infra.update.post_upgrade run`（内部调用 `Update.post_upgrade.run`）

---

## Update

**描述：** 升级扩展门面 — `data_scripts` / `post_upgrade`

### data_scripts

#### register / get / list / run

`Update.data_scripts.register(action_id: str, *, description: str = "")` → 装饰器  
`Update.data_scripts.get(action_id: str) -> RegisteredMigrationScript | None`  
`Update.data_scripts.list() -> dict[str, RegisteredMigrationScript]`  
`Update.data_scripts.run(db, action_id: str, *, context: dict | None = None) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`（Facade 封装 `0.5.0`）
- **描述：** DB 迁移数据脚本注册与执行；未注册时 `run` 抛 `KeyError`
- **举例：**

```python
from core.infra.update import Update

@Update.data_scripts.register("demo_backfill", description="demo")
def _demo(db, context: dict) -> None:
    ...

Update.data_scripts.run(db, "demo_backfill")
```

### post_upgrade

#### register / get / list / run

`Update.post_upgrade.register(action_id: str, *, description: str = "")` → 装饰器  
`Update.post_upgrade.get(action_id: str) -> RegisteredPostUpgradeAction | None`  
`Update.post_upgrade.list() -> list[RegisteredPostUpgradeAction]`  
`Update.post_upgrade.run(repo_root: Path, *, context: dict | None = None) -> PostUpgradeRunResult`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`（Facade 封装 `0.5.0`）
- **描述：** 升级收尾动作；注册表为空时 `run` 返回 `skipped=True`

---

## contracts

| 符号 | 说明 |
|------|------|
| `RegisteredMigrationScript` / `MigrationScriptFn` | 数据脚本条目与函数类型 |
| `RegisteredPostUpgradeAction` / `PostUpgradeFn` | 收尾动作条目与函数类型 |
| `PostUpgradeRunResult` | 收尾执行结果 |
