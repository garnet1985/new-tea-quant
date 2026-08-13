# Updater 架构文档

**版本：** `0.1.0`

## 模块介绍

`infra.updater` 拥有应用升级：编排源码（`core/orchestrator/`）、数据迁移脚本注册表、post-upgrade 收尾。

**运行时**必须在 `userspace/system/updater/`（由 `Updater.runtime.sync_orchestrator` 写入）。`core/` 在 `managed_scope` 内，升级镜像时会被覆盖，不能从 core 跑流水线。

**不负责：** 首次安装、安装 wizard、`needs_install`（均在 `infra.setup`）。

## 架构

```text
Updater
  ├── data_scripts  → core/db/registry
  ├── post_upgrade  → core/post_upgrade/registry + runner
  ├── runtime       → core/orchestrator_sync.sync_orchestrator
  └── types         → contracts
```

```text
cli.py u ──► userspace/system/updater (拷贝)
devcli pu ──► Updater.runtime.sync_orchestrator ──► Setup.artifacts.package_userspace
userspace updater ──subprocess──► python -m core.infra.updater.core.post_upgrade run
infra.db plan_executor ─────► Updater.data_scripts.run
```

```text
core/infra/updater/
├── updater.py / contracts.py
├── core/
│   ├── db/
│   ├── post_upgrade/
│   ├── orchestrator/
│   └── orchestrator_sync.py
└── __test__/
```

## 相关文档

- [DESIGN.md](./DESIGN.md)
- [API.md](../API.md)
