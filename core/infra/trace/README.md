# Trace（`infra.trace`）

匿名 usage 上报。**默认关闭**（opt-in）。静态 Facade：`Trace`。

## 布局

```text
core/infra/trace/
├── trace.py / contracts.py
├── core/
│   ├── defaults.py      # 内置 TARGET_URL 等（唯一源）
│   ├── services/
│   └── __test__/
├── __test__/
└── docs/
```

## 改上报地址

见 [`core/defaults.py`](./core/defaults.py) 或 `NTQ_TRACE_ENDPOINT` / `userspace/system/config/trace.json`。

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
- [docs/FEEDBACK.md](./docs/FEEDBACK.md)（应用内软反馈；**不**经 Trace.consent）

