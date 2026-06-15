# Project Context 模块 API 文档

本文档采用统一 API 条目格式：函数名、状态、描述、诞生版本、参数（三列表格）、返回值。仅列出对外导出、且上层常调用的入口。

---

## ProjectContextManager

### 函数名
`ProjectContextManager()`

- 状态：`stable`
- 描述：Facade：构造后 `path` / `discovery` / `config` / `file` 分别绑定各 Manager 类对象。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`ProjectContextManager`

---

### 函数名
`ProjectContextManager.core_info() -> Optional[Dict[str, Any]]`

- 状态：`stable`
- 描述：读取 `core/core_meta.json`；失败则尝试 `core.system.system_meta.to_dict()`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Optional[Dict[str, Any]]`

---

### 函数名
`ProjectContextManager.core_version() -> Optional[str]`

- 状态：`stable`
- 描述：从 `core_info()` 取 `version` 字段并转为字符串。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Optional[str]`

---

## PathManager

以下均为类静态方法，签名前缀 `PathManager.`。

### 函数名
`PathManager.get_root() -> Path`

- 状态：`stable`
- 描述：项目根目录；向上查找根标记并缓存。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Path`

---

### 函数名
`PathManager.core() -> Path`

- 状态：`stable`
- 描述：`core/` 目录；优先存在则返回，否则兼容 `app/core/`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Path`

---

### 函数名
`PathManager.userspace() -> Path`

- 状态：`stable`
- 描述：`userspace/`；环境变量 `NEW_TEA_QUANT_USERSPACE_ROOT` / `NTQ_USERSPACE_ROOT` 优先。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Path`

---

### 函数名
`PathManager.default_config() -> Path`

- 状态：`stable`
- 描述：`core/default_config/`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Path`

---

### 函数名
`PathManager.user_config() -> Path`

- 状态：`stable`
- 描述：`userspace/config/`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Path`

---

### 函数名
`PathManager.config() -> Path`

- 状态：`stable`
- 描述：同 `user_config()`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Path`

---

### 函数名
`PathManager.backup() -> Path`

- 状态：`stable`
- 描述：`userspace/backup/` 目录。
- 诞生版本：`0.2.1`
- params：

无

- 返回值：`Path`

---

### 函数名
`PathManager.backup_data() -> Path`

- 状态：`stable`
- 描述：`userspace/backup/data/` 目录。
- 诞生版本：`0.2.1`
- params：

无

- 返回值：`Path`

---

### 函数名
`PathManager.strategy(strategy_name: str) -> Path`

- 状态：`stable`
- 描述：`userspace/strategies/{strategy_name}`。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str` | 必填 |

- 返回值：`Path`

---

### 函数名
`PathManager.strategy_settings(strategy_name: str) -> Path`

- 状态：`stable`
- 描述：策略 `settings.py` 路径。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str` | 必填 |

- 返回值：`Path`

---

### 函数名
`PathManager.strategy_results(strategy_name: str) -> Path`

- 状态：`stable`
- 描述：策略结果根目录。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str` | 必填 |

- 返回值：`Path`

---

### 函数名
`PathManager.strategy_simulation_enum(strategy_name: str) -> Path`

- 状态：`stable`
- 描述：枚举（机会枚举）输出根目录；版本子目录与 `meta.json` 均位于 `results/simulations/enum` 下。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str` | 必填 |

- 返回值：`Path`

---

### 函数名
`PathManager.strategy_simulation_price(strategy_name: str) -> Path`

- 状态：`stable`
- 描述：价格因子模拟版本根目录：`results/simulations/price`。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str` | 必填 |

- 返回值：`Path`

---

### 函数名
`PathManager.strategy_simulation_capital(strategy_name: str) -> Path`

- 状态：`stable`
- 描述：资金分配模拟版本根目录：`results/simulations/capital`。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str` | 必填 |

- 返回值：`Path`

---

### 函数名
`PathManager.strategy_scan_results(strategy_name: str) -> Path`

