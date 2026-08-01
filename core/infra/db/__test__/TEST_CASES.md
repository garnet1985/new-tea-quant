# 测试用例 — `infra.db`

**模块：** `infra.db`  
**覆盖版本：** `0.4.0`  
**本文件位置：** `__test__/`

---

## Scope

验证门面 `Db`、`contracts` 导出，以及（存量）包根过渡 re-export。实现向单测仍在本目录各 `test_*.py`（后续可下沉到 `core/**/__test__/`）。

## 边界

**负责**

- `Db.manager` / `migration` / `duckdb` 可调用
- `contracts` 关键符号存在
- 过渡期 `from core.infra.db import DatabaseManager` 仍可用

**不负责**

- 完整引擎 / 迁移行为（见各专题 `test_*.py`）
- 外部模块业务正确性

**允许的测试类型（本目录）：** `api` · 存量实现单测

---

## Scenario：facade_and_contracts

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_facade_exported` | `test_api.py` | `Db` 在 `__all__`，三 namespace齐全 |
| `test_manager_namespace` | `test_api.py` | manager 方法可调用 |
| `test_migration_namespace` | `test_api.py` | migration 转发 |
| `test_duckdb_namespace` | `test_api.py` | process_pool 模块可取 |
| `test_contracts_symbols` | `test_api.py` | contracts 符号 |
| `test_transitional_package_reexports` | `test_api.py` | 包根过渡导出 |
