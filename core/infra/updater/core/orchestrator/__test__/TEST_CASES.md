# 测试用例 — `infra.updater` orchestrator

**模块：** `infra.updater`  
**本文件位置：** `core/infra/updater/core/orchestrator/__test__/`

## Scope

升级编排、下载 URL、清理与迁移子进程调用。

## 边界

**负责：** `core/orchestrator/*`  
**不负责：** 门面注册表（见模块根 `__test__/`）

| Case 文件 | 说明 |
|-----------|------|
| `test_updater_migration_spawn.py` | 缺快照 / 环境变量放行 |
| `test_upgrade_cleanup.py` | 升级清理 helper |
| `test_updater_download_urls.py` | 下载 URL 构造 |
