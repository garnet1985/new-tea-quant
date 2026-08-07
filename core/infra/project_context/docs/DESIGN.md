# Project Context 详细设计

**版本：** `0.5.0`

实现向行为；总览见 [架构文档](./ARCHITECTURE.md)。

---

## 1. Facade + namespace

- **`ProjectContext`：** 静态 namespace 容器，无实例状态。
- **内部 Manager：** `PathManager`、`ConfigManager`、`DiscoveryManager` 不对外导出。
- **人读契约：** 根目录 `API.md`；跨模块类型在 `contracts.py` 或 `ProjectContext.types`。

### 决策摘要

| 决策 | 选择 | 理由 |
|------|------|------|
| 入口 | 仅 `ProjectContext` | 防止多入口与命名漂移 |
| 路径类型 | `pathlib.Path` | 跨平台、可组合 |
| 配置缺失 | `load_core_config` → `{}`；overridable 两侧皆无 → 抛错 | 可选配置温和失败；强依赖可覆盖配置须显式失败 |
| 稳定性标记 | 公开 API 最高 `beta`（core `0.x`） | 与 CORE_MODULE_STANDARDS 一致 |
| 契约载体 | `API.md` + `test_api.py`（不再维护 `api.yaml`） | 人读 SSOT |
| 文件发现 | `find_in_tree` 在 `infra.discovery` | 通用 IO 与项目上下文解耦 |

---

## 2. 路径

- **项目根：** 自包路径向上查找根标记（`.git`、`pyproject.toml` 等），命中后缓存；否则 fallback 父链。
- **userspace 优先级：** `NEW_TEA_QUANT_USERSPACE_ROOT` → `NTQ_USERSPACE_ROOT` → `{project_root}/.ntq/userspace-path.json` → `{project_root}/userspace`。
- **策略根：** `coerce_strategy_folder` — 绝对 discovered folder 原样返回；相对 id 拼到 `userspace/strategies/`。
- **命名：** `get_xxx_root` / `get_xxx_directory` / `get_xxx_path`；仿真目录用 `get_strategy_simulation_{price,portfolio,enum}_directory`；Tag 门面用 `get_tag_directory`。
- **备份数据：** `get_backup_data_directory` → `userspace/system/backup/data/`。

---

## 3. 配置加载

- **`load_core_config`：** 委托 `DiscoveryManager.load_overridable_config("", name)`；缺文件返回空 dict。
- **`load_database_config`：** 合并 `database/common` + `database/{type}` + userspace + `DB_*` env。
- **`load_data_config` / 访问器：** 读合并后的 `data.json` 字段（含 `get_decimal_places`、`get_adj_factor_event_decimal_places`、`get_database_type`）。
- **`merge_market_profile_dicts`：** 市场 profile 规则深度合并；供 discovery `merge_fn` 使用。

---

## 4. 配置发现

- **`discover_configs(domain)`：** core ∪ userspace 下 id 并集排序。
- **`load_overridable_config`：** 默认 `ConfigManager.load_with_defaults`；可注入自定义 `merge_fn`。
- **`OverridableConfigNotFoundError` / `DiscoveredConfig`：** 定义于 `contracts`，经 `ProjectContext.types` 挂载。

---

## 5. 测试

- **`__test__/test_api.py`：** 公开 Facade / contracts 契约 smoke（`force_run`）。
- **`core/__test__/`：** 内部 Manager 行为测试（PathManager、ConfigManager、DiscoveryManager 等）。

---

## 相关文档

- [架构总览](./ARCHITECTURE.md)
- [API](../API.md)
