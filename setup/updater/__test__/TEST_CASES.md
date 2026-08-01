# 测试用例 — `setup/updater`

**覆盖版本：** 与 updater 行为同步（非 infra.db 模块版本）  
**本文件位置：** `setup/updater/__test__/`

## Scope

updater 子进程调用数据库迁移 CLI 的行为。

## 边界

**负责：** `setup/updater/helper.spawn_database_migration_cli` 等  
**不负责：** `infra.db` 迁移算法本身

| Case 文件 | 说明 |
|-----------|------|
| `test_updater_migration_spawn.py` | 缺快照 / 环境变量放行 |
