# Strategy（`modules.strategy`）

**模块：** `modules.strategy` · **版本：** `0.12.0`

## 简介

策略执行的核心。管理策略发现、配置加载、扫描（找机会）和模拟（跑回测）。策略代码以 hooks 形式挂入，回测推进由 BacktestEngine 执行，本模块管调度和产物持久化。

## 适用场景

- CLI 或工作台触发 `scan` 全市场找机会、或 `simulate` 跑回测
- 用户写的策略文件经 `StrategyHooks` 挂入，在这里被发现和执行
- 列出当前项目已发现的策略、查看元数据

## 模块依赖

- `infra.cmd_layout`：终端展示
- `infra.db`：数据库操作
- `infra.discovery`：自动发现策略包
- `infra.export_import`：策略包导入导出
- `infra.project_context`：路径与配置
- `infra.trace`：匿名上报
- `infra.utils`：通用工具
- `modules.analysis`：统计 / ML 原语
- `modules.backtest_engine`：回测调度与推进
- `modules.data_contract`：声明式取数
- `modules.data_manager`：底层数据读取
- `modules.data_source`：外部数据源抓取
- `modules.indicator`：技术指标计算
- `modules.market_profile`：市场交易规则
- `modules.post_process`：扫描结果分发

## 设计初衷

- **要解决的问题：** 把"策略是什么、怎么跑、跑完放哪"三件事集中管理。
- **明确不做：** 不自己实现回测 Timeline（那是 BacktestEngine 的职责）；归因编排在 `engines/analyzer`，纯统计 / ML 在 `modules.analysis`。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [概念与运作](./docs/CONCEPTS.md)
- [设计](./docs/DESIGN.md)
