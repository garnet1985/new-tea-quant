# Adapter（`modules.adapter`）

策略 **Scanner** 完成后，将机会列表与 `context` 交给 userspace **adapter** 做后续处理。对外门面为 `Adapter`；基类见 `contracts`。

## 布局

```text
core/modules/adapter/
├── adapter.py          # Facade Adapter
├── contracts.py        # BaseOpportunityAdapter
├── core/
│   ├── base_adapter.py
│   ├── adapter_validator.py
│   └── loader.py       # userspace 动态加载（内部）
├── API.md / QUICKSTART.md / glossary.yaml
├── __test__/
└── docs/
```

## 适用场景

- 设置校验阶段确认 adapter 可加载（`Adapter.validate`）
- 编写 userspace adapter 时继承 `BaseOpportunityAdapter`，从 `context` 取 strategy 推送的字段（如 `price_history`）

## 模块依赖

- `infra.project_context`

## 常见问题

**Q：该 import 什么？**  
A：`from core.modules.adapter import Adapter`；基类 `from core.modules.adapter.contracts import BaseOpportunityAdapter`。

**Q：历史胜率从哪来？**  
A：strategy `AdapterDispatcher` 写入 `context["price_history"]`；adapter 只读 context，不回读磁盘产物。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [测试用例](./__test__/TEST_CASES.md)
