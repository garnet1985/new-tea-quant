# Dev CLI scripts

一功能一文件夹。由 `devcli.py` / `core.infra.cli.dev.handlers` 调用。

跨脚本共享件放 [`../services/`](../services/)（目前仅 `paths.py`）。

| 文件夹 | 入口 | 说明 |
|--------|------|------|
| `publish_prep/` | `devcli.py p` | 发布闸门（含 changelog_sync） |
| `raw_icon_scan/` | pack 步骤 / `-m …raw_icon_scan` | 裸状态 emoji |
| `dependency_risk/` | `devcli.py cd` | 依赖风险 |
| `minimal_import_check/` | `devcli.py ic` | UI 最小 import |
| `py39_compat_check/` | pack 步骤 | 3.9 语法 |
| `stock_pool/` | `devcli.py ssp` / `pc` | 分层样本池 |
| `temp_cleanup/` | `cgc`/`csc`/`cdc`/`cmc` | 清 .ntq / results / workbench 快照 |

独立运行示例：`python -m core.infra.cli.dev.scripts.raw_icon_scan`
