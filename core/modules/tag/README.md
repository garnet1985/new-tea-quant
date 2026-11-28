# Tag（`modules.tag`）

**模块：** `modules.tag` · **版本：** `0.4.3`

**最低支持核心版本：** `>=0.5.0`

## 简介

批量算因子并持久化到数据库。比如每日把全市场股票的 PE-TTM 跑一遍存起来，策略回测时直接查表用。因子有两种算的方式：逐股跑（委托 BacktestEngine）和一次性批量算（主进程）。

## 适用场景

- 每日定时更新一批因子（PE、PB、换手率、市值等）
- 策略回测需要某个因子但不想自己在代码里算一遍，直接查 Tag 表

## 模块依赖

- `infra.discovery`：自动发现因子配置
- `infra.project_context`：路径与配置
- `infra.trace`：匿名上报
- `infra.utils`：通用工具
- `modules.backtest_engine`：批量跑 `per_entity` 型因子
- `modules.data_contract`：声明式取数
- `modules.data_manager`：底层数据读取
- `modules.strategy`：策略元数据（因子可能引用策略产物）

## 设计初衷

- **要解决的问题：** 因子需要批量、持久化、可跨策略复用，不能让每个策略各自算一遍。
- **明确不做：** 不做因子研究（选哪个因子好是分析层的事）；不做多因子合成（那是 Strategy 的事）。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [快速开始](./QUICKSTART.md)
- [决策](./docs/DECISIONS.md)
