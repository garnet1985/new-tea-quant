# Data Contract

**模块：** `modules.data_contract` · **版本：** `0.4.2`

声明式取数。用 DataKey 签发契约，分成 meta、runtime、specific 三层。公开入口是 `ContractIssuer`。`DATA_KEY`、基类和专用子类从 `contracts` 导入。最短示例见 [QUICKSTART.md](./QUICKSTART.md)，调用面见 [API.md](./API.md)。

依赖：`modules.data_manager`、`infra.project_context`、`infra.utils`。

测试见 [`__test__/TEST_CASES.md`](__test__/TEST_CASES.md)。架构见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)，设计见 [docs/DESIGN.md](docs/DESIGN.md)，原理见 [docs/CONCEPTS.md](docs/CONCEPTS.md)，名词见 [glossary.yaml](glossary.yaml)。
