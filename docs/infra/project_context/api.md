# Project Context 模块 API 文档

按「描述、函数签名、参数、输出、示例」列出 Project Context 模块中**上层模块常用的入口**；内部辅助函数不列入。架构与设计见 `architecture.md` / `decisions.md`，快速上手见 `overview.md`。

---

## ProjectContextManager（Facade）

### ProjectContextManager（构造函数）

**描述**：项目上下文管理器 Facade，组合 `PathManager`、`FileManager`、`ConfigManager`，提供统一入口 `ctx.path.*` / `ctx.file.*` / `ctx.config.*`。

**函数签名**：`ProjectContextManager()`

**参数**：无

**输出**：`ProjectContextManager` 实例，属性：

- `path`: `PathManager` 类本身  
- `file`: `FileManager` 类本身  
- `config`: `ConfigManager` 类本身  

**Example**：

```python
from core.infra.project_context import ProjectContextManager

ctx = ProjectContextManager()
core_dir = ctx.path.core()
settings = ctx.config.load_with_defaults(default_path, user_path)
```

---

### core_info

**描述**：读取 `core/core_meta.json`，返回 core 的元信息（版本号、发布日期等）。

**函数签名**：`ProjectContextManager.core_info() -> Optional[Dict[str, Any]]`

**参数**：无

**输出**：`Optional[Dict[str, Any]]` —— 包含 `version`、`release_date` 等字段；不存在或解析失败时为 `None`。

---

### core_version

**描述**：获取 core 版本号，基于 `core_info()` 的包装。

**函数签名**：`ProjectContextManager.core_version() -> Optional[str]`

**参数**：无

**输出**：`Optional[str]` —— 版本号字符串，如 `"0.1.0"`；失败时为 `None`。

---

## PathManager（路径管理）

### get_root

**描述**：检测并返回项目根目录。内部通过 `__file__` 向上查找 `.git` / `pyproject.toml` 等标记文件，并做缓存。

**函数签名**：`PathManager.get_root() -> Path`

**参数**：无

**输出**：`Path` —— 项目根目录。

---

### core

**描述**：返回 `core/` 目录路径（或兼容旧结构的 `app/core/`）。

**函数签名**：`PathManager.core() -> Path`

**输出**：`Path` —— `core/` 目录。

---

### userspace

**描述**：返回 `userspace/` 根目录。优先使用环境变量 `NEW_TEA_QUANT_USERSPACE_ROOT` / `NTQ_USERSPACE_ROOT`，否则回退到项目根下的 `userspace/`。

**函数签名**：`PathManager.userspace() -> Path`

**输出**：`Path` —— `userspace/` 根目录。

---

### default_config / user_config

**描述**：返回默认配置目录与用户配置目录路径。

**函数签名**：

- `PathManager.default_config() -> Path` —— `core/default_config/`  
- `PathManager.user_config() -> Path` —— `userspace/config/`

---

### strategy_settings / strategy_results

**描述**：按策略名称返回策略配置文件与结果目录路径。

**函数签名**：

