# 测试用例 — `setup/updater`

**覆盖版本：** 与 updater 行为同步（非 infra.update 模块版本）  
**本文件位置：** `setup/updater/__test__/`

## Scope

升级编排、下载 URL、交互入口、清理与迁移子进程调用。

## 边界

**负责：** `setup/updater/*`  
**不负责：** `infra.update` 注册表本身（见 `core/infra/update/__test__/`）

| Case 文件 | 说明 |
|-----------|------|
| `test_updater_migration_spawn.py` | 缺快照 / 环境变量放行 |
| `test_upgrade_entry.py` | 交互升级入口 |
| `test_upgrade_cleanup.py` | 升级清理 helper |
| `test_updater_download_urls.py` | 下载 URL 构造 |
