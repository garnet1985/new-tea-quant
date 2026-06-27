# API迁移指南 - ProjectContext → Discovery

## 背景

ProjectContext已经精简，移除了所有Discovery和Config相关的API（22个），只保留路径快捷入口（41个）。

所有Discovery和Config的调用方需要迁移到`infra/discovery`模块。

## 迁移映射表

### 1. 配置加载API迁移

| 旧API（ProjectContext） | 新API（infra/discovery） | 说明 |
|------------------------|------------------------|------|
| `ProjectContext.load_core_config("logging")` | `FileUtils.load_json(path)` | 需要先获取路径 |
| `ProjectContext.load_database_config()` | `FileUtils.load_json(path)` | 需要先获取路径 |
| `ProjectContext.load_data_config()` | `FileUtils.load_json(path)` | 需要先获取路径 |
| `ProjectContext.load_json_file(path)` | `FileUtils.load_json(path)` | 直接替换 |
| `ProjectContext.load_file_content(path)` | `FileUtils.load_file_content(path)` | 直接替换 |

### 2. Discovery API迁移

| 旧API（ProjectContext） | 新API（infra/discovery） | 说明 |
|------------------------|------------------------|------|
| `ProjectContext.discover_strategies()` | `discover_directories(PathManager.get_strategies_root())` | 需要过滤目录名 |
| `ProjectContext.discover_tags()` | `discover_directories(PathManager.get_tags_root())` | 需要过滤目录名 |
| `ProjectContext.discover_configs(domain)` | 自定义实现 | 使用 FileDiscovery + FileUtils |
| `ProjectContext.find_file(filename, dir)` | `FileUtils.find_file(dir, filename)` | 参数顺序调整 |
| `ProjectContext.find_in_tree(base_dir, key)` | `FileUtils.find_file(base_dir, filename)` | 使用 find_file |

### 3. 特殊配置API迁移

| 旧API（ProjectContext） | 新API（底层实现） | 说明 |
|------------------------|------------------|------|
| `ProjectContext.get_default_start_date()` | 从 data.json 中读取 | 使用 FileUtils.load_json() |
| `ProjectContext.get_as_of_latest_completed_trading_date()` | 从 data.json 中读取 | 使用 FileUtils.load_json() |
| `ProjectContext.get_use_sample_stock_list()` | 从 data.json 中读取 | 使用 FileUtils.load_json() |

### 4. 配置合并API迁移

| 旧API（ProjectContext） | 新API（底层实现） | 说明 |
|------------------------|------------------|------|
| `ProjectContext.deep_merge_config(defaults, custom)` | 自定义实现 | 使用 Utils.deep_merge_dict() |
| `ProjectContext.merge_mapping_configs(defaults, custom)` | 自定义实现 | 使用 Utils.deep_merge_dict() |
| `ProjectContext.load_with_defaults(default_path, user_path)` | 自定义实现 | FileUtils.load_json() + Utils.deep_merge_dict() |

## 迁移示例

### 示例1：加载配置文件

**旧代码**：
```python
from core.infra.project_context import ProjectContext

# 加载 logging 配置
settings = ProjectContext.load_core_config("logging")
```

**新代码**：
```python
from core.infra.project_context import ProjectContext
from core.infra.discovery import FileUtils

# 先获取路径，再加载配置
core_config_root = ProjectContext.get_default_config_root()
logging_config_path = core_config_root / "logging.json"
settings = FileUtils.load_json(logging_config_path)
```

### 示例2：发现策略

**旧代码**：
```python
from core.infra.project_context import ProjectContext

# 发现所有策略
strategies = ProjectContext.discover_strategies()
```

**新代码**：
```python
from core.infra.project_context import ProjectContext
from core.infra.discovery import discover_directories
from pathlib import Path

# 发现策略目录
strategies_root = ProjectContext.get_strategies_root()
strategy_dirs = discover_directories(
    strategies_root,
    pattern="*/",
    exclude_patterns=["*/.*"]
)
# 提取策略名称
strategies = [dir.name for dir in strategy_dirs if not dir.name.startswith('.')]
strategies.sort()
```

### 示例3：查找文件

**旧代码**：
```python
from core.infra.project_context import ProjectContext
from pathlib import Path

# 查找文件
file_path = ProjectContext.find_file("settings.json", Path("/project"))
```

**新代码**：
```python
from core.infra.discovery import FileUtils
from pathlib import Path

# 查找文件（参数顺序调整）
file_path = FileUtils.find_file(
    start_dir=Path("/project"),
    filename="settings.json"
)
```

### 示例4：获取特殊配置

**旧代码**：
```python
from core.infra.project_context import ProjectContext

# 获取默认起始日期
default_start_date = ProjectContext.get_default_start_date()
```

**新代码**：
```python
from core.infra.project_context import ProjectContext
from core.infra.discovery import FileUtils

# 加载 data.json 并读取字段
data_config_path = ProjectContext.get_default_config_root() / "data.json"
data_config = FileUtils.load_json(data_config_path)
default_start_date = data_config.get("default_start_date", "20200101")
```

## 迁移步骤

1. **查找所有使用旧API的地方**：
   ```bash
   # 查找所有 ProjectContext.load_* 调用
   grep -r "ProjectContext.load_" --include="*.py"

   # 查找所有 ProjectContext.discover_* 调用
   grep -r "ProjectContext.discover_" --include="*.py"

   # 查找所有 ProjectContext.find_* 调用
   grep -r "ProjectContext.find_" --include="*.py"
   ```

2. **逐个迁移**：
   - 先迁移简单的API（如 `load_json_file` → `FileUtils.load_json`）
   - 再迁移复杂的API（如 `discover_strategies`）

3. **测试验证**：
   - 运行单元测试确保功能正确
   - 运行集成测试确保系统正常

## 常见问题

### Q1: 为什么移除这些API？

**原因**：
- ProjectContext应该只提供路径快捷入口
- Discovery和Config是通用功能，调用方直接使用底层更清晰
- 精简API，减少维护负担

### Q2: 迁移后性能会下降吗？

**不会**：
- 新API（FileUtils、FileDiscovery）提供了更高效的功能
- 支持缓存机制
- 路径获取更快

### Q3: 如果发现迁移困难怎么办？

**建议**：
- 先保留旧API一段时间（标记为deprecated）
- 给调用方足够的迁移时间
- 提供迁移脚本帮助批量迁移

## 临时兼容方案

如果需要临时保留旧API，可以添加deprecated标记：

```python
# api.py（临时兼容）
@classmethod
@abstractmethod
def load_core_config(cls, config_name: str) -> Dict[str, Any]:
    """
    加载 core 配置

    deprecated: v0.5.0 - 请改用 FileUtils.load_json()
    """
    pass
```

然后在实现中调用底层：

```python
# project_context_manager.py（临时兼容）
@classmethod
def load_core_config(cls, config_name: str) -> Dict[str, Any]:
    """加载 core 配置（已废弃）"""
    import warnings
    warnings.warn(
        "load_core_config() 已废弃，请改用 FileUtils.load_json()",
        DeprecationWarning
    )
    # 调用底层实现
    from core.infra.discovery import FileUtils
    core_config_root = PathManager.get_default_config_root()
    config_path = core_config_root / f"{config_name}.json"
    return FileUtils.load_json(config_path) or {}
```

## 总结

迁移完成后：
- ProjectContext：只保留路径快捷入口（41个API）
- Discovery：所有Discovery API都在 infra/discovery
- Config：所有Config加载都用 FileUtils

架构更清晰，职责更明确。