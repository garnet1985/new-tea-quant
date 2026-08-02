# Trace（`infra.trace`）

匿名 usage 上报。**默认关闭**（opt-in）。静态 Facade：`Trace`。

## 布局

```text
core/infra/trace/
├── trace.py / contracts.py
├── API.md / QUICKSTART.md / glossary.yaml
├── core/services/
├── __test__/
└── docs/
```

## 快速开始

见 [QUICKSTART.md](./QUICKSTART.md)。

```python
from core.infra.trace import Trace

Trace.ask_permission(source="cli")
Trace.track("install.complete", {"success": True})
```

## 相关文档

- [API.md](./API.md)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
