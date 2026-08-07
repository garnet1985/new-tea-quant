# 测试用例 — `infra.export_import`（模块根）

**模块：** `infra.export_import`  
**覆盖版本：** `0.3.0`  
**本文件位置：** `__test__/`

---

## Scope

验证门面 `ExportImport` 与 `contracts` / `types`（`test_api.py`）。  
打包 / 安装行为单测在 `core/__test__/`。

## 边界

**负责**

- 包根仅导出 `ExportImport`
- `archive` / `install` / `types` 公开行为抽检

**不负责**

- strategy 业务编排（见 `core/modules/strategy/.../package`）

**允许的测试类型（本目录）：** `api`

---

## Scenario：facade_api

| Case | 文件 | 说明 |
|------|------|------|
| `test_facade_export` | `test_api.py` | `__all__` + 三命名空间 |
| `test_contracts_symbols` | `test_api.py` | contracts ≡ types |
| `test_conflict_policy_values` | `test_api.py` | 三策略枚举 |
| `test_archive_install_round_trip_smoke` | `test_api.py` | create → install 抽检 |
| `test_preflight_accepts_manifest` | `test_api.py` | preflight(manifest) |
