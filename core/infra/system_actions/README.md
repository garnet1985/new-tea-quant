# System Actions（`infra.system_actions`）

系统级操作：全局 pipeline 租约。

## 布局

```text
core/infra/system_actions/
├── system_actions.py   # Facade
├── contracts.py
├── core/
│   └── pipeline_lease/  # 内部实现 + __test__
├── __test__/
└── docs/
```

## 快速开始

见 [QUICKSTART.md](./QUICKSTART.md)。

```python
from core.infra.system_actions import SystemActions

SystemActions.pipeline.read_status()
```

从模板新建策略 / Tag：`cli.py -n`（`core.infra.cli.user.scripts.create_from_template`）。

## 相关文档

- [API.md](./API.md)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
