# Task Guard（`infra.task_guard`）

长任务互斥：同时只允许一个全局长任务（Tag / Strategy / renew 等）占用资源。

**不是** job queue / 多任务 pipeline 调度；将来若有真 pipeline，本能力可并入或舍弃。

## 布局

```text
core/infra/task_guard/
├── task_guard.py   # Facade
├── contracts.py
├── core/lease/     # TaskLease 实现 + __test__
├── __test__/
└── docs/
```

## 快速开始

见 [QUICKSTART.md](./QUICKSTART.md)。

```python
from core.infra.task_guard import TaskGuard

TaskGuard.read_status()
```

## 相关文档

- [API.md](./API.md)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
