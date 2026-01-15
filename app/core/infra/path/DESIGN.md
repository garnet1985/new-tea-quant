# Path Management Module - 设计文档

## 📋 概述

Path Management Module 提供项目路径、文件操作和配置管理的统一接口。

**核心功能**：
1. **路径管理**：提供基于项目根目录的路径访问
2. **文件操作**：文件查找、读取、存在性检查等
3. **配置管理**：支持默认配置和用户配置的自动合并

## 🏗️ 架构设计

### 模块结构

```
core/infra/path/
├── __init__.py                    # 模块导出
├── DESIGN.md                      # 本文档
├── path_manager.py                # 路径管理器
├── file_manager.py                 # 文件管理器
├── config_manager.py              # 配置管理器
└── project_context_manager.py    # 项目上下文管理器（Facade）
```

### 职责划分

#### 1. PathManager（路径管理器）

**职责**：提供常用路径的快捷访问，所有路径基于项目根目录。

**核心功能**：
- 项目根目录检测和访问
- 核心目录路径（`core/`）
- 用户空间路径（`userspace/`）
- 策略相关路径（策略目录、配置文件、结果目录等）
- 标签相关路径
- 配置目录路径

**设计原则**：
- 所有路径都基于项目根目录（通过 `__file__` 自动检测）
- 提供静态方法，无状态
- 返回 `Path` 对象，不强制创建目录（由调用方决定）

**API 示例**：
```python
PathManager.get_root()              # 项目根目录
PathManager.core()                  # core/ 目录
PathManager.userspace()             # userspace/ 目录
PathManager.config()                # config/ 目录
PathManager.strategy("example")     # userspace/strategies/example/
PathManager.strategy_settings("example")  # userspace/strategies/example/settings.py
PathManager.strategy_results("example")  # userspace/strategies/example/results/
PathManager.tag_scenario("momentum")      # userspace/tags/momentum/
```

#### 2. FileManager（文件管理器）

**职责**：文件查找、读取、存在性检查等操作。

**核心功能**：
- 递归查找文件
- 查找所有匹配的文件
- 读取文件内容
- 检查文件/目录是否存在
- 确保目录存在（创建目录）

**设计原则**：
- 使用 `pathlib.Path` 而不是字符串路径
- 提供静态方法，无状态
- 文件不存在时返回 `None` 或空列表

**API 示例**：
```python
FileManager.find_file("settings.py", base_dir, recursive=True)
FileManager.find_files("settings.py", base_dir, recursive=True)
FileManager.read_file(path, encoding="utf-8")
FileManager.file_exists(path)
FileManager.dir_exists(path)
FileManager.ensure_dir(path)  # 确保目录存在，不存在则创建
```

#### 3. ConfigManager（配置管理器）

**职责**：处理默认配置和用户配置的加载与合并。

**核心功能**：
- 加载 JSON 配置文件
- 加载 Python 配置文件（如 `settings.py`）
- 合并默认配置和用户配置
- 支持深度合并和完全覆盖两种模式

**设计原则**：
- 配置合并逻辑复用 `utils/util.py` 的 `deep_merge_config`
- 支持 JSON 和 Python 两种文件格式
- Python 文件支持动态导入（`importlib`）
- 提供静态方法，无状态

**API 示例**：
```python
# 加载配置（自动合并默认配置和用户配置）
ConfigManager.load_with_defaults(
    default_path=Path("core/modules/strategy/default_settings.json"),
    user_path=Path("userspace/strategies/example/settings.py"),
    deep_merge_fields={"params"},
    override_fields={"dependencies"},
    file_type="py"  # "json" | "py"
)

# 单独加载
ConfigManager.load_json(path)
ConfigManager.load_python(path, var_name="settings")
```

#### 4. ProjectContextManager（项目上下文管理器）

**职责**：Facade 模式，组合三个 Manager 提供统一入口。

**设计原则**：
- 组合 `PathManager`、`FileManager`、`ConfigManager`
- 提供便捷的统一 API
- 可以独立使用各个 Manager，也可以使用 Facade
- 单例模式或静态方法（待定）

**API 示例**：
```python
# 方式 1：使用 Facade（推荐）
ctx = ProjectContextManager()
core_dir = ctx.path.core()
settings = ctx.config.load_with_defaults(default_path, user_path)
file = ctx.file.find_file("settings.py", ctx.path.userspace())

# 方式 2：独立使用（灵活）
from app.core.infra.path import PathManager, FileManager, ConfigManager
core_dir = PathManager.core()
```

## 🎯 使用场景

### 场景 1：获取策略配置（自动合并默认配置）

```python
from app.core.infra.path import ProjectContextManager

ctx = ProjectContextManager()

# 自动合并默认配置和用户配置
default_settings = ctx.path.core() / "modules" / "strategy" / "default_settings.json"
user_settings = ctx.path.strategy_settings("example")
settings = ctx.config.load_with_defaults(
    default_settings,
    user_settings,
    deep_merge_fields={"params"},
    file_type="py"
)
```

### 场景 2：查找策略文件

```python
# 查找所有策略的 settings.py
strategies_dir = ctx.path.userspace() / "strategies"
settings_files = ctx.file.find_files("settings.py", strategies_dir, recursive=True)
```

### 场景 3：确保结果目录存在

```python
results_dir = ctx.path.strategy_results("example")
ctx.file.ensure_dir(results_dir)
```

### 场景 4：加载数据源映射配置

```python
# 加载数据源映射（默认 + 用户自定义）
default_mapping = ctx.path.core() / "modules" / "data_source" / "handlers" / "mapping.json"
user_mapping = ctx.path.userspace() / "data_source" / "mapping.json"
mapping = ctx.config.load_with_defaults(
    default_mapping,
    user_mapping,
    deep_merge_fields={"params"},
    override_fields={"dependencies"}
)
```

## 📝 实现细节

### 项目根目录检测

```python
@staticmethod
def get_root() -> Path:
    """获取项目根目录
    
    检测逻辑：
    1. 从当前文件（__file__）向上查找，直到找到包含特定标记的目录
    2. 标记可以是：.git、pyproject.toml、setup.py、README.md 等
    3. 缓存结果，避免重复检测
    """
```

### 配置加载

- **JSON**：使用 `json.load()`
- **Python**：使用 `importlib.import_module()` 动态导入，然后获取变量

### 错误处理

- **路径不存在**：返回 `Path` 对象，不强制创建（由调用方决定）
- **文件不存在**：返回 `None` 或空字典（根据方法）
- **配置加载失败**：记录日志，返回默认值或抛出异常（根据场景）

## 🔍 待讨论问题

1. **ProjectContextManager 是单例还是实例？**
   - 建议：静态方法或单例（因为都是无状态的工具方法）

2. **ConfigManager 是否支持其他文件格式（YAML、TOML）？**
   - 建议：先支持 JSON 和 Python，后续扩展

3. **是否需要支持路径别名（如 `@core`、`@userspace`）？**
   - 建议：先不实现，后续根据需求决定

## 📚 依赖

- `pathlib.Path` - Python 标准库
- `utils/util.py` - 配置合并逻辑（`deep_merge_config`）
- `importlib` - Python 标准库（用于动态导入 Python 配置文件）
