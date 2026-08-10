# Project Context API 文档

**版本：** `0.5.0`  
**最低支持核心版本：** `>=0.4.0`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。  
> 所列门面入口须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `ProjectContext`；异常 / 常量 / 合并函数从 [`contracts.py`](./contracts.py) 导入。实现位于 [`core/`](./core/)。

---

## ProjectContext

**描述：** 项目上下文门面（Facade）— `path` / `config` / `meta` / `cache` / `discovery` / `types` 命名空间

### path

**描述：** 项目根、userspace 与语义目录路径（返回 `pathlib.Path`）

#### get_project_root

`ProjectContext.path.get_project_root() -> Path`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 推断并缓存项目根目录

#### get_core_root / get_userspace_root

`ProjectContext.path.get_core_root() -> Path`  
`ProjectContext.path.get_userspace_root() -> Path`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** `core/`；userspace（优先级：`NEW_TEA_QUANT_USERSPACE_ROOT` → `NTQ_USERSPACE_ROOT` → `{project_root}/.ntq/userspace-path.json` → `{project_root}/userspace`）

#### coerce_strategy_folder

`ProjectContext.path.coerce_strategy_folder(strategy_folder_or_rel: str | Path) -> Path`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.5.0`
- **描述：** 绝对 discovered folder 原样返回；相对 id 拼到 `userspace/strategies/`

#### get_backup_data_directory

`ProjectContext.path.get_backup_data_directory() -> Path`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.5.0`
- **描述：** `userspace/system/backup/data/`

#### get_strategies_root / get_tags_root

`ProjectContext.path.get_strategies_root() -> Path`  
`ProjectContext.path.get_tags_root() -> Path`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.3.0`
- **描述：** `userspace/strategies/`；`userspace/extensions/tags/`

#### get_strategy_directory / get_tag_directory

`ProjectContext.path.get_strategy_directory(strategy_name: str) -> Path`  
`ProjectContext.path.get_tag_directory(tag_name: str) -> Path`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.3.0`
- **描述：** 指定策略 / Tag scenario 目录（Tag 用 `get_tag_directory`）

#### 策略仿真与扫描路径

`ProjectContext.path.get_strategy_simulation_price_directory(strategy_name) -> Path`  
`ProjectContext.path.get_strategy_simulation_portfolio_directory(strategy_name) -> Path`  
`ProjectContext.path.get_strategy_simulation_enum_directory(strategy_name) -> Path`  
`ProjectContext.path.get_strategy_scan_results_directory(strategy_name) -> Path`

- **类型：** `static`
- **状态：** `beta`
- **描述：** 策略仿真与扫描结果目录（PathManager 规范命名）

#### 其他 path 辅助

同命名空间还提供系统库、备份、tmp、data_source / data_contract、策略仿真与扫描结果等路径构造（见 `core/namespaces.py` 中 `PathNamespace`）。状态均为 **`beta`**。

```python
from core.infra.project_context import ProjectContext

root = ProjectContext.path.get_project_root()
userspace = ProjectContext.path.get_userspace_root()
```

### config

**描述：** 默认配置与 userspace 覆盖的加载与合并

#### load_core_config

`ProjectContext.config.load_core_config(config_name: str, *, deep_merge_fields=None, override_fields=None) -> dict`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 合并 `core/default_config/{name}.json` 与 `userspace/config/{name}.json`；两侧皆无有效文件时返回 `{}`（不抛错）

#### load_database_config

`ProjectContext.config.load_database_config(database_type: str | None = None) -> dict`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 合并 database common / type 配置，并应用 `DB_*` 环境变量覆盖

#### load_data_config

`ProjectContext.config.load_data_config() -> dict`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 加载合并后的 `data.json`

#### get_default_start_date / get_as_of_latest_completed_trading_date / get_use_sample_stock_list / get_default_market_profile_key / get_decimal_places / get_adj_factor_event_decimal_places / get_database_type / get_simulation_results_max_versions / get_workbench_db_max_versions / get_scan_results_max_versions

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.3.1`（as_of / sample）；`0.2.0`（start_date）；`0.5.0`（decimal / database_type 访问器）；`0.5.0`（retention 访问器，不 bump）
- **描述：** `data.json` 与 database 常用字段访问器；retention 三项分别为仿真磁盘 / workbench DB / scan 日期版本 keep-N（缺键或非法值报错，不在代码里再给默认）

#### load_benchmark_stock_index_list

`ProjectContext.config.load_benchmark_stock_index_list() -> list[dict]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 全局基准股票指数列表

#### merge_market_profile_dicts

`ProjectContext.config.merge_market_profile_dicts(core: dict, user: dict) -> dict`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.5.0`
- **描述：** 市场 profile 专用合并；可作 `discovery.load_overridable_config(..., merge_fn=ProjectContext.config.merge_market_profile_dicts)`

### meta

#### core_version / core_info

`ProjectContext.meta.core_version() -> str | None`  
`ProjectContext.meta.core_info() -> dict | None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 读取 `core_meta.json`（可选回退 `core.system`）

### cache

#### clear_userspace_cache

`ProjectContext.cache.clear_userspace_cache() -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 清理 userspace 路径缓存

### discovery

#### discover_configs

`ProjectContext.discovery.discover_configs(domain: str = "", *, pattern: str = "*.json") -> list[str]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 扫描 core / userspace 下 domain 的配置 id（无后缀），并集排序

#### load_overridable_config

`ProjectContext.discovery.load_overridable_config(domain, config_id, *, merge_fn=None, deep_merge_fields=None, override_fields=None, file_type="json") -> dict`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 加载可覆盖配置；两侧皆无有效文件时抛出 `OverridableConfigNotFoundError`
- **注意：** 通用目录树文件发现 `find_in_tree` 已迁至 `core.infra.discovery`（`Discovery.file.find_in_tree`），不在本模块暴露。
- **举例：**

```python
from core.infra.project_context import ProjectContext
from core.infra.project_context.contracts import OverridableConfigNotFoundError

cfg = ProjectContext.discovery.load_overridable_config(
    "markets",
    "china_a_stock",
    merge_fn=ProjectContext.config.merge_market_profile_dicts,
)
```

---

## types

**描述：** 与 `contracts` 同源的类型与常量挂载点（`TypesNamespace`）

| 符号 | 说明 |
|------|------|
| `OverridableConfigNotFoundError` | 可覆盖配置未找到 |
| `DiscoveredConfig` | 配置路径发现结果 dataclass |
| `MergeFn` | 自定义合并函数类型 |
| `DEFAULT_DUCKDB_DOMAINS` / `DUCKDB_DOMAIN_FILES` / `SUPPORTED_DB_TYPES` | DuckDB 域默认与支持类型 |

```python
from core.infra.project_context import ProjectContext

err = ProjectContext.types.OverridableConfigNotFoundError
```

---

## contracts

| 符号 | 说明 |
|------|------|
| `OverridableConfigNotFoundError` | 可覆盖配置未找到（`FileNotFoundError` 子类） |
| `DiscoveredConfig` | 配置路径发现结果 dataclass |
| `DEFAULT_DUCKDB_DOMAINS` / `DUCKDB_DOMAIN_FILES` / `SUPPORTED_DB_TYPES` | DuckDB 域默认与支持类型 |

```python
from core.infra.project_context.contracts import (
    DEFAULT_DUCKDB_DOMAINS,
    OverridableConfigNotFoundError,
)
```
