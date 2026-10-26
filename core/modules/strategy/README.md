# Strategy（`modules.strategy`）

**模块：** `modules.strategy` · **版本：** `0.12.0`

为 NTQ 提供策略执行：扫描、枚举、价格因子、组合模拟与决策者模式，以及策略发现。对外门面为 `Strategy`；hooks / 枚举 / 共享类型见 `contracts`。

## 适用场景

- CLI / 工作台触发 scan 或 simulate 各步
- 用户策略经 `StrategyHooks` + `StrategyContext` 挂入回测
- 列出 / 查询已发现策略元数据

## 模块依赖

- `infra.cmd_layout`
- `infra.db`
- `infra.discovery`
- `infra.export_import`
- `infra.project_context`
- `infra.trace`
- `infra.utils`
- `modules.analysis`：分析模块：回测完成后，解释策略 inputs 与 outputs 的关系（骨架，行为 API 未定）
- `modules.backtest_engine`：回测引擎模块：对上层应用提供的任务进行规划，重组和按时间推进。
- `modules.data_contract`：数据契约模块：提供一套可扩展的数据声明到数据加载的契约，主要目的是为了实现回测过程中的声明式数据注入
- `modules.data_manager`：数据管理模块：提供统一的数据访问门面，支持对不同数据源的访问和查询。
- `modules.data_source`：数据源模块：提供配置驱动的数据抓取，支持按照不同模式和不同数据供应商请求并加载数据。
- `modules.indicator`：技术指标计算模块：使用pandas-ta-classic包提供技术指标计算服务，支持计算多种技术指标
- `modules.market_profile`：市场制度规则模块：提供市场制度规则的查询服务，支持查询涨跌停、最小申报单位、板块手数等规则。
- `modules.post_process`：后续处理模块：扫描机会协议规范化，以及 PostProcessor / Adapter 发现与执行。
## 设计初衷

- **要解决的问题：** 统一策略包发现、模拟缓存与多引擎编排入口。
- **明确不做：** 不在本模块另起平行于 BacktestEngine 的调度 / Timeline（硬约束见 [docs/DESIGN.md](./docs/DESIGN.md) 与 [docs/notes/BOUNDARY_NOTES.md](./docs/notes/BOUNDARY_NOTES.md)）。归因编排在 `engines/analyzer`，纯统计/ML 在 `modules.analysis`（见 [core/engines/analyzer/docs/BOUNDARY.md](./core/engines/analyzer/docs/BOUNDARY.md)）。

## 常见问题

**Q：enumerate 和 simulate 什么关系？**  
A：`Strategy.enumerate` / `Strategy.price_factor` / `Strategy.portfolio` 都是 `Strategy.simulate(..., kind=...)` 的薄封装。kind 为 `enum` / `price` / `portfolio`。

**Q：我该 import 什么？**  
A：从 `Strategy` 进门面，从 `contracts` 进钩子和共享类型（`StrategyHooks`、`StrategyContext`、`Opportunity`、`SimulateKind`）。勿 deep-import `core.modules.strategy.core.engines.*`（实现位于 `core/`，包根只导出 `Strategy`）。最短可运行路径见 [快速开始](./QUICKSTART.md)。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [概念与运作](./docs/CONCEPTS.md)
- [设计](./docs/DESIGN.md)
- [Version / 指纹](./docs/VERSIONING.md)
- [边界笔记](./docs/notes/BOUNDARY_NOTES.md)
- [测试用例](./__test__/TEST_CASES.md)
