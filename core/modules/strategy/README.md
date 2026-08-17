# Strategy（`modules.strategy`）

为 NTQ 提供策略执行：扫描、枚举、价格因子与组合模拟，以及策略发现。对外门面为 `Strategy`；hooks / 枚举 / 共享类型见 `contracts`。

## 适用场景

- CLI / 工作台触发 scan 或 simulate 各步
- 用户策略经 `StrategyHooks` + `StrategyContext` 挂入回测
- 列出 / 查询已发现策略元数据

## 模块依赖

见 `module_info.yaml`（data_manager、data_contract、indicator、backtest_engine、project_context）。  
兼容 core：`>=0.4.4`。

## 设计初衷

- **要解决的问题：** 统一策略包发现、模拟缓存与多引擎编排入口。
- **明确不做：** 不在本模块另起平行于 BacktestEngine 的调度 / Timeline（硬约束见 [docs/DESIGN.md](./docs/DESIGN.md) 与 [docs/notes/BOUNDARY_NOTES.md](./docs/notes/BOUNDARY_NOTES.md)）。不负责回测归因（见 `modules.analysis`）。

## 用户策略 import（公开面）

```python
from core.modules.strategy import Strategy
from core.modules.strategy.contracts import (
    StrategyHooks,
    StrategyContext,
    Opportunity,
    SimulateKind,
)
```

勿 deep-import `core.modules.strategy.core.engines.*`（实现位于 `core/`，包根只导出 `Strategy`）。

## 常见问题

**Q：enumerate 和 simulate 什么关系？**  
A：`enumerate` / `price_factor` / `portfolio` 都是 `Strategy.simulate(..., kind=...)` 的薄封装。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [边界笔记](./docs/notes/BOUNDARY_NOTES.md)
- [测试用例](./__test__/TEST_CASES.md)
