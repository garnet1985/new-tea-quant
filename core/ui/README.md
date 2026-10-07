# UI

**模块：** `ui` · **版本：** `0.2.3` · **最低核心版本：** `>=0.5.0`

浏览器里的 NTQ。React 应用在 `fed/`。HTTP 在 `core/bff`，不在本模块。

依赖：`modules.strategy`、`infra.project_context`。

日常从仓库根的 `launcher.py` 启动。单独拉起 BFF 用 `python -m core.bff.app`。前端脚本在 `fed/package.json`。

架构见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)，设计见 [docs/DESIGN.md](docs/DESIGN.md)，全页引导见 [docs/CONCEPTS.md](docs/CONCEPTS.md)。
