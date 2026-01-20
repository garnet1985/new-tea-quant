# Discovery 模块概览

> **快速入门指南**：本文档介绍 Discovery 模块的用途、核心概念、目录结构和常见用法。详细设计请参考 [architecture.md](./architecture.md)。

---

## 模块简介

**Discovery 模块**是一个通用的「自动发现工具」，用于在约定路径下自动发现：

- 某个基类的所有子类（如 Provider / Handler / Strategy Worker / Adapter 等）
- 某个模块中约定名称的对象（如 `SCHEMA`、`CONFIG`）
- 某个类上的特定属性（如 Handler 的 `config_class`）

它的目标是**统一框架中的自动发现逻辑**，避免在各个业务模块里重复写扫描 / import / 过滤的代码。

---

## 核心特性

- **统一接口**：不同场景（类发现 / 模块发现 / 属性发现）共用一致的调用风格
- **约定优于配置**：大量使用命名约定（如 `{base_module}.{name}.provider`）
- **高度可配置**：通过 `DiscoveryConfig` 灵活定义过滤和键提取规则
- **缓存机制**：自动缓存扫描结果，避免重复导入模块
- **错误容忍**：某些模块加载失败只记录日志，不中断整个流程

---

## 核心概念

| 概念 | 说明 |
|------|------|
| **DiscoveryConfig** | 描述「怎么发现」的一组规则：基类、模块名模式、过滤函数、键提取函数等 |
| **ClassDiscovery** | 用于在指定包下发现继承某个基类的所有子类，并按键组织结果 |
| **ModuleDiscovery** | 用于在指定包下发现模块中的某个对象（如 `SCHEMA`） |
| **discover_subclasses** | 简化版类发现工具，封装常见模式 |

---

## 文件夹结构

```text
core/infra/discovery/
├── __init__.py              # 对外导出 ClassDiscovery / ModuleDiscovery / DiscoveryConfig 等
├── class_discovery.py       # ClassDiscovery 实现
├── module_discovery.py      # ModuleDiscovery 实现
└── __test__/                # 单元测试
    ├── README.md
    ├── test_class_discovery.py
    └── test_module_discovery.py

docs/architecture/discovery/
├── overview.md              # 本文件：快速概览与使用示例
├── architecture.md          # 详细架构与设计说明
└── decisions.md             # 关键设计决策记录
```

---

## 典型使用场景

### 1. 发现所有 Provider 实现

```python
from core.infra.discovery import ClassDiscovery, DiscoveryConfig
from core.modules.data_source.base_provider import BaseProvider

config = DiscoveryConfig(
    base_class=BaseProvider,
    module_name_pattern="userspace.data_source.providers.{name}.provider",
    key_extractor=lambda cls: getattr(cls, "provider_name", None),
    class_filter=lambda cls: hasattr(cls, "provider_name") and cls.provider_name
)

discovery = ClassDiscovery(config)
result = discovery.discover("userspace.data_source.providers")

for provider_name, provider_class in result.classes.items():
    print(provider_name, provider_class)
```

### 2. 发现 Handler 对应的 SCHEMA 模块

```python
from core.infra.discovery import ModuleDiscovery

discovery = ModuleDiscovery()
schemas = discovery.discover_objects(
    base_module_path="userspace.data_source.handlers",
    object_name="SCHEMA",
    module_pattern="{base_module}.{name}.schema",
)

# schemas 形如: {"kline": KlineSchema, "stock_list": StockListSchema}
```

### 3. 发现某个 Handler 的 config_class 属性

```python
from core.infra.discovery import ClassDiscovery, DiscoveryConfig

config = DiscoveryConfig(
    base_class=None,  # 可选：只按路径查找
)
discovery = ClassDiscovery(config)

config_class = discovery.discover_class_attribute(
    class_path="userspace.data_source.handlers.kline.KlineHandler",
    attribute_name="config_class",
    default=None,
)
```

---

## 简化接口：`discover_subclasses`

对于「只需要找所有子类」的简单场景，可以使用封装好的便捷函数：

```python
from core.infra.discovery.class_discovery import discover_subclasses
from core.modules.data_source.base_provider import BaseProvider

providers = discover_subclasses(
    base_class=BaseProvider,
    base_module_path="userspace.data_source.providers",
    module_name_pattern="{base_module}.{name}.provider",
    key_extractor=lambda cls: getattr(cls, "provider_name", None),
)
```

返回结果通常是一个 `{key: class}` 的字典，key 由 `key_extractor` 决定。

---

## 与其他模块的关系

- **与 DataSource 模块**：
  - 用于发现 Provider / Handler / SCHEMA / HandlerConfig 等
- **与 Strategy 模块**：
  - 用于发现 Strategy Worker、Adapter 等扩展类（规划 / 迁移中）
- **与 DataManager / DB 模块**：
  - 可用于发现 base_tables、Schema 定义等（规划 / 迁移中）

Discovery 自身不关心业务，只提供「怎么找到这些东西」的基础设施能力。

---

## 进一步阅读

- **[architecture.md](./architecture.md)**：Discovery 模块的设计背景、架构和组件说明
- **[decisions.md](./decisions.md)**：为什么要引入 Discovery、以及几个关键设计取舍
- **`core/infra/discovery/README.md`**：更贴近代码的 API 说明和示例

---

**文档结束**

