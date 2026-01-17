# Discovery Module 设计文档

## 📋 设计背景

框架中有很多地方需要自动发现功能：
- Provider 发现（`provider_instance_pool.py`）
- Handler Config 发现（`data_source_definition.py`）
- Schema 发现（`data_source_manager.py`）
- Strategy Worker 发现（`strategy_discovery_helper.py`）
- Adapter 发现（`adapter_dispatcher.py`）
- Base Tables 发现（`data_manager.py`）

这些代码有大量重复模式，需要抽象成通用工具。

## 🎯 设计目标

1. **统一接口**：所有自动发现都使用相同的接口
2. **灵活配置**：通过配置类灵活定义发现规则
3. **缓存机制**：自动缓存发现结果，避免重复扫描
4. **约定优于配置**：支持约定命名（如 `HandlerClassName + "Config"`）
5. **错误容忍**：发现失败不会中断流程

## 🏗️ 架构设计

### 核心组件

1. **ClassDiscovery**：类自动发现工具
   - 扫描包结构
   - 查找继承特定基类的类
   - 提取类属性
   - 缓存结果

2. **ModuleDiscovery**：模块自动发现工具
   - 扫描模块
   - 提取模块中的对象（如 `SCHEMA`, `CONFIG`）

3. **DiscoveryConfig**：发现配置
   - 定义发现规则
   - 支持过滤和提取函数

### 使用模式

```python
# 模式 1: 发现子类
config = DiscoveryConfig(
    base_class=BaseProvider,
    module_name_pattern="{base_module}.{name}.provider",
    key_extractor=lambda cls: getattr(cls, 'provider_name', None)
)
discovery = ClassDiscovery(config)
result = discovery.discover("userspace.data_source.providers")

# 模式 2: 发现模块对象
discovery = ModuleDiscovery()
schemas = discovery.discover_objects(
    base_module_path="userspace.data_source.handlers",
    object_name="SCHEMA",
    module_pattern="{base_module}.{name}.schema"
)

# 模式 3: 发现类属性
config_class = discovery.discover_class_attribute(
    class_path="userspace.data_source.handlers.kline.KlineHandler",
    attribute_name="config_class"
)
```

## 🔄 迁移策略

### 阶段 1: 创建工具（已完成）
- ✅ 创建 `ClassDiscovery` 和 `ModuleDiscovery`
- ✅ 提供统一接口和配置

### 阶段 2: 逐步迁移（建议）
- 迁移 `provider_instance_pool.py` 使用 `ClassDiscovery`
- 迁移 `data_source_manager.py` 使用 `ModuleDiscovery`
- 迁移 `data_source_definition.py` 使用 `discover_class_attribute`
- 迁移其他发现逻辑

### 阶段 3: 清理（未来）
- 删除重复的发现代码
- 统一使用 `discovery` 模块

## 📝 设计决策

### 1. 为什么放在 `core/infra`？

- `infra` 是基础设施层，自动发现属于基础设施功能
- 与 `project_context`、`db`、`worker` 同级，职责清晰

### 2. 为什么分离 `ClassDiscovery` 和 `ModuleDiscovery`？

- 职责不同：类发现 vs 模块对象发现
- 使用场景不同：类发现更复杂，需要过滤和提取；模块发现更简单
- 保持接口简洁

### 3. 为什么使用 `DiscoveryConfig`？

- 配置与逻辑分离
- 支持灵活的自定义规则
- 易于测试和扩展

### 4. 缓存机制

- 默认启用缓存，避免重复扫描
- 支持手动清除缓存
- 多进程环境需要重新扫描（由调用方处理）

## 🚀 未来扩展

1. **插件系统**：支持自定义发现策略
2. **性能优化**：并行扫描、增量发现
3. **监控和统计**：记录发现耗时、成功率
4. **验证机制**：发现后自动验证类的有效性
