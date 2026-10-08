# Data Source

**模块：** `modules.data_source` · **版本：** `0.2.0`

配置驱动的数据抓取。从 `userspace/data_source/mapping.py` 和各 handler 的 `config.py` 加载表 schema，实例化 Handler 与 Provider，由调度器按依赖顺序执行并写库。`is_dry_run` 为真时跳过写入。

公开入口是 `DataSourceManager`。Provider、Handler、job 和配置类型从 `contracts` 导入。最短示例见 [QUICKSTART.md](./QUICKSTART.md)，调用面见 [API.md](./API.md)。

依赖：`modules.data_manager`、`infra.project_context`、`infra.discovery`、`infra.db`、`infra.utils`、`infra.cmd_layout`。

测试见 [`__test__/TEST_CASES.md`](__test__/TEST_CASES.md)。架构见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)，设计见 [docs/DESIGN.md](docs/DESIGN.md)，名词见 [glossary.yaml](glossary.yaml)。
