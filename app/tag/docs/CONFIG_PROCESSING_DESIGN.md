# Tag 配置处理设计文档

## 📋 设计目标

设计配置处理模块，实现：
1. 读取 settings 文件（Python 文件，统一命名为 settings.py）
2. 检查 tag 是否 enable（`is_enabled` 字段）
3. 验证必需字段，给默认值或报错
4. 输出可执行的 config 字典

## 🎯 输入输出

**输入**：
- `settings_path`: settings 文件路径（相对路径，相对于 calculator 同级目录）
  - 示例：如果 calculator 在 `app/tag/tags/example/calculator.py`
  - 则 settings 在 `app/tag/tags/example/settings.py`
  - 相对路径：`"settings.py"` 或 `"./settings.py"`

**输出**：
- 成功：返回处理后的 config 字典（Dict[str, Any]）
- 失败：抛出异常（ValueError, FileNotFoundError, ImportError 等）

## 📐 设计细节

### 1. 读取 Config 文件

**文件格式**：
- Python 文件（`.py`）
- 必须包含 `TAG_CONFIG` 字典变量

**读取方式**：
- 动态导入 Python 模块
- 提取 `TAG_CONFIG` 变量

**错误处理**：
- 文件不存在：`FileNotFoundError`
- 语法错误：`SyntaxError`
- 缺少 `TAG_CONFIG`：`AttributeError` 或 `ValueError`
- 导入错误：`ImportError`（如依赖的模块不存在）

### 2. 检查 is_enabled

**位置**：
- 在 config 字典的根上：`config["is_enabled"]`
- 默认值：`False`（如果未配置）

**行为**：
1. **找不到 config 文件**：直接抛出 `FileNotFoundError`（因为 calculator 必须有一个配置文件）
2. **找不到 is_enabled 字段**：给出 warning，按照 `False` 执行（跳过该 tag）
3. **有 is_enabled 字段且为 False**：明确抛出 `ValueError`，告诉用户 tag 被 disable 了，所以跳过

**实现逻辑**：
```python
if "is_enabled" not in config:
    import warnings
    warnings.warn(f"Tag {config.get('meta', {}).get('name', 'unknown')} 缺少 is_enabled 字段，默认按 False 处理（跳过）")
    raise ValueError(f"Tag 未启用: {config.get('meta', {}).get('name', 'unknown')} (is_enabled 字段缺失，默认 False)")

if not config.get("is_enabled", False):
    tag_name = config.get("meta", {}).get("name", "unknown")
    raise ValueError(f"Tag 未启用: {tag_name} (is_enabled = False)")
```

### 3. 验证必需字段

**必需字段列表**：
```python
required_fields = {
    "meta": dict,              # 必需，字典（元信息）
    "base_term": str,          # 必需，枚举值
    "performance": dict,       # 必需，字典（包含必需子字段）
}
```

**可选字段（有默认值）**：
```python
optional_fields = {
    "core": None,              # 可选，None 或不存在也可以
    "required_terms": [],      # 可选，默认 []
    "required_data": [],       # 可选，默认 []
}
```

**performance 字段的必需子字段**（performance 必须存在）：
```python
performance_required = {
    "update_mode": str,         # 必须字段且在枚举中
    "on_version_change": str,  # 必须字段，并且在枚举中
}

performance_optional = {
    "max_worker": int,          # 可选，默认按照 job 数量自动分配
}
```

**meta 字段的必需子字段**：
```python
meta_required = {
    "name": str,               # 必需，字符串
    "display_name": str,       # 必需，字符串
    "version": str,            # 必需，字符串（如 "1.0"）
}
```

**验证规则**：
1. 检查必需字段是否存在
2. 检查字段类型是否正确
3. 检查枚举值是否有效
4. 应用默认值（如果字段不存在）

### 4. 处理默认值

**处理顺序**：
1. 先验证必需字段（如果缺少，报错）
2. 再处理默认值（如果字段不存在，设置默认值）

**默认值规则**：
- `core`: 如果不存在，设置为 `None` 或 `{}`（空字典）
- `required_terms`: 如果不存在或为 `None`，设置为 `[]`
- `required_data`: 如果不存在，设置为 `[]`
- `performance`: 如果不存在，设置为 `{}`（空字典，由系统自动分配）
- `performance.update_mode`: 如果不存在，必须报错（必需字段）
- `performance.on_version_change`: 如果不存在，必须报错（必需字段）
- `performance.max_worker`: 如果不存在，由系统根据 job 数量自动分配（不设置默认值）

