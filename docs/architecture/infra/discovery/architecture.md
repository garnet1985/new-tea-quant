# Discovery 架构文档

**版本：** 3.0  
**最后更新**：2026-01-20

---

## 目录

- [设计背景与业务目标](#设计背景与业务目标)
- [设计目标](#设计目标)
- [整体架构](#整体架构)
- [核心组件与职责](#核心组件与职责)
- [运行时 Workflow](#运行时-workflow)
- [迁移策略](#迁移策略)
- [未来扩展方向](#未来扩展方向)

---

## 设计背景与业务目标

### 背景问题

在框架的发展过程中，出现了大量「自动发现」的需求：

- Provider 发现（如 `provider_instance_pool.py`）
- Handler Config 发现（`data_source_definition.py`）
- Schema 发现（`data_source_manager.py`）
- Strategy Worker 发现（`strategy_discovery_helper.py`）
- Adapter 发现（`adapter_dispatcher.py`）
- Base Tables / Schema 发现（`data_manager.py`）

早期这些逻辑分别散落在不同模块中，典型模式是：

- 使用 `pkgutil` / `importlib` 扫描某个包
- 手动 import 子模块
- 遍历模块中的类或对象
- 手动写过滤逻辑

问题是：

- 大量重复代码，容易 copy-paste 出 bug
- 错误处理不统一，有的静默失败，有的直接抛异常
- 接口风格不统一，后期很难迁移到统一的发现机制

### 业务目标

Discovery 模块的目标是：

1. **统一发现能力**：为框架中所有「按约定加载扩展」的场景提供统一实现
2. **减少重复代码**：用通用工具替代零散的扫描逻辑
3. **提高可维护性**：通过集中实现缓存、错误处理和日志
4. **保护用户体验**：发现失败时尽量不影响主流程（记录警告即可）

---

## 设计目标

基于上述背景，Discovery 的设计目标为：

1. **统一接口**
   - 类发现、模块对象发现、类属性发现共用相似的 API 风格
2. **高度可配置**
   - 通过 `DiscoveryConfig` 描述「发现规则」，而不是硬编码在函数里
3. **缓存机制**
   - 对相同路径的扫描结果做缓存，避免重复导入模块
4. **约定优于配置**
   - 支持以命名约定简化配置（如 `{base_module}.{name}.provider`）
5. **错误容忍**
   - 单个模块导入失败不影响整体结果，统一记录 warning

---

## 整体架构

### 模块划分

```text
core/infra/discovery/
├── __init__.py
├── class_discovery.py       # ClassDiscovery + discover_subclasses
├── module_discovery.py      # ModuleDiscovery
└── __test__/                # 单元测试
    ├── test_class_discovery.py
    └── test_module_discovery.py
```

Discovery 位于 `core/infra`，与 `db` / `worker` / `project_context` 同级，作为**基础设施能力**提供给上层业务模块使用。

### 高层关系图

```text
        上层业务模块
  (data_source / strategy / adapter / data_manager ...)
                    ▲
                    │ 使用自动发现能力
                    │
          ┌─────────┴─────────┐
          │                   │
   ClassDiscovery        ModuleDiscovery
          ▲                   ▲
          │ 依赖              │ 依赖
          └─────────┬────────┘
                    │
             DiscoveryConfig
                    │
                    ▼
           importlib / pkgutil / inspect
```

---

## 核心组件与职责

### DiscoveryConfig

**作用**：描述「发现规则」的配置类。

**常见字段（根据 README/DESIGN 抽象）：**

- `base_class`: 只发现继承此基类的类（可选）
- `module_name_pattern`: 模块命名模式，如 `"{base_module}.{name}.provider"`
- `class_filter`: 过滤函数，决定某个类是否被纳入结果
- `key_extractor`: 从类中提取 key 的函数（如 `provider_name`）
- `attribute_extractors`: 需要额外提取的属性映射（可选）
- `skip_modules` / `skip_classes`: 需要跳过的模块名 / 类名集合

**职责**：

- ✅ 提供声明式配置，解耦「规则」与「发现逻辑」
- ✅ 支持复用同一规则到多个路径
- ❌ 不直接执行任何扫描或导入操作

---

### ClassDiscovery

**作用**：在指定包下发现目标基类的所有子类，并根据规则组织结果。

**职责**：

- ✅ 遍历指定包（`base_module_path`）下的所有子模块
- ✅ 根据 `DiscoveryConfig` 中的 `module_name_pattern` 生成 import 路径
- ✅ 使用 `importlib` 导入模块
- ✅ 搜索继承 `base_class` 的类，并应用 `class_filter`
- ✅ 使用 `key_extractor` 生成 key（如 `provider_name`）
- ✅ 支持缓存发现结果，避免重复扫描
- ✅ 提供辅助方法：
  - `discover(...)`
  - `discover_class_by_path(class_path, base_class=None)`
  - `discover_class_attribute(class_path, attribute_name, default=None)`

**不负责**：

- ❌ 不决定「这些类怎么用」（由业务模块负责）
- ❌ 不处理多进程缓存同步（多进程下可重新扫描）

---

### ModuleDiscovery

**作用**：在指定包下发现模块中约定名称的对象（例如 `SCHEMA`、`CONFIG`）。

**职责**：

- ✅ 遍历指定包路径
- ✅ 通过 `module_pattern` 生成模块名并导入
- ✅ 在模块内查找指定对象名（如 `SCHEMA`）
- ✅ 将结果组织为 `{name: object}` 的形式返回

**不负责**：

- ❌ 不解析对象内部结构（例如 SCHEMA 的字段）
- ❌ 不关心对象的具体业务含义

---

### 便捷函数：`discover_subclasses`

定义在 `class_discovery.py` 中，用于简化最常见的「基类 + 包路径 + 命名约定」场景。

**典型参数**：

- `base_class`
- `base_module_path`
- `module_name_pattern`
- `key_extractor`

内部构建一个简单的 `DiscoveryConfig` 并调用 `ClassDiscovery`。

---

## 运行时 Workflow

以「发现 Provider 子类」为例：

```text
1. 上层模块定义规则
   - base_class = BaseProvider
   - base_module_path = "userspace.data_source.providers"
   - module_name_pattern = "{base_module}.{name}.provider"
   - key_extractor = provider_name

2. 构建 DiscoveryConfig

3. 创建 ClassDiscovery
   - discovery = ClassDiscovery(config)

4. 调用 discover()
   - for name in 子目录:
       - 生成 module_name = module_name_pattern.format(...)
       - import module_name
       - 遍历 module 中的所有类
       - 过滤出继承 BaseProvider 的类
       - 提取 provider_name 作为 key

5. 组织结果并返回
   - result.classes = {provider_name: provider_class}
```

以「发现 Handler 的 SCHEMA 模块」为例：

```text
1. 上层模块定义规则
   - base_module_path = "userspace.data_source.handlers"
   - module_pattern = "{base_module}.{name}.schema"
   - object_name = "SCHEMA"

2. 创建 ModuleDiscovery

3. 调用 discover_objects()
   - 对每个 name:
       - 生成 module_name
       - import module_name
       - 取出 module.SCHEMA
       - 放入结果 dict
```

错误处理策略：

- 模块导入失败：记录 warning，跳过该模块
- 类不符合过滤条件：静默忽略
- 某个路径完全没有结果：返回空 dict，由调用方决定如何处理

---

## 迁移策略

设计文档中给出的迁移步骤：

### 阶段 1：创建工具（已完成）

- ✅ 编写 `ClassDiscovery` 和 `ModuleDiscovery`
- ✅ 定义 `DiscoveryConfig` 和基础 API

### 阶段 2：逐步迁移（进行中 / 规划中）

- 将 `provider_instance_pool.py` 改为使用 `ClassDiscovery`
- 将 `data_source_manager.py` 的 SCHEMA 发现改为使用 `ModuleDiscovery`
- 将 `data_source_definition.py` 的 Handler Config 发现改为使用 `discover_class_attribute`
- 统一 Strategy / Adapter / DataManager 的发现逻辑

### 阶段 3：清理（规划中）

- 删除旧的手写扫描逻辑
- 在文档中统一推荐 Discovery 模块的使用方式

---

## 未来扩展方向

### 待实现扩展（单机版支持）

1. **更强的过滤与验证**
   - 在发现阶段就做简单验证（如必须有某些属性）
   - 提供 hook 让业务模块插入自定义校验逻辑
2. **性能优化**
   - 对大量模块的扫描支持简单的并发 / 分批扫描
   - 更细粒度的缓存策略（按模块级别缓存）
3. **更友好的调试输出**
   - 支持在 debug 模式下输出详细的「发现过程日志」
   - 提供工具打印当前所有已发现的类 / 模块对象

### 可扩展方向（超出当前单机版范围）

1. **插件系统**
   - 基于 Discovery 实现「插件目录」自动注册机制
   - 提供插件元数据发现与注册流程
2. **增量发现**
   - 结合文件系统监控，只对变更的模块重新扫描

---

## 相关文档

- `core/infra/discovery/README.md`：API 和使用示例
- `core/infra/discovery/DESIGN.md`：Discovery 模块原始设计记录
- [overview.md](./overview.md)：Discovery 概览与快速入门
- [decisions.md](./decisions.md)：关键设计决策记录

---

**文档结束**

