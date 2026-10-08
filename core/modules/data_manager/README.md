# Data Manager

**模块：** `modules.data_manager` · **版本：** `0.2.1`

进程内统一数据访问门面。持有 `DatabaseManager`，发现 `core/tables` 与 `userspace/extensions/tables`，装配 `DataService`。

公开入口是 `DataManager`。`BaseTableNames` 从 `contracts` 导入。领域服务经 `DataManager` 的属性访问，例如 `stock`、`calendar`。最短示例见 [QUICKSTART.md](./QUICKSTART.md)，调用面见 [API.md](./API.md)。

依赖：`infra.db`、`infra.project_context`、`infra.discovery`、`infra.utils`、`infra.cmd_layout`。

测试见 [`__test__/TEST_CASES.md`](__test__/TEST_CASES.md)。架构见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)，设计见 [docs/DESIGN.md](docs/DESIGN.md)，名词见 [glossary.yaml](glossary.yaml)。
