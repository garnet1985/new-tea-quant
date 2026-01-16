# Discovery Module - 自动发现工具

## 📋 概述

提供通用的类、模块、配置自动发现功能，统一框架中的自动发现逻辑。

## 🎯 使用场景

- **Provider 发现**：自动发现所有 Provider 实现
- **Handler 发现**：自动发现 Handler 类及其 Config
- **Strategy Worker 发现**：自动发现策略 Worker 类
- **Adapter 发现**：自动发现适配器类
- **Schema 发现**：自动发现 Schema 定义

## 🚀 快速开始

### ClassDiscovery - 类自动发现

```python
from core.infra.discovery import ClassDiscovery, DiscoveryConfig
from core.modules.data_source.base_provider import BaseProvider

# 配置发现规则
config = DiscoveryConfig(
    base_class=BaseProvider,
    module_name_pattern="userspace.data_source.providers.{name}.provider",
    key_extractor=lambda cls: getattr(cls, 'provider_name', None),
    class_filter=lambda cls: hasattr(cls, 'provider_name') and cls.provider_name
)

# 执行发现
discovery = ClassDiscovery(config)
result = discovery.discover("userspace.data_source.providers")

# 使用结果
for provider_name, provider_class in result.classes.items():
    print(f"{provider_name}: {provider_class}")
```

### 便捷函数

```python
from core.infra.discovery.class_discovery import discover_subclasses

# 简单场景：发现所有子类
providers = discover_subclasses(
    base_class=BaseProvider,
    base_module_path="userspace.data_source.providers",
    module_name_pattern="{base_module}.{name}.provider",
    key_extractor=lambda cls: getattr(cls, 'provider_name', None)
)
```

### ModuleDiscovery - 模块自动发现

```python
from core.infra.discovery import ModuleDiscovery

# 发现所有 schema 模块
discovery = ModuleDiscovery()
schemas = discovery.discover_objects(
    base_module_path="userspace.data_source.handlers",
    object_name="SCHEMA",
    module_pattern="{base_module}.{name}.schema"
)

# schemas = {"kline": KlineSchema, "stock_list": StockListSchema}
```

### 发现类的属性

```python
from core.infra.discovery import ClassDiscovery

discovery = ClassDiscovery(config)

# 发现 Handler 的 config_class 属性
config_class = discovery.discover_class_attribute(
    class_path="userspace.data_source.handlers.kline.KlineHandler",
    attribute_name="config_class"
)
```

## 📖 API 文档

### DiscoveryConfig

发现配置类，定义发现规则。

**参数：**
- `base_class` (Type): 基类（只发现继承此类的子类）
- `module_name_pattern` (str): 模块名模式（如 `"{base_module}.{name}.provider"`）
- `class_filter` (Callable, optional): 类过滤函数
- `key_extractor` (Callable, optional): 键提取函数（从类中提取唯一标识）
- `attribute_extractors` (Dict, optional): 属性提取器字典
- `skip_modules` (Set, optional): 跳过的模块名集合
- `skip_classes` (Set, optional): 跳过的类名集合

### ClassDiscovery

类自动发现工具。

**主要方法：**
- `discover(base_module_path, use_cache=True)`: 发现指定包下的所有类
- `discover_class_by_path(class_path, base_class=None)`: 通过完整路径发现单个类
- `discover_class_attribute(class_path, attribute_name, default=None)`: 发现类的特定属性
- `clear_cache(base_module_path=None)`: 清除缓存

### ModuleDiscovery

模块自动发现工具。

**主要方法：**
- `discover_objects(...)`: 发现所有模块中的特定对象
- `discover_modules_by_path(...)`: 通过文件路径发现模块

## 🔧 迁移指南

### 从 provider_instance_pool.py 迁移

**之前：**
```python
def _scan_provider_package(self, package_path, base_module_path: str):
    for importer, modname, ispkg in pkgutil.iter_modules(package_path):
        # ... 手动扫描逻辑
```

**之后：**
```python
from core.infra.discovery import ClassDiscovery, DiscoveryConfig

config = DiscoveryConfig(
    base_class=BaseProvider,
    module_name_pattern=f"{base_module_path}.{{name}}.provider",
    key_extractor=lambda cls: getattr(cls, 'provider_name', None),
    class_filter=lambda cls: hasattr(cls, 'provider_name') and cls.provider_name
)
discovery = ClassDiscovery(config)
result = discovery.discover(base_module_path)
self._provider_classes = result.classes
```

## 📝 设计原则

1. **统一接口**：所有自动发现都使用相同的接口
2. **灵活配置**：通过 `DiscoveryConfig` 灵活配置发现规则
3. **缓存机制**：自动缓存发现结果，避免重复扫描
4. **约定优于配置**：支持约定命名（如 `HandlerClassName + "Config"`）
5. **错误容忍**：发现失败不会中断流程，只记录警告