- 状态：`stable`
- 描述：策略扫描结果根目录：`results/scan`；其下为按日期的子目录（如 `YYYYMMDD`），文件命名与原先 `scan_cache` 下一致（例如 `opportunities.csv`）。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str` | 必填 |

- 返回值：`Path`

---

### 函数名
`PathManager.tags() -> Path`

- 状态：`stable`
- 描述：`userspace/tags`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Path`

---

### 函数名
`PathManager.tag_scenario(scenario_name: str) -> Path`

- 状态：`stable`
- 描述：标签场景目录。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `scenario_name` | `str` | 必填 |

- 返回值：`Path`

---

### 函数名
`PathManager.tag_scenario_settings(scenario_name: str) -> Path`

- 状态：`stable`
- 描述：标签场景 `settings.py`。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `scenario_name` | `str` | 必填 |

- 返回值：`Path`

---

### 函数名
`PathManager.tag_scenario_worker(scenario_name: str) -> Path`

- 状态：`stable`
- 描述：标签场景 `tag_worker.py`。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `scenario_name` | `str` | 必填 |

- 返回值：`Path`

---

### 函数名
`PathManager.data_source() -> Path`

- 状态：`stable`
- 描述：`userspace/data_source`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Path`

---

### 函数名
`PathManager.data_source_mapping() -> Path`

- 状态：`stable`
- 描述：`userspace/data_source/mapping.py`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Path`

---

### 函数名
`PathManager.data_source_handlers() -> Path`

- 状态：`stable`
- 描述：`userspace/data_source/handlers`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Path`

---

### 函数名
`PathManager.data_source_handler(handler_name: str) -> Path`

- 状态：`stable`
- 描述：单个 handler 目录。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `handler_name` | `str` | 必填 |

- 返回值：`Path`

---

### 函数名
`PathManager.data_contract() -> Path`

- 状态：`stable`
- 描述：`userspace/data_contract`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Path`

---

### 函数名
`PathManager.data_contract_mapping() -> Path`

- 状态：`stable`
- 描述：`userspace/data_contract/mapping.py`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Path`

---

### 函数名
`PathManager.data_contract_loaders() -> Path`

- 状态：`stable`
- 描述：`userspace/data_contract/loaders`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Path`

---

### 函数名
`PathManager.data_source_providers() -> Path`

