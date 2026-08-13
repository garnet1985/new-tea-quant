# Setup（安装域）

安装编排、安装步骤、安装产物工厂。**不是** setuptools 的 `setup.py`。

**公开入口：** `from setup import Setup`  
CLI / `install.py` / `launcher.py` / BFF **只调用门面**，不在 CLI 里实现安装逻辑。

## 布局

```text
setup/
├── setup.py / contracts.py / __init__.py    # 公开入口层
├── core/                                    # 内部实现
│   ├── env.py                               # NewTeaQuantSetup（venv / 路径）
│   ├── install_runtime.py / cli_runtime.py / ui_runtime.py
│   ├── steps/                               # 安装步骤
│   ├── scripts/                             # 产物工厂
│   └── updater/
├── init_userspace/ / init_data/             # 产物落盘（非实现）
└── docs/ / __test__/                        # 文档与公开 API 测试
```

## 快速开始

见 [QUICKSTART.md](./QUICKSTART.md)。

```python
from setup import Setup

Setup.runtime.needs_install("cli")
```

## 相关文档

- [API.md](./API.md)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
