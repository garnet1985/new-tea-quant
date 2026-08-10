# Update 架构文档

**版本：** `0.1.0`

## 模块介绍

`infra.update` 提供升级**扩展点**：数据迁移脚本注册表（供 `infra.db` 执行器调用）与 post-upgrade 收尾（供 `setup/updater` 子进程调用）。

**不负责：** 版本探测、下载、managed_scope 镜像、schema 快照编排（均在 `setup/updater/`）。

## 架构

```text
Update
  ├── data_scripts  → core/db/registry
  ├── post_upgrade  → core/post_upgrade/registry + runner
  └── types         → contracts
```

```text
setup/updater ──subprocess──► python -m core.infra.update.core.post_upgrade run
infra.db plan_executor ─────► Update.data_scripts.run
```

```text
core/infra/update/
├── update.py / contracts.py
├── core/
│   ├── db/
│   └── post_upgrade/   # + actions/ + __main__.py + __test__/
└── __test__/
```

## 相关文档

- [DESIGN.md](./DESIGN.md)
- [API.md](../API.md)
