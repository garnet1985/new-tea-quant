# Discovery 模块 API 文档

按「描述、函数签名、参数、输出、示例」列出 Discovery 模块中**用户会直接使用的入口**；内部辅助函数不列入。架构与设计见 `architecture.md` / `decisions.md`，快速上手见 `overview.md`。

---

## ClassDiscovery

### ClassDiscovery（构造函数）

**描述**：创建类发现器，用于在某个包下按配置规则自动发现继承某基类的所有子类，并提取指定属性。

**函数签名**：`ClassDiscovery(config: DiscoveryConfig)`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `config` | `DiscoveryConfig` | 发现配置，定义基类、模块名模式、过滤函数、键提取函数等 |

**输出**：无（构造实例）

**Example**：

```python
from core.infra.discovery import ClassDiscovery, DiscoveryConfig
from core.modules.data_source.base_provider import BaseProvider

config = DiscoveryConfig(
    base_class=BaseProvider,
    module_name_pattern="userspace.data_source.providers.{name}.provider",
    key_extractor=lambda cls: getattr(cls, "provider_name", None),
    class_filter=lambda cls: hasattr(cls, "provider_name") and cls.provider_name,
)
discovery = ClassDiscovery(config)
```

---

### discover

**描述**：在指定基础包下自动发现所有符合配置规则的子类，返回 `DiscoveryResult`（`classes` + `metadata`）。

**函数签名**：`ClassDiscovery.discover(base_module_path: str, use_cache: bool = True) -> DiscoveryResult`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `base_module_path` | `str` | 基础模块路径，如 `"userspace.data_source.providers"` |
| `use_cache` | `bool` | 是否使用缓存结果，默认 `True` |

**输出**：`DiscoveryResult` ——  
- `classes`: `{key: class}` 映射  
- `metadata`: `{attr_name: {key: value}}` 的属性提取结果（若在 `config.attribute_extractors` 中配置）

**Example**：

```python
result = discovery.discover("userspace.data_source.providers")
for name, provider_cls in result.classes.items():
    print(name, provider_cls)
```

---

### discover_class_by_path

**描述**：通过完整路径加载单个类，并可选验证其是否继承某基类。

**函数签名**：`ClassDiscovery.discover_class_by_path(class_path: str, base_class: Optional[Type] = None) -> Optional[Type]`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `class_path` | `str` | 类完整路径，如 `"userspace.data_source.handlers.kline.KlineHandler"` |
| `base_class` | `Type \| None` | 可选基类，提供时会验证返回类是否为其子类 |

**输出**：`Optional[Type]` —— 找到则返回类对象，否则返回 `None`。

**Example**：

```python
handler_cls = discovery.discover_class_by_path(
    "userspace.data_source.handlers.kline.KlineHandler",
)
```

---

### discover_class_attribute

**描述**：根据类路径发现某个类属性（如 `config_class`），支持「类属性」和「约定命名（ClassName + AttributeName.capitalize）」两种策略。

**函数签名**：`ClassDiscovery.discover_class_attribute(class_path: str, attribute_name: str, default: Any = None) -> Any`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `class_path` | `str` | 类完整路径 |
| `attribute_name` | `str` | 属性名，如 `"config_class"` |
| `default` | `Any` | 未找到时返回的默认值 |

**输出**：`Any` —— 找到的属性值或默认值。

**Example**：

```python
config_cls = discovery.discover_class_attribute(
    "userspace.data_source.handlers.kline.KlineHandler",
    attribute_name="config_class",
    default=None,
)
```

---

### clear_cache

**描述**：清空发现结果缓存，用于变更代码或动态加载模块后的刷新。

**函数签名**：`ClassDiscovery.clear_cache(base_module_path: Optional[str] = None) -> None`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `base_module_path` | `str \| None` | 基础模块路径；为 `None` 时清空所有缓存 |

**输出**：`None`

---

## ModuleDiscovery

### discover_objects

**描述**：在指定基础包下，按模块命名约定加载子模块，并提取其中名称为 `object_name` 的对象（如 `SCHEMA`、`CONFIG`）。

**函数签名**：`ModuleDiscovery.discover_objects(base_module_path: str, object_name: str, module_pattern: str = "{base_module}.{name}", skip_modules: set | None = None) -> Dict[str, Any]`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `base_module_path` | `str` | 基础模块路径，如 `"userspace.data_source.handlers"` |
| `object_name` | `str` | 目标对象名，如 `"SCHEMA"`、`"CONFIG"` |
| `module_pattern` | `str` | 子模块路径模式，默认 `"{base_module}.{name}"` |
| `skip_modules` | `set \| None` | 需要跳过的模块名集合，默认跳过 `__pycache__` / `__init__` 及下划线开头模块 |

**输出**：`Dict[str, Any]` —— `{模块名: 对象}` 映射。

**Example**：

```python
from core.infra.discovery import ModuleDiscovery

schemas = ModuleDiscovery.discover_objects(
    base_module_path="userspace.data_source.handlers",
    object_name="SCHEMA",
    module_pattern="{base_module}.{name}.schema",
)
```

---

### discover_modules_by_path

**描述**：根据文件路径（而非包结构）发现模块或模块中的某个对象，适合 userspace 目录结构不完全遵守包规范时使用。

**函数签名**：`ModuleDiscovery.discover_modules_by_path(base_path: Path, module_pattern: str, object_name: Optional[str] = None) -> Dict[str, Any]`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `base_path` | `Path` | 基础路径，如 `PathManager.data_source_handlers()` |
| `module_pattern` | `str` | 模块路径模式，如 `"userspace.data_source.handlers.{name}.schema"` |
| `object_name` | `str \| None` | 要提取的对象名；为 `None` 时返回整个模块 |

**输出**：`Dict[str, Any]` —— `{目录名: 模块或对象}` 映射。

**Example**：

```python
from pathlib import Path
from core.infra.discovery import ModuleDiscovery
from core.infra.project_context import PathManager

base_path = PathManager.data_source_handlers()
schemas = ModuleDiscovery.discover_modules_by_path(
    base_path=base_path,
    module_pattern="userspace.data_source.handlers.{name}.schema",
    object_name="SCHEMA",
)
```

---

## discover_subclasses（便捷函数）

### discover_subclasses

**描述**：简化版类发现工具，在给定包下发现所有继承指定基类的子类，返回 `{key: class}` 字典。

**函数签名**：`discover_subclasses(base_class: Type, base_module_path: str, module_name_pattern: str = "{base_module}.{name}", key_extractor: Optional[Callable[[Type], str]] = None, class_filter: Optional[Callable[[Type], bool]] = None) -> Dict[str, Type]`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `base_class` | `Type` | 需要发现的基类 |
| `base_module_path` | `str` | 基础模块路径 |
| `module_name_pattern` | `str` | 子模块路径模式，默认 `"{base_module}.{name}"` |
| `key_extractor` | `Callable[[Type], str] \| None` | 从类中提取键（如 `provider_name`）的函数 |
| `class_filter` | `Callable[[Type], bool] \| None` | 类过滤函数，返回 `True` 才保留 |

**输出**：`Dict[str, Type]` —— `{key: class}` 字典。

**Example**：

```python
from core.infra.discovery import discover_subclasses
from core.modules.data_source.base_provider import BaseProvider

providers = discover_subclasses(
    base_class=BaseProvider,
    base_module_path="userspace.data_source.providers",
    module_name_pattern="{base_module}.{name}.provider",
    key_extractor=lambda cls: getattr(cls, "provider_name", None),
)
```

