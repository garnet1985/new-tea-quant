# Adapter 架构文档

**版本：** `0.3.0`

## 模块介绍

`modules.adapter` 定义策略扫描产物的**消费侧扩展点**：用户继承 `BaseOpportunityAdapter` 实现 `process`。框架在 **`strategy`** 的 Scanner 管线末尾通过 **`AdapterDispatcher`** 按配置名从 `userspace.extensions.adapters.<name>.adapter` 动态加载并执行；本模块提供 **`Adapter.validate`** 供设置校验，以及 **`HistoryLoader`** 读取价格模拟落盘结果以辅助展示。

## 架构

```text
Adapter (Facade)
  └── validate → core/adapter_validator.AdapterValidator
contracts
  ├── BaseOpportunityAdapter → core/base_adapter
  └── HistoryLoader          → core/history_loader
core/loader.AdapterLoader    # 与 strategy.AdapterDispatcher 共用加载规则
```

## 边界

**In scope：** adapter 契约、userspace 目录约定、校验、历史模拟摘要加载  
**Out of scope：** 扫描调度、具体业务 adapter、下单/风控；`AdapterDispatcher` 归属 `modules.strategy`

## 相关文档

- [DESIGN.md](./DESIGN.md)
- [API.md](../API.md)
