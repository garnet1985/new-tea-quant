# Update（`infra.update`）

升级扩展：DB 数据迁移脚本注册表、post-upgrade 收尾动作注册表与 CLI。

编排 / 下载 / 版本探测见仓库 `setup/updater/`。

## 布局

```text
core/infra/update/
├── update.py           # Facade
├── contracts.py
├── API.md / QUICKSTART.md / glossary.yaml
├── db/                 # 数据脚本注册表
├── post_upgrade/       # 收尾动作 + CLI
├── __test__/
└── docs/
```

## 快速开始

见 [QUICKSTART.md](./QUICKSTART.md)。

```python
from core.infra.update import Update

Update.post_upgrade.run(repo_root)
```

## 相关文档

- [API.md](./API.md)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
