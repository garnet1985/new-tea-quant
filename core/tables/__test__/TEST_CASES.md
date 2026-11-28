# Tables — 测试用例索引

**模块：** `tables` · **版本：** `0.4.3`

**最低支持核心版本：** `>=0.5.0`

**路径：** `core/tables/__test__/`

## Scope

本 suite 断言**表定义契约**（schema/model 成对、命名、`sys_` 前缀、必需键）。不负责 `DataManager` 全流程集成（见 `modules.data_manager`）。

## 负责

- 全库 `core/tables/**/schema.py` 静态契约
- 包内领域单测（adj_factor、st_period_rules 等）由各子目录 `__test__` 维护

## 不负责

- infra.db 引擎行为
- renew / BFF 端到端

---

## Scenario：表定义契约（API.md）

| Case | 文件 | 说明 |
|------|------|------|
| `test_every_schema_has_model_pair` | `test_api.py` | 每个 schema.py 同级有 model.py |
| `test_schema_required_keys_and_sys_prefix` | `test_api.py` | 必需键与 name 以 sys_ 开头 |
| `test_each_model_defines_db_base_subclass` | `test_api.py` | model.py 含 DbBaseModel 子类 |
| `test_glossary_version_matches_module_info` | `test_api.py` | glossary 头注释版本一致 |

---

## Scenario：领域单测（子包）

| Case | 文件 | 说明 |
|------|------|------|
| （见 `stock/adj_factor_events/__test__/` 等） | 各子目录 | 表领域逻辑单元测试 |