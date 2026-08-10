# Adapter 架构文档

**版本：** `0.3.0`

## 模块介绍

`modules.adapter` 定义策略扫描产物的**消费侧扩展点**：用户继承 `BaseOpportunityAdapter` 实现 `process`。框架在 **`strategy`** 的 Scanner 管线末尾通过 **`AdapterDispatcher`** 按配置名从 `userspace.extensions.adapters.<name>.adapter` 动态加载并执行；本模块提供 **`Adapter.validate` / `Adapter.load_class`**。额外展示数据（如 price 历史）由 strategy **推入 `context`**，本模块不回读模拟产物。

## 架构

```text
Adapter (Facade)
  └── validate / load_class → core/adapter_validator + core/loader
contracts
  └── BaseOpportunityAdapter → core/base_adapter
core/loader.AdapterLoader    # 与 strategy.AdapterDispatcher 共用加载规则
```

## 边界

**In scope：** adapter 契约、userspace 目录约定、校验与动态加载  
**Out of scope：** 扫描调度、模拟产物读取、具体业务 adapter、下单/风控；`AdapterDispatcher` 与 `price_history` 组装归属 `modules.strategy`

## 相关文档

- [DESIGN.md](./DESIGN.md)
- [API.md](../API.md)
