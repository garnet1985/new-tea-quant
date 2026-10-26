# Backtest Engine（`modules.backtest_engine`）

**模块：** `modules.backtest_engine` · **版本：** `0.2.0`

回测调度 Facade：对 Tag / Strategy 提供 **probe → plan → execute → monitor** 流水线。数据装载由调用方经 `RunCallbacks` 注入，engine 不读业务 DB。支持两种回测模式：`entity_based`（逐股）与 `slice_based`（时间切片），内置内存溢出监控。

## 适用场景

- Strategy 模块模拟多策略组合、Tag 模块批量算因子等需要"调度 + 推进"能力的场景
- 单进程或多进程跑回测，且需要 probe 自动决定 batch / slice 组装方式

## 模块依赖

- `infra.db`
- `infra.machine_capacity`
- `infra.project_context`
- `modules.data_contract`：数据契约模块：提供一套可扩展的数据声明到数据加载的契约，主要目的是为了实现回测过程中的声明式数据注入
- `modules.data_manager`：数据管理模块：提供统一的数据访问门面，支持对不同数据源的访问和查询。
## 设计初衷

- **要解决的问题：** 回测调度是复杂多进程问题（探针、计划、执行、监控分离），不能让 Strategy 和 Tag 各自实现一遍。
- **明确不做：** 不读取业务 DB（数据全部经 `RunCallbacks` 注入）；不做策略归因（属 `strategy/engines/analyzer`）。

## 常见问题

**Q：两种模式怎么选？**
A：`entity_based` 逐股推进，适合因子计算；`slice_based` 按时间切片批量推进，适合组合模拟。详见 [docs/SLICE_BASED_ALGORITHM.md](./docs/SLICE_BASED_ALGORITHM.md)。

## 相关文档

- [公开 API](./API.md)
- [快速开始](./QUICKSTART.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [slice_based 算法](./docs/SLICE_BASED_ALGORITHM.md)
