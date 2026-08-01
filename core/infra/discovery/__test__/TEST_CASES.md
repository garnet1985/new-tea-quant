# 测试用例 — `infra.discovery`

**模块：** `infra.discovery`  
**覆盖版本：** `0.4.0`  
**本文件位置：** `__test__/`

---

## Scope

验证门面 `Discovery` 与公开 namespace 行为（对齐根目录 `API.md`）；以及类/模块发现内部单测。

## 边界

**负责**

- `Discovery.file` / `discover` / `class_discovery` 可调用与核心行为
- `contracts` 类型可导入

**不负责**

- 业务扩展目录内容正确性（Provider / Strategy 业务）

**允许的测试类型：** `api` · 包内单测（本目录）

---

## Scenario：facade_api（`test_api.py`）

| Case | 说明 |
|------|------|
| `test_facade_export` | 三 namespace存在；`__all__ == ["Discovery"]` |
| `test_contracts_symbols` | contracts 类型可导入 |
| `test_file_namespace_methods` | file 方法齐全 |
| `test_discover_namespace_methods` | discover 方法齐全 |
| `test_class_discovery_namespace_methods` | class_discovery 方法齐全 |
| `test_file_find_file_*` / `load_*` / `save_*` | 文件 API 行为 |
| `test_discover_files` / `directories` / `files_by_suffix` | 批量路径发现 |
| `test_discover_subclasses` / `objects` / `create_config` / `discover_class_by_path` | 可调用性 |
| `TestEdgeCases.*` | 空目录 / 嵌套 / max_depth |

## Scenario：class_discovery（`test_class_discovery.py`）

内部 `ClassDiscovery` 扫描与过滤。

## Scenario：module_discovery（`test_module_discovery.py`）

内部 `ModuleDiscovery.discover_objects`。
