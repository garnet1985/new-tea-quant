# Data Contract 模块单元测试

**版本：** 0.5.0 · **用例注册表：** [`test_cases.yaml`](test_cases.yaml)

本目录覆盖 **`DataContracts` Facade**、**`IssueResult` / 句柄形态**、**mapping 完整性** 与 **Tag entity_type** 映射。默认 **不连 DB**（mock loader 或 `cache_enabled=False` + `should_load_initially=False`）。

---

## 测试文件概览

| 文件 | 用例数 | 说明 |
| --- | ---: | --- |
| `test_api.py` | 9 | Facade API 契约（`api.yaml` 0.5.0） |
| `test_data_contract_smoke.py` | 5 | GLOBAL / PER_ENTITY issue 形态、until |
| `test_mapping_completeness.py` | 1 | `DataKey` ↔ `default_map` 全覆盖 |
| `test_tag_entity_type.py` | 6 | `resolve_tag_entity_type`（5 组 parametrize + 1 异常） |
| （已迁）`core/bff/APIs/data/contracts/helpers/__test__/` | 3 | BFF catalog 分页与 summary |

**合计：** 模块 `__test__` 21；catalog 测在 BFF helpers

---

## 按主题分类

| 主题 | 覆盖内容 | 主要文件 |
| --- | --- | --- |
| **Facade / cache** | 黑盒 cache 默认开启；PER_ENTITY 不可 cache override | `test_api.py` |
| **issue / load** | `should_load_initially`、显式 `load(issued)` | `test_api.py`, smoke |
| **until / 时间** | PIT 前缀、`get_*_time`、reset | `test_api.py`, smoke |
| **句柄 / loader** | Contract 子类、loader 类型、loader_params | smoke |
| **注册表** | 新增 `DataKey` 必须进 `default_map` | `test_mapping_completeness.py` |
| **Tag 集成** | DataKey → BFF entity_type | `test_tag_entity_type.py` |
| **Workbench BFF** | catalog 列表字段与分页 | `test_contract_catalog.py` |

---

## 运行

```bash
# 模块全部（推荐）
python3 -m pytest core/modules/data_contract/__test__/ -q

# BFF catalog
python3 -m pytest core/bff/APIs/data/contracts/helpers/__test__/ -q

# 单文件
python3 -m pytest core/modules/data_contract/__test__/test_api.py -q

# 单用例
python3 -m pytest core/modules/data_contract/__test__/test_api.py::test_load_after_issue -q
```

---

## 夹具与约定

- **`_reset_cache`（autouse）**：每个用例前后 `reset_shared_contract_cache()`，避免 GLOBAL cache 串用例。
- **`dcm` fixture**：`DataContracts(cache_enabled=False)`，便于断言 `has_cache` 与避免触库。
- **无 pandas 环境**：smoke / mapping 用例在 import 前注入占位 `pandas` 模块，loader 导入不失败。

---

## 新增用例 checklist

1. 在对应 `test_*.py` 增加 `test_*` 函数。
2. 同步更新 [`test_cases.yaml`](test_cases.yaml) 的 `scenarios`（`name` 与函数名一致）。
3. 若涉及新 **公开** Facade 行为，先更新 [`api.yaml`](../api.yaml) 再写测试。
4. 新增 **`DataKey`** 枚举时，`test_mapping_completeness` 应仍通过（或同步补 `default_map`）。

---

## 相关文档

- [api.yaml](../api.yaml) — 公开 API 契约
- [OVERVIEW.md](../OVERVIEW.md) — 使用概览
- [docs/DECISIONS.md](../docs/DECISIONS.md) — 缓存与 issue/load 决策
