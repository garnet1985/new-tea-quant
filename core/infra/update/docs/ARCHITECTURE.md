# Update 架构文档

**版本：** `0.5.0`

## 模块介绍

`infra.update` 提供升级**扩展点**：数据迁移脚本注册表（供 `infra.db` 执行器调用）与 post-upgrade 收尾（供 `setup/updater` 子进程调用）。

**不负责：** 版本探测、下载、managed_scope 镜像、schema 快照编排（均在 `setup/updater/`）。

## 架构

```text
Update
  ├── data_scripts  → db/registry
  └── post_upgrade  → post_upgrade/registry + runner
contracts           → Registered* / PostUpgradeRunResult

setup/updater ──subprocess──► python -m core.infra.update.post_upgrade run
infra.db plan_executor ─────► Update.data_scripts.run
```

## 相关文档

- [DESIGN.md](./DESIGN.md)
- [API.md](../API.md)
