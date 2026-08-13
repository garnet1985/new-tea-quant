# 测试用例 — `infra.db` / `core/migration`

**覆盖版本：** `0.5.0`  
**本文件位置：** `core/migration/__test__/`

## Scope

schema 迁移管线：history、plan prune、migrate_manager CLI runner。

## 边界

**负责：** migration 子包行为与 migrate_manager 门面 CLI  
**不负责：** updater 子进程编排（见 `setup/core/updater/__test__`）

| Case 文件 | 说明 |
|-----------|------|
| `test_migration_runner.py` | migrate_manager CLI |
| `test_migration_history.py` | 迁移历史 |
| `test_plan_prune.py` | plan 剪枝 |
