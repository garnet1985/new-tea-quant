# Discovery 模块 API 文档

本文档采用统一 API 条目格式：函数名、状态、描述、诞生版本、参数（三列表格）、返回值。仅列出 `core.infra.discovery` 对外导出且由业务代码直接使用的入口。

---

## DiscoveryResult

### 函数名
`DiscoveryResult`

- 状态：`stable`
- 描述：`ClassDiscovery.discover` 的聚合结果类型（`@dataclass`）：`classes` 为注册键到类；`metadata` 为 `DiscoveryConfig.attribute_extractors` 的汇总。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `classes` (可选) | `Dict[str, Type]` | 字段；默认空映射 |
| `metadata` (可选) | `Dict[str, Any]` | 字段；默认空映射 |

- 返回值：数据类实例（无额外构造语义）。

---

## DiscoveryConfig

### 函数名
`DiscoveryConfig`

- 状态：`stable`
- 描述：`ClassDiscovery` 的规则载体（`@dataclass`）：基类、模块路径模式、过滤与键提取、附加属性提取及跳过集合。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `base_class` | `Type` | 必填 |
| `module_name_pattern` | `str` | 必填；`str.format` 占位符 `base_module`、`name` |
| `class_filter` (可选) | `Optional[Callable[[Type], bool]]` | 额外过滤 |
| `key_extractor` (可选) | `Optional[Callable[[Type], str]]` | 注册键；未提供则用类名 |
| `attribute_extractors` (可选) | `Dict[str, Callable[[Type], Any]]` | 默认 `{}` |
| `skip_modules` (可选) | `Set[str]` | 默认含 `__pycache__`、`__init__` |
| `skip_classes` (可选) | `Set[str]` | 默认空集 |

- 返回值：`DiscoveryConfig` 实例。

---

## ClassDiscovery

### 函数名
`ClassDiscovery(config: DiscoveryConfig)`

- 状态：`stable`
- 描述：创建类发现器实例。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `config` | `DiscoveryConfig` | 必填 |

- 返回值：`ClassDiscovery`

### 函数名
`discover(base_module_path: str, use_cache: bool = True) -> DiscoveryResult`

- 状态：`stable`
- 描述：在指定基础包下按配置发现子类；可选使用实例级缓存。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `base_module_path` | `str` | 必填；已安装的 Python 包路径 |
| `use_cache` (可选) | `bool` | 默认 `True` |

- 返回值：`DiscoveryResult`。基础包不存在时返回空结果并打 debug；未捕获异常打 error 后仍返回已收集结果。仅遍历基础包下 **`ispkg` 为真的子包**；重复键保留先加入的类并 `warning`。

### 函数名
`discover_class_by_path(class_path: str, base_class: Optional[Type] = None) -> Optional[Type]`

- 状态：`stable`
- 描述：按全限定名加载单个类，可选校验基类。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `class_path` | `str` | 必填；`包.模块.类名` |
| `base_class` (可选) | `Optional[Type]` | 提供时校验 `issubclass` |

- 返回值：`Type` 或 `None`。模块缺失为 debug；其他异常为 warning。

### 函数名
`discover_class_attribute(class_path: str, attribute_name: str, default: Any = None) -> Any`

- 状态：`stable`
- 描述：先读类属性；失败则在模块上查找 `类名 + attribute_name.capitalize()`（`capitalize` 仅首字母大写，如 `config_class` → `Config_class`）。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `class_path` | `str` | 必填 |
| `attribute_name` | `str` | 必填 |
| `default` (可选) | `Any` | 默认 `None` |

- 返回值：属性值或 `default`。

### 函数名
`clear_cache(base_module_path: Optional[str] = None) -> None`

- 状态：`stable`
- 描述：清除类发现缓存；传入路径则只删该键，否则清空全部。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `base_module_path` (可选) | `Optional[str]` | 默认 `None` 表示清空全部缓存 |

- 返回值：`None`

---

## discover_subclasses

### 函数名
`discover_subclasses(base_class: Type, base_module_path: str, module_name_pattern: str = "{base_module}.{name}", key_extractor: Optional[Callable[[Type], str]] = None, class_filter: Optional[Callable[[Type], bool]] = None) -> Dict[str, Type]`

