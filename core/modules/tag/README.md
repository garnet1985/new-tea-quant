# Tag

**模块：** `modules.tag` · **版本：** `0.4.0` · **最低核心版本：** `>=0.5.0`

标签资产层。按 `data.base` 路由：per_entity 交给 BacktestEngine，global 和 non_time_series 在主进程推进。公开入口是 `Tag`。钩子和枚举从 `contracts` 导入。最短示例见 [QUICKSTART.md](./QUICKSTART.md)，调用面见 [API.md](./API.md)。

依赖：`modules.data_manager`、`modules.data_contract`、`modules.backtest_engine`、`modules.strategy`、`infra.project_context`、`infra.discovery`、`infra.utils`、`infra.trace`。

CLI 和工作台触发单个或全部已启用 tag。场景目录在 `userspace/extensions/tags`，每个场景是 `settings.py` 加 `tag.py`。本模块不另做一套和回测引擎平行的调度。界面上的目录和运行在 `core/bff/APIs/tag`。

测试见 [`__test__/TEST_CASES.md`](__test__/TEST_CASES.md)。架构见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)，设计见 [docs/DESIGN.md](docs/DESIGN.md)，名词见 [glossary.yaml](glossary.yaml)。