- `PathManager.strategy_settings(strategy_name: str) -> Path`  
- `PathManager.strategy_results(strategy_name: str) -> Path`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str` | 策略名称 |

**输出**：`Path`

**Example**：

```python
settings_path = PathManager.strategy_settings("my_strategy")
results_dir = PathManager.strategy_results("my_strategy")
```

---

### data_source_mapping / data_source_handlers / data_source_providers

**描述**：Data Source 相关路径，供数据源管理和 Discovery 使用。

**函数签名**：

- `PathManager.data_source_mapping() -> Path` —— `userspace/data_source/mapping.py`  
- `PathManager.data_source_handlers() -> Path` —— `userspace/data_source/handlers`  
- `PathManager.data_source_providers() -> Path` —— `userspace/data_source/providers`

---

### find_config_recursively

**描述**：在给定根目录下递归查找指定数据源 key 对应的 `config.py`，用于兼容不同层级结构的 Handler 目录。

**函数签名**：`PathManager.find_config_recursively(base_dir: Path, data_source_key: str, config_filename: str = "config.py") -> Optional[Path]`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `base_dir` | `Path` | 搜索根目录 |
| `data_source_key` | `str` | 数据源键名，用于匹配目录名 |
| `config_filename` | `str` | 配置文件名，默认 `"config.py"` |

**输出**：`Optional[Path]` —— 找到的配置文件路径；未找到返回 `None`。

---

## FileManager（文件管理）

### find_file

**描述**：在指定目录（可选递归）查找单个文件。

**函数签名**：`FileManager.find_file(filename: str, base_dir: Path, recursive: bool = True) -> Optional[Path]`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `filename` | `str` | 文件名，如 `"settings.py"` |
| `base_dir` | `Path` | 搜索根目录 |
| `recursive` | `bool` | 是否递归查找，默认 `True` |

**输出**：`Optional[Path]` —— 找到的文件路径；未找到返回 `None`。

---

### find_files

**描述**：查找所有匹配的文件，返回列表。

**函数签名**：`FileManager.find_files(filename: str, base_dir: Path, recursive: bool = True) -> List[Path]`

---

### read_file

**描述**：读取文件内容，文件不存在或读取失败时返回 `None`。

**函数签名**：`FileManager.read_file(path: Path, encoding: str = "utf-8") -> Optional[str]`

---

### file_exists / dir_exists / ensure_dir

**描述**：文件/目录存在性检查和目录创建。

**函数签名**：

- `FileManager.file_exists(path: Path) -> bool`  
- `FileManager.dir_exists(path: Path) -> bool`  
- `FileManager.ensure_dir(path: Path) -> Path`

---

## ConfigManager（配置管理）

### load_with_defaults

**描述**：加载「默认配置 + 用户配置」并合并，支持 JSON / Python 文件和深度合并字段。

**函数签名**：`ConfigManager.load_with_defaults(default_path: Path, user_path: Path, deep_merge_fields: Set[str] | None = None, override_fields: Set[str] | None = None, file_type: str = "json") -> Dict[str, Any]`

**参数（摘选）**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `default_path` | `Path` | 默认配置文件路径 |
| `user_path` | `Path` | 用户配置文件路径（不存在时只返回默认配置） |
| `deep_merge_fields` | `Set[str] \| None` | 需要深度合并的字段名集合 |
| `override_fields` | `Set[str] \| None` | 需要完全覆盖的字段名集合 |
| `file_type` | `str` | `"json"` 或 `"py"` |

**输出**：`Dict[str, Any]` —— 合并后的配置。

**Example**：

```python
from pathlib import Path
from core.infra.project_context import ConfigManager, PathManager

default_path = PathManager.default_config() / "data.json"
user_path = PathManager.user_config() / "data.json"
settings = ConfigManager.load_with_defaults(default_path, user_path, deep_merge_fields={"stock_list_filter"})
```

---

### load_database_config / get_database_type

**描述**：加载数据库配置（合并默认与用户配置），并获取当前数据库类型。

**函数签名**：

- `ConfigManager.load_database_config(database_type: str | None = None) -> Dict[str, Any]`  
- `ConfigManager.get_database_type() -> str`

---

### load_data_config / load_worker_config / load_system_config / load_logging_config

**描述**：加载各类核心配置（数据、Worker、系统、日志），内部均通过 `load_core_config` + `load_with_defaults` 实现。

**函数签名**（示例）：

- `ConfigManager.load_data_config() -> Dict[str, Any]`  
- `ConfigManager.load_worker_config() -> Dict[str, Any]`  
- `ConfigManager.load_system_config() -> Dict[str, Any]`  
- `ConfigManager.load_logging_config() -> Dict[str, Any]`

---

### get_module_config

**描述**：获取某模块的 Worker 配置（用于并发控制），返回任务类型和预留核心数。

**函数签名**：`ConfigManager.get_module_config(module_name: str) -> Dict[str, Any]`

**输出**：`Dict[str, Any]` —— 如 `{"task_type": TaskType, "reserve_cores": 2}`。

---

### 若干便捷访问方法

**描述**：从配置中读取常用字段。

**常用方法**：

- `ConfigManager.get_default_start_date() -> str`  
- `ConfigManager.get_decimal_places() -> int`  
- `ConfigManager.get_stock_list_filter() -> Dict[str, Any]`  

这些方法内部均基于 `load_data_config()` 实现。

---

## 相关文档

- [Project Context 概览](./overview.md)  
- [Project Context 架构](./architecture.md)  
- [Project Context 设计决策](./decisions.md)  