- 状态：`stable`
- 描述：构造 `DiscoveryConfig` 与 `ClassDiscovery` 并执行一次 `discover`，仅返回 `classes` 字典。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `base_class` | `Type` | 必填 |
| `base_module_path` | `str` | 必填 |
| `module_name_pattern` (可选) | `str` | 默认 `"{base_module}.{name}"` |
| `key_extractor` (可选) | `Optional[Callable[[Type], str]]` | 默认 `None` |
| `class_filter` (可选) | `Optional[Callable[[Type], bool]]` | 默认 `None` |

- 返回值：`Dict[str, Type]`

---

## ModuleDiscovery

### 函数名
`discover_objects(base_module_path: str, object_name: str, module_pattern: str = "{base_module}.{name}", skip_modules: set = None) -> Dict[str, Any]`

- 状态：`stable`
- 描述：`ModuleDiscovery` 的静态方法。在基础包的一级子模块上按 `module_pattern` 导入并读取 `object_name`；不要求子项为包（与 `ClassDiscovery.discover` 不同）。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `base_module_path` | `str` | 必填 |
| `object_name` | `str` | 必填；模块内属性名，如 `SCHEMA` |
| `module_pattern` (可选) | `str` | 默认 `"{base_module}.{name}"` |
| `skip_modules` (可选) | `set` | 默认 `None` 时使用 `{"__pycache__", "__init__"}` |

- 返回值：`Dict[str, Any]`。基础包不存在返回 `{}`；缺对象或导入失败则跳过。

### 函数名
`discover_modules_by_path(base_path: Path, module_pattern: str, object_name: Optional[str] = None) -> Dict[str, Any]`

- 状态：`stable`
- 描述：`ModuleDiscovery` 的静态方法。遍历 `base_path` 下一级子目录（跳过 `_` 前缀），将目录名代入 `module_pattern`（仅 `name` 占位符）后导入；给定 `object_name` 则取属性，否则返回模块对象。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `base_path` | `Path` | 必填 |
| `module_pattern` | `str` | 必填；仅 `format(name=...)` |
| `object_name` (可选) | `Optional[str]` | 默认 `None` 时返回模块对象 |

- 返回值：`Dict[str, Any]`。路径不存在返回 `{}`。

---

## 示例

### 类发现（`ClassDiscovery` + `DiscoveryConfig`）

将 `YourBase` 换为项目中的抽象基类；`your_package.plugins` 为实际包路径。

```python
from core.infra.discovery import ClassDiscovery, DiscoveryConfig

# from myapp.plugin_base import YourBase

# config = DiscoveryConfig(
#     base_class=YourBase,
#     module_name_pattern="{base_module}.{name}.plugin",
#     key_extractor=lambda cls: getattr(cls, "plugin_name", None) or None,
#     class_filter=lambda cls: bool(getattr(cls, "plugin_name", None)),
# )
# result = ClassDiscovery(config).discover("myapp.plugins")
# for name, cls in result.classes.items():
#     print(name, cls)
```

### 便捷函数（`discover_subclasses`）

```python
from core.infra.discovery import discover_subclasses

# from myapp.plugin_base import YourBase
# classes = discover_subclasses(
#     YourBase,
#     "myapp.plugins",
#     module_name_pattern="{base_module}.{name}.plugin",
#     key_extractor=lambda c: getattr(c, "plugin_name", None),
# )
```

### 模块对象发现（`ModuleDiscovery.discover_objects`）

```python
from core.infra.discovery import ModuleDiscovery

schemas = ModuleDiscovery().discover_objects(
    base_module_path="userspace.data_source.handlers",
    object_name="SCHEMA",
    module_pattern="{base_module}.{name}.schema",
)
```

### 路径驱动发现（`discover_modules_by_path`）

不存在或空目录时返回空字典，便于在 CI 中 smoke：

```python
from pathlib import Path
from core.infra.discovery import ModuleDiscovery

assert ModuleDiscovery.discover_modules_by_path(
    base_path=Path("/path/does/not/exist"),
    module_pattern="pkg.{name}",
) == {}
```

---

## 相关文档

- [架构总览](./ARCHITECTURE.md)
- [详细设计](./DESIGN.md)
- [决策记录](./DECISIONS.md)