## 🔧 实现设计

### ConfigProcessor 类

```python
from typing import Dict, Any, Optional
import importlib.util
import os
from pathlib import Path
from app.tag.enums import KlineTerm, UpdateMode, VersionChangeAction


class ConfigProcessor:
    """Tag 配置处理器
    
    职责：
    1. 读取 config 文件
    2. 检查 is_enabled
    3. 验证必需字段
    4. 处理默认值
    5. 输出可执行的 config 字典
    """
    
    @staticmethod
    def load_config(settings_path: str, calculator_path: str = None) -> Dict[str, Any]:
        """
        加载并处理 settings 文件
        
        Args:
            settings_path: settings 文件路径（相对路径，相对于 calculator 同级目录）
            calculator_path: calculator 文件路径（可选，用于确定 settings 的相对路径）
            
        Returns:
            Dict[str, Any]: 处理后的 config 字典
            
        Raises:
            FileNotFoundError: 文件不存在（直接抛错，因为 calculator 必须有一个配置文件）
            SyntaxError: 文件语法错误
            ValueError: 配置验证失败（包括 is_enabled = False）
            ImportError: 导入错误（如依赖模块不存在）
        """
        # 1. 读取 settings 文件
        config = ConfigProcessor._read_settings_file(settings_path, calculator_path)
        
        # 2. 检查 is_enabled（必须在验证之前，因为如果 disabled 就不需要继续验证）
        ConfigProcessor._check_enabled(config)
        
        # 3. 验证必需字段
        ConfigProcessor._validate_required_fields(config)
        
        # 4. 处理默认值
        ConfigProcessor._apply_defaults(config)
        
        # 5. 验证枚举值
        ConfigProcessor._validate_enums(config)
        
        return config
    
    @staticmethod
    def _read_settings_file(settings_path: str, calculator_path: str = None) -> Dict[str, Any]:
        """
        读取 settings 文件（Python 文件）
        
        Args:
            settings_path: settings 文件路径（相对路径）
            calculator_path: calculator 文件路径（可选，用于确定相对路径的基准）
            
        Returns:
            Dict[str, Any]: TAG_CONFIG 字典
            
        Raises:
            FileNotFoundError: 文件不存在（直接抛错，因为 calculator 必须有一个配置文件）
            SyntaxError: 文件语法错误
            AttributeError: 缺少 TAG_CONFIG 变量
        """
        # 转换为绝对路径
        if not os.path.isabs(settings_path):
            if calculator_path:
                # 相对于 calculator 同级目录
                calculator_dir = os.path.dirname(os.path.abspath(calculator_path))
                settings_path = os.path.join(calculator_dir, settings_path)
            else:
                # 相对于当前工作目录
                settings_path = os.path.abspath(settings_path)
        
        if not os.path.exists(settings_path):
            raise FileNotFoundError(
                f"Settings 文件不存在: {settings_path}\n"
                f"Calculator 必须有一个配置文件（settings.py）"
            )
        
        # 动态导入模块
        spec = importlib.util.spec_from_file_location("tag_settings", settings_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"无法加载 settings 文件: {settings_path}")
        
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except SyntaxError as e:
            raise SyntaxError(f"Settings 文件语法错误: {settings_path}\n{str(e)}")
        except Exception as e:
            raise ImportError(f"导入 settings 文件失败: {settings_path}\n{str(e)}")
        
        # 提取 TAG_CONFIG
        if not hasattr(module, "TAG_CONFIG"):
            raise ValueError(f"Settings 文件缺少 TAG_CONFIG 变量: {settings_path}")
        
        config = module.TAG_CONFIG
        
        if not isinstance(config, dict):
            raise ValueError(f"TAG_CONFIG 必须是字典类型，当前类型: {type(config)}")
        
        return config
    
    @staticmethod
    def _check_enabled(config: Dict[str, Any]):
        """
        检查 tag 是否启用
        
        行为：
        1. 找不到 is_enabled 字段：给出 warning，按照 False 执行（跳过）
        2. 有 is_enabled 字段且为 False：明确抛出 ValueError，告诉用户 tag 被 disable 了
        
        Args:
            config: config 字典
            
        Raises:
            ValueError: tag 未启用（is_enabled = False 或字段缺失）
        """
        import warnings
        
        # 检查根级别的 is_enabled 字段
        if "is_enabled" not in config:
            tag_name = config.get("meta", {}).get("name", "unknown")
            warnings.warn(
                f"Tag '{tag_name}' 缺少 is_enabled 字段，默认按 False 处理（跳过）",
                UserWarning
            )
            raise ValueError(
                f"Tag 未启用: {tag_name} (is_enabled 字段缺失，默认 False，跳过该 tag)"
            )
        
        # 检查 is_enabled 的值
        is_enabled = config.get("is_enabled", False)
        if not is_enabled:
            tag_name = config.get("meta", {}).get("name", "unknown")
            raise ValueError(
                f"Tag 未启用: {tag_name} (is_enabled = False，跳过该 tag)"
            )
    
    @staticmethod
    def _validate_required_fields(config: Dict[str, Any]):
        """
        验证必需字段
        
        必需字段：
        - meta: 必需，字典（元信息）
        - base_term: 必需，字符串（枚举值）
        
        可选字段：
        - core: 可选，None 或不存在也可以
        - performance: 可选，默认按照 job 数量自动分配
        - required_terms: 可选，默认 []
        - required_data: 可选，默认 []
        
        如果 performance 存在，则其子字段：
        - update_mode: 必须字段且在枚举中
        - on_version_change: 必须字段，并且在枚举中
        
        Args:
            config: config 字典
            
        Raises:
            ValueError: 缺少必需字段或字段类型错误
        """
        # 验证顶层必需字段
        if "meta" not in config:
            raise ValueError("配置缺少必需字段: meta")
        
        if "base_term" not in config:
            raise ValueError("配置缺少必需字段: base_term")
        
        # 验证 meta 必需字段
        meta = config["meta"]
        if not isinstance(meta, dict):
            raise ValueError(f"meta 必须是字典，当前类型: {type(meta)}")
        
        meta_required = ["name", "display_name", "version"]
        for field in meta_required:
            if field not in meta:
                raise ValueError(f"meta 缺少必需字段: {field}")
        
        # 验证字段类型
        if not isinstance(meta["name"], str):
            raise ValueError(f"meta.name 必须是字符串，当前类型: {type(meta['name'])}")
        
        if not isinstance(meta["display_name"], str):
            raise ValueError(f"meta.display_name 必须是字符串，当前类型: {type(meta['display_name'])}")
        
        if not isinstance(meta["version"], str):
            raise ValueError(f"meta.version 必须是字符串，当前类型: {type(meta['version'])}")
        
        # 验证 base_term 类型
        if not isinstance(config["base_term"], str):
            raise ValueError(f"base_term 必须是字符串，当前类型: {type(config['base_term'])}")
        
        # 验证 performance（必需字段）
        if "performance" not in config:
            raise ValueError("配置缺少必需字段: performance")
        
        perf = config["performance"]
        if not isinstance(perf, dict):
            raise ValueError(f"performance 必须是字典，当前类型: {type(perf)}")
        
        # performance 的必需子字段
        if "update_mode" not in perf:
            raise ValueError("performance 缺少必需字段: update_mode")
        
        if "on_version_change" not in perf:
            raise ValueError("performance 缺少必需字段: on_version_change")
        
        # core 是可选的，不需要验证
    
    @staticmethod
    def _apply_defaults(config: Dict[str, Any]):
        """
        应用默认值
        
        Args:
            config: config 字典（会被修改）
        """
        # core 默认 None（如果不存在）
        if "core" not in config:
            config["core"] = None
        
        # required_terms 默认 []
        if "required_terms" not in config or config["required_terms"] is None:
            config["required_terms"] = []
        
        # required_data 默认 []
        if "required_data" not in config:
            config["required_data"] = []
        
        # 注意：performance 是必需字段，必须在 _validate_required_fields 中验证
        # performance.update_mode 和 on_version_change 是必需字段
        # performance.max_worker 是可选的，由系统根据 job 数量自动分配，不设置默认值
    
    @staticmethod
    def _validate_enums(config: Dict[str, Any]):
        """
        验证枚举值
        
        Args:
            config: config 字典
            
        Raises:
            ValueError: 枚举值无效
        """
        # 验证 base_term
        base_term = config["base_term"]
        valid_terms = [term.value for term in KlineTerm]
        if base_term not in valid_terms:
            raise ValueError(
                f"base_term 必须是 {valid_terms} 之一（使用 KlineTerm 枚举），"
                f"当前值: {base_term}"
            )
        
        # 验证 required_terms（如果存在）
        required_terms = config.get("required_terms", [])
        if required_terms:
            for term in required_terms:
                if term not in valid_terms:
                    raise ValueError(
                        f"required_terms 中的值必须是 {valid_terms} 之一（使用 KlineTerm 枚举），"
                        f"当前值: {term}"
                    )
        
        # 验证 performance 中的枚举值（performance 是必需字段）
        perf = config["performance"]
        
        # 验证 update_mode（必需字段）
        update_mode = perf["update_mode"]
        valid_modes = [mode.value for mode in UpdateMode]
        if update_mode not in valid_modes:
            raise ValueError(
                f"update_mode 必须是 {valid_modes} 之一（使用 UpdateMode 枚举），"
                f"当前值: {update_mode}"
            )
        
        # 验证 on_version_change（必需字段）
        on_version_change = perf["on_version_change"]
        valid_actions = [action.value for action in VersionChangeAction]
        if on_version_change not in valid_actions:
            raise ValueError(
                f"on_version_change 必须是 {valid_actions} 之一（使用 VersionChangeAction 枚举），"
                f"当前值: {on_version_change}"
            )
```

