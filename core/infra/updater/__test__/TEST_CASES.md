# 测试用例 — `infra.updater`（模块根）

**模块：** `infra.updater`  
**覆盖版本：** `0.5.0`  
**本文件位置：** `__test__/`

---

## Scope

验证门面 `Updater` 与 `contracts` / `types`（`test_api.py`）。  
post-upgrade 执行顺序在 `core/post_upgrade/__test__/`。编排在 `core/orchestrator/__test__/`。

## 边界

**负责：** 公开 namespace API  
**不负责：** 编排细节（见 `core/orchestrator/__test__/`）

**允许的测试类型（本目录）：** `api`

---

## Scenario：facade_api

| Case | 文件 | 说明 |
|------|------|------|
| `test_facade_export` | `test_api.py` | `__all__` + namespaces |
| `test_types` | `test_api.py` | types ≡ contracts |
| `test_post_upgrade_run_skips_when_empty` | `test_api.py` | 空表 skip |
| `test_data_scripts_register_and_get` | `test_api.py` | 注册/查询（测后 clear） |
