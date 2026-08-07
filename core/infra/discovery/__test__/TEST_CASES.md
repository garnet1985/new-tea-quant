# 测试用例 — `infra.discovery`（模块根）

**模块：** `infra.discovery`  
**覆盖版本：** `0.4.0`  
**本文件位置：** `__test__/`

---

## Scope

验证门面 `Discovery` 与 `contracts`（`test_api.py`）。  
包内实现单测在 `core/__test__/`（不必在本文件逐条索引）。

## 边界

**负责**

- 包根仅导出 `Discovery`
- `Discovery.file` / `discover` / `class_discovery` 公开行为
- `contracts` 类型面

**不负责**

- 包内实现细节（见 `core/__test__/`）
- 业务扩展目录内容正确性

**允许的测试类型（本目录）：** `api`

---

## Scenario：facade_api

| Case | 文件 | 说明 |
|------|------|------|
| `test_facade_export` | `test_api.py` | `__all__` + 三 namespace |
| `test_contracts_symbols` | `test_api.py` | contracts 类型 |
| `test_file_*` | `test_api.py` | find / load / save |
| `test_discover_files*` / directories | `test_api.py` | 批量路径 |
| `test_discover_subclasses_behavior` | `test_api.py` | 临时包扫子类 |
| `test_discover_objects_behavior` | `test_api.py` | 临时包扫对象 |
| `test_discover_class_by_path_behavior` | `test_api.py` | 定点加载 |
| `test_files_by_suffix_requires_dot` | `test_api.py` | suffix 契约 |
| `TestEdgeCases.*` | `test_api.py` | 空目录 / 嵌套 / max_depth |