- 状态：`stable`
- 描述：`userspace/data_source/providers`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Path`

---

### 函数名
`PathManager.data_source_provider(provider_name: str) -> Path`

- 状态：`stable`
- 描述：单个 provider 目录。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `provider_name` | `str` | 必填 |

- 返回值：`Path`

---

## FileManager

### 函数名
`FileManager.find_file(filename: str, base_dir: Path, recursive: bool = True) -> Optional[Path]`

- 状态：`stable`
- 描述：在目录中查找首个匹配文件名。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `filename` | `str` | 必填 |
| `base_dir` | `Path` | 必填 |
| `recursive` (可选) | `bool` | 默认 `True` |

- 返回值：`Optional[Path]`

---

### 函数名
`FileManager.find_files(filename: str, base_dir: Path, recursive: bool = True) -> List[Path]`

- 状态：`stable`
- 描述：查找全部匹配文件。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `filename` | `str` | 必填 |
| `base_dir` | `Path` | 必填 |
| `recursive` (可选) | `bool` | 默认 `True` |

- 返回值：`List[Path]`

---

### 函数名
`FileManager.read_file(path: Path, encoding: str = "utf-8") -> Optional[str]`

- 状态：`stable`
- 描述：读文本；失败或不存在返回 `None`。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `path` | `Path` | 必填 |
| `encoding` (可选) | `str` | 默认 `utf-8` |

- 返回值：`Optional[str]`

---

### 函数名
`FileManager.file_exists(path: Path) -> bool`

- 状态：`stable`
- 描述：路径存在且为文件。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `path` | `Path` | 必填 |

- 返回值：`bool`

---

### 函数名
`FileManager.dir_exists(path: Path) -> bool`

- 状态：`stable`
- 描述：路径存在且为目录。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `path` | `Path` | 必填 |

- 返回值：`bool`

---

### 函数名
`FileManager.ensure_dir(path: Path) -> Path`

- 状态：`stable`
- 描述：`mkdir(parents=True, exist_ok=True)` 后返回路径。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `path` | `Path` | 必填 |

- 返回值：`Path`

---

## ConfigManager

### 函数名
`ConfigManager.load_with_defaults(default_path: Path, user_path: Path, deep_merge_fields: Set[str] | None = None, override_fields: Set[str] | None = None, file_type: str = "json") -> Dict[str, Any]`

- 状态：`stable`
- 描述：加载默认并与用户合并。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `default_path` | `Path` | 必填 |
| `user_path` | `Path` | 必填 |
| `deep_merge_fields` (可选) | `Set[str] | None` | 嵌套 dict 合并字段 |
| `override_fields` (可选) | `Set[str] | None` | 浅层覆盖语义 |
| `file_type` (可选) | `str` | `json` 或 `py` |

- 返回值：`Dict[str, Any]`

---

### 函数名
`ConfigManager.load_json(path: Path) -> Dict[str, Any]`

- 状态：`stable`
- 描述：加载 JSON；失败返回 `{}`。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `path` | `Path` | 必填 |

- 返回值：`Dict[str, Any]`

---

### 函数名
`ConfigManager.load_python(path: Path, var_name: str = "settings") -> Dict[str, Any]`

- 状态：`stable`
- 描述：动态加载 Python 文件中的 dict 变量。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `path` | `Path` | 必填 |
| `var_name` (可选) | `str` | 默认 `settings` |

- 返回值：`Dict[str, Any]`

---

### 函数名
`ConfigManager.load_core_config(config_name: str, deep_merge_fields: Set[str] | None = None, override_fields: Set[str] | None = None) -> Dict[str, Any]`

- 状态：`stable`
- 描述：合并 `default_config/{config_name}.json` 与 `userspace/config/{config_name}.json`。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `config_name` | `str` | 不含后缀 |
| `deep_merge_fields` (可选) | `Set[str] | None` | 默认 `None` |
| `override_fields` (可选) | `Set[str] | None` | 默认 `None` |

- 返回值：`Dict[str, Any]`

---

### 函数名
`ConfigManager.load_database_config(database_type: str | None = None) -> Dict[str, Any]`

- 状态：`stable`
- 描述：合并 database 默认/用户及环境变量；见实现。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `database_type` (可选) | `str | None` | 默认从 common 配置推断 |

- 返回值：`Dict[str, Any]`

---

### 函数名
`ConfigManager.load_with_env_vars(config: Dict[str, Any], env_var_mapping: Dict[str, str]) -> Dict[str, Any]`

- 状态：`stable`
- 描述：按点分路径写入环境变量覆盖。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `config` | `Dict[str, Any]` | 必填 |
| `env_var_mapping` | `Dict[str, str]` | 配置路径 -> 环境变量名 |

- 返回值：`Dict[str, Any]`

---

### 函数名
`ConfigManager.load_data_config() -> Dict[str, Any]`

- 状态：`stable`
- 描述：`load_core_config('data')`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Dict[str, Any]`

---

## DiscoveryManager

以下均为类静态方法，签名前缀 `DiscoveryManager.`。

### 函数名
`DiscoveryManager.discover_configs(domain: str = "", *, pattern: str = "*.json") -> List[str]`

- 状态：`stable`
- 描述：扫描 `default_config[/domain]/` 与 `userspace/config[/domain]/` 下匹配文件的 config id（无后缀）并集。
- 诞生版本：`0.3.0`
- params：

| 参数 | 类型 | 说明 |
|------|------|------|
| `domain` | `str` | 空串为根级 `data.json` 等；`markets` 为子目录 |
| `pattern` (可选) | `str` | 默认 `*.json` |

- 返回值：`List[str]`

---

### 函数名
`DiscoveryManager.discover_config(domain: str, config_id: str) -> DiscoveredConfig`

