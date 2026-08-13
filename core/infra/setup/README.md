# Setup（`infra.setup`）

安装编排、安装步骤、安装产物工厂。**不是** setuptools 的 `setup.py`。

**公开入口：** `from core.infra.setup import Setup`  
CLI / `install.py` / `launcher.py` / BFF **只调用门面**。应用升级见 `core.infra.updater`。

产物 zip 在 `initialization/userspace/`、`initialization/data/`（方便找到，不进本模块）。

## 布局

```text
core/infra/setup/
├── setup.py / contracts.py / __init__.py
├── core/
│   ├── env.py
│   ├── install_runtime.py / cli_runtime.py / ui_runtime.py
│   ├── steps/
│   └── scripts/
└── docs/ / __test__/
```

## 快速开始

见 [QUICKSTART.md](./QUICKSTART.md)。

```python
from core.infra.setup import Setup

Setup.runtime.needs_install("cli")
```

## 相关文档

- [API.md](./API.md)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
