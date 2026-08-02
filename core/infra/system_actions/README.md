# System Actions（`infra.system_actions`）

系统级操作：缓存清理、全局 pipeline 租约、从模板新建策略 / Tag。

## 布局

```text
core/infra/system_actions/
├── system_actions.py   # Facade
├── contracts.py
├── API.md / QUICKSTART.md / glossary.yaml
├── cache_cleanup/      # 内部实现
├── shortcuts/          # 内部实现
├── __test__/
└── docs/
```

## 快速开始

见 [QUICKSTART.md](./QUICKSTART.md)。

```python
from core.infra.system_actions import SystemActions

SystemActions.pipeline.read_status()
```

## 相关文档

- [API.md](./API.md)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