## 📝 使用示例

### 基本使用

```python
from app.tag.config_processor import ConfigProcessor

# 加载 settings（相对于 calculator 同级目录）
calculator_path = "app/tag/tags/example/calculator.py"
config = ConfigProcessor.load_config("settings.py", calculator_path)

# 使用 config
print(config["meta"]["name"])  # "EXAMPLE_TAG"
print(config["base_term"])     # "daily"
```

### 错误处理

```python
from app.tag.config_processor import ConfigProcessor

try:
    calculator_path = "app/tag/tags/example/calculator.py"
    config = ConfigProcessor.load_config("settings.py", calculator_path)
except FileNotFoundError as e:
    print(f"Settings 文件不存在: {e}")  # 直接抛错，因为 calculator 必须有一个配置文件
except ValueError as e:
    print(f"配置验证失败: {e}")  # 包括 is_enabled = False 的情况
except SyntaxError as e:
    print(f"语法错误: {e}")
except ImportError as e:
    print(f"导入错误: {e}")
```

## ✅ 已确定的设计决策

1. **is_enabled 的位置**：`config["is_enabled"]`（根级别）
   - 默认值：`False`（如果未配置）
   - 找不到字段：给 warning，按 False 执行（跳过）
   - 有字段且为 False：明确抛出 ValueError，告诉用户 tag 被 disable 了

