# Tag（`modules.tag`）

**模块：** `modules.tag` · **版本：** `0.4.0`

标签资产层：把一个或多个数据源按规则（配置驱动）标成因子并持久化。`per_entity` 型因子委托 BacktestEngine 跑，`global` / `non_time_series` 型主进程推进。

## 适用场景

- 每日把所有股票跑一遍"PE-TTM"并写回数据库
- 用回测引擎的逐股能力批量计算因子

## 模块依赖

- `infra.discovery`
- `infra.project_context`
- `infra.trace`
- `infra.utils`
- `modules.backtest_engine`：回测引擎模块：对上层应用提供的任务进行规划，重组和按时间推进。
- `modules.data_contract`：数据契约模块：提供一套可扩展的数据声明到数据加载的契约，主要目的是为了实现回测过程中的声明式数据注入
- `modules.data_manager`：数据管理模块：提供统一的数据访问门面，支持对不同数据源的访问和查询。
- `modules.strategy`：策略执行模块：Strategy facade 提供 scan / simulate / discov
## 设计初衷

- **要解决的问题：** 因子需要批量、持久化、可跨策略复用，不应让策略各自算一遍。
- **明确不做：** 不做因子研究（选哪个因子好是分析层的事）；不做因子合成（多因子组合在 Strategy 里）。

## 常见问题

**Q：per_entity 和 global 有什么区别？**
A：`per_entity` 会把每只标的当作一个 backtest job 跑（能复用 BacktestEngine 的调度和数据契约）；`global` 在主进程直接算。详见 [API.md](./API.md)。

## 相关文档

- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
