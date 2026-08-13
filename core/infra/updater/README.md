# Updater（`infra.updater`）

应用升级：编排源码、DB 数据迁移脚本注册表、post-upgrade 收尾、把编排同步进 `userspace/system/updater`。

运行时从 `userspace/system/updater` 启动（`cli.py u`）。不要从本模块 `import pipeline` 来执行升级。

## 布局

```text
core/infra/updater/
├── updater.py          # Facade
├── contracts.py
├── core/
│   ├── db/             # 数据脚本注册表
│   ├── post_upgrade/   # 收尾动作 + CLI
│   ├── orchestrator/   # 编排源码（拷贝到 userspace）
│   └── orchestrator_sync.py
├── __test__/
└── docs/
```

## 快速开始

见 [QUICKSTART.md](./QUICKSTART.md)。

```python
from core.infra.updater import Updater

Updater.runtime.sync_orchestrator(dest)
Updater.post_upgrade.run(repo_root)
```

## 相关文档

- [API.md](./API.md)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