2. **settings 文件路径**：相对于 calculator 同级目录
   - 统一命名为 `settings.py`
   - 如果 calculator 在 `app/tag/tags/example/calculator.py`
   - 则 settings 在 `app/tag/tags/example/settings.py`

3. **必需字段**：
   - `meta`: 必需，字典（元信息）
   - `base_term`: 必需，字符串（枚举值）
   - `performance`: 必需，字典（包含必需子字段）
   - `performance.update_mode`: 必需且在枚举中
   - `performance.on_version_change`: 必需且在枚举中
   - `core`: 可选，None 或不存在也可以
   - `performance.max_worker`: 可选，默认按照 job 数量自动分配
   - `required_terms`: 可选，默认 []
   - `required_data`: 可选，默认 []

4. **找不到 config 文件**：直接抛出 `FileNotFoundError`（因为 calculator 必须有一个配置文件）

5. **config 文件的 validate_config 函数**：可选，如果存在则调用（双重验证）

## ✅ 设计原则

1. **早期验证**：在加载时就验证，避免后续错误
2. **明确错误**：错误信息要清晰，指出具体问题
3. **默认值处理**：自动应用默认值，减少用户配置
4. **类型安全**：验证字段类型，避免运行时错误
5. **枚举验证**：严格验证枚举值，减少输入错误
