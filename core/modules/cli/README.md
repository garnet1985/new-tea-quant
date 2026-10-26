# CLI（`modules.cli`）
**模块：** `modules.cli` · **版本：** `0.4.5`

为 New Tea Quant（简称 **NTQ**）提供**双入口命令行**：`Cli.user`（策略用户）与 `Cli.dev`（开发 / 运维）。对外只暴露一个「门面」类 `Cli`（英文常称 **Facade**：把内部多套实现收成统一入口）；共用脚手架挂在 `Cli.shared`。更多词条见 [glossary.yaml](./glossary.yaml)。

## 适用场景

- 从仓库根用 `cli.py` 跑策略侧命令（扫描、模拟、tag、更新等）。
- 从仓库根用 `devcli.py` 跑开发 / 运维命令（UI、清理、pack、样本池等）。
- 在入口脚本里通过 `Cli.user` / `Cli.dev` 启动解析与分发，或复用 `Cli.shared` 做命令行参数（argv）短别名展开。

## 模块依赖

- `infra.cmd_layout`
- `infra.db`
- `infra.project_context`
- `infra.setup`
- `infra.task_guard`
- `infra.trace`
- `infra.utils`
- `modules.agent`：AI agent：Provider、Navigator、流向、知识拼装与本机工具。
- `modules.data_contract`：数据契约模块：提供一套可扩展的数据声明到数据加载的契约，主要目的是为了实现回测过程中的声明式数据注入
- `modules.data_manager`：数据管理模块：提供统一的数据访问门面，支持对不同数据源的访问和查询。
- `modules.data_source`：数据源模块：提供配置驱动的数据抓取，支持按照不同模式和不同数据供应商请求并加载数据。
- `modules.indicator`：技术指标计算模块：使用pandas-ta-classic包提供技术指标计算服务，支持计算多种技术指标
- `modules.series_relation`：序列关系：多条 time series 并置比较（对齐呈现 + 可选关系摘要）。
- `modules.strategy`：策略执行模块：Strategy facade 提供 scan / simulate / discov
- `modules.tag`：标签资产层：按 data.base 路由；per_entity 经 BacktestEngine；g
## 设计初衷

- **要解决的问题：** 把用户命令与开发命令分成两套入口，同时用统一入口类暴露可测的公开调用面。
- **明确不做：** 不把 user / dev 合成单一命令行程序；不把 `user/`、`dev/`、`shared/` 包路径当作公开 import 面。

## 常见问题

**Q：`cli.py` 和 `devcli.py` 为什么要分开？**  
A：受众不同，且短别名会冲突（如 `ex`）。设计说明见 [docs/DESIGN.md](./docs/DESIGN.md)。

**Q：代码里该 import 什么？**  
A：只 `from core.modules.cli import Cli`，见 [API.md](./API.md)。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [测试用例](./__test__/TEST_CASES.md)
