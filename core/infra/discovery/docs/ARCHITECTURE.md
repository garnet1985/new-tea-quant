# Discovery 架构文档

**版本：** `0.2.0`

---

## 模块介绍

`infra.discovery` 为 NTQ 提供可配置的包扫描能力：在约定目录结构下发现子类、模块级对象，以及按全限定类名做定点加载与属性解析。

---

## 模块目标

- 用统一方式替代分散的 `pkgutil` / `importlib` 手写扫描逻辑。
- 支持可插拔的过滤、键提取与附加元数据提取。
- 在扩展缺失或损坏时以日志为主、不中断整体发现流程。
- 对高频类发现路径提供进程内缓存。

---

## 模块职责与边界

**职责（In scope）**

- 按包路径与命名模式导入子模块并收集类型或对象。
- 提供单次类发现的缓存与清理。
- 提供基于全限定名的单类加载与属性回退策略（类属性 + 模块级约定名）。

**边界（Out of scope）**

- 不定义业务基类（由 data_source、strategy 等模块提供）。
- 不负责配置热更新、文件监视或跨进程缓存失效。
- 不实现并行扫描或插件版本协商。

---

## 依赖说明

- 无模块级 YAML 依赖；实现仅依赖 Python 标准库。

---

## 工作拆分

- `ClassDiscovery`（`class_discovery.py`）：在基础包下对每个**子包**按模式加载目标模块，筛选 `DiscoveryConfig.base_class` 的子类，合并 `attribute_extractors` 元数据，并维护 `base_module_path` 级缓存。
- `ModuleDiscovery`（`module_discovery.py`）：在基础包下枚举一级子模块名，按模式导入并读取指定名称的模块属性；可选基于 `Path` 列举子目录再映射为模块名。
- `DiscoveryConfig` / `DiscoveryResult`（`class_discovery.py`）：描述发现规则与一次发现的 `classes` + `metadata` 结果容器。
- `discover_subclasses`（`class_discovery.py`）：用默认 `DiscoveryConfig` 构造 `ClassDiscovery` 并仅返回 `classes` 字典的便捷函数。
- `__init__.py`：导出上述公共符号。

---

## 架构/流程图

```text
类枚举: 调用方 -> ClassDiscovery.discover(base_module_path)
         -> import 基础包 -> pkgutil 子包 -> 按 module_name_pattern import
         -> 模块内筛子类 -> DiscoveryResult（可选写入缓存）

模块对象: 调用方 -> ModuleDiscovery.discover_objects
         -> import 基础包 -> 一级子模块名 -> 按 module_pattern import -> getattr(object_name)

定点加载: discover_class_by_path / discover_class_attribute
         -> importlib 加载模块 -> getattr
```

```text
ClassDiscovery（实例级 _cache）
ModuleDiscovery（无缓存；静态方法）
```

---

## 相关文档

- [详细设计](./DESIGN.md)：扫描规则、键冲突、属性约定与缓存语义。
- [API](./API.md)、[决策记录](./DECISIONS.md)