- 状态：`stable`
- 描述：解析 core / userspace 路径，不读取内容。
- 诞生版本：`0.3.0`
- params：

| 参数 | 类型 | 说明 |
|------|------|------|
| `domain` | `str` | 配置域 |
| `config_id` | `str` | 配置 id |

- 返回值：`DiscoveredConfig`

---

### 函数名
`DiscoveryManager.load_overridable_config(domain, config_id, *, merge_fn=None, deep_merge_fields=None, override_fields=None, file_type="json") -> Dict[str, Any]`

- 状态：`stable`
- 描述：发现路径后加载并合并；`merge_fn` 为 `None` 时使用 `ConfigManager.load_with_defaults`。
- 诞生版本：`0.3.0`
- params：

| 参数 | 类型 | 说明 |
|------|------|------|
| `domain` | `str` | 配置域 |
| `config_id` | `str` | 配置 id |
| `merge_fn` | 可选 callable | 如 `merge_market_profile_dicts` |

- 返回值：`Dict[str, Any]`

---

### 函数名
`DiscoveryManager.find_in_tree(base_dir: Path, key: str, config_filename: str = "config.py") -> Optional[Path]`

- 状态：`stable`
- 描述：在任意目录树中查找配置（如 data source handlers）。
- 诞生版本：`0.3.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `base_dir` | `Path` | 搜索根 |
| `key` | `str` | 目录名匹配键 |
| `config_filename` (可选) | `str` | 默认 `config.py` |

- 返回值：`Optional[Path]`

---

## ConfigManager（续）

### 函数名
`ConfigManager.load_worker_config() -> Dict[str, Any]`

- 状态：`stable`
- 描述：`load_core_config('worker')`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Dict[str, Any]`

---

### 函数名
`ConfigManager.load_system_config() -> Dict[str, Any]`

- 状态：`stable`
- 描述：`load_core_config('system')`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Dict[str, Any]`

---

### 函数名
`ConfigManager.load_logging_config() -> Dict[str, Any]`

- 状态：`stable`
- 描述：`load_core_config('logging')`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Dict[str, Any]`

---

### 函数名
`ConfigManager.load_benchmark_stock_index_list() -> List[Dict[str, Any]]`

- 状态：`stable`
- 描述：从数据配置读取 `benchmark_stock_index_list`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`List[Dict[str, Any]]`

---

### 函数名
`ConfigManager.get_default_start_date() -> str`

- 状态：`stable`
- 描述：数据配置 `default_start_date`。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`str`

---

### 函数名
`ConfigManager.get_decimal_places() -> int`

- 状态：`stable`
- 描述：`data.json` → `decimal_places.default`（默认 `2`）。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`int`

---

### 函数名
`ConfigManager.get_adj_factor_event_decimal_places() -> Dict[str, int]`

- 状态：`stable`
- 描述：`decimal_places.adj_factor_event` 爬取舍入精度（`factor_places` / `price_places` / `diff_places`）。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`Dict[str, int]`

---

### 函数名
`ConfigManager.get_database_type() -> str`

- 状态：`stable`
- 描述：当前数据库类型字符串。
- 诞生版本：`0.2.0`
- params：

无

- 返回值：`str`

---

### 函数名
`ConfigManager.get_module_config(module_name: str) -> Dict[str, Any]`

- 状态：`stable`
- 描述：Worker 模块任务配置：`task_type`（枚举）、`reserve_cores`；内部导入 `TaskType`。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `module_name` | `str` | 如 `OpportunityEnumerator` |

- 返回值：`Dict[str, Any]`

---

## 示例

```python
from core.infra.project_context import PathManager, DiscoveryManager, ConfigManager

root = PathManager.get_root()
profiles = DiscoveryManager.discover_configs("markets")
raw = DiscoveryManager.load_overridable_config("markets", "china_a_stock")
db_cfg = ConfigManager.load_database_config()
data = ConfigManager.load_data_config()
```

---

## 相关文档

- [架构总览](./ARCHITECTURE.md)
- [详细设计](./DESIGN.md)
- [决策记录](./DECISIONS.md)