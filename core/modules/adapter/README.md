# Adapter（`modules.adapter`）

策略 **Scanner** 完成后，将 `Opportunity` 列表交给 userspace **adapter** 做后续处理。对外门面为 `Adapter`；基类与 `HistoryLoader` 见 `contracts`。

## 布局

```text
core/modules/adapter/
├── adapter.py          # Facade Adapter
├── contracts.py        # BaseOpportunityAdapter / HistoryLoader
├── core/
│   ├── base_adapter.py
│   ├── adapter_validator.py
│   ├── history_loader.py
│   └── loader.py       # userspace 动态加载（内部）
├── API.md / QUICKSTART.md / glossary.yaml
├── __test__/
└── docs/
```

## 适用场景

- 设置校验阶段确认 adapter 可加载（`Adapter.validate`）
- 编写 userspace adapter 时继承 `BaseOpportunityAdapter`

## 模块依赖

- `modules.strategy`（Opportunity 等）

## 常见问题

**Q：该 import 什么？**  
A：`from core.modules.adapter import Adapter`；基类 `from core.modules.adapter.contracts import BaseOpportunityAdapter`。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [测试用例](./__test__/TEST_CASES.md)
