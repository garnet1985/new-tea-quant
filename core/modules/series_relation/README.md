# Series Relation（`modules.series_relation`）

**模块：** `modules.series_relation` · **版本：** `0.2.0`

**最低支持核心版本：** `>=0.5.0`

## 简介

把多条时间序列放到同一张图上看：比如大盘指数 vs 美联储利率、板块内几只股票的 K 线、回测净值 vs 基准。模块会算相关性、滞后关系、缩放比例，帮你看出"谁领先谁、是不是整体同形波动"。

## 适用场景

- 想知道大盘指数和某个宏观指标是不是反相关、有没有延迟
- 一个板块里 30 只股票是不是整体一起波动，有没有滞后的一两只
- 把自己策略的回测净值和沪深 300 基准放一起比

## 模块依赖

- `infra.discovery`：自动发现数据源
- `infra.project_context`：路径与配置
- `modules.data_contract`：声明式取数据
- `modules.data_manager`：底层数据读取
- `modules.strategy`：取回测产物（组合净值等）

## 设计初衷

- **要解决的问题：** 多序列关系分析需要"对齐 + 算相关 + 找滞后"，不是简单把几条曲线叠一起。
- **明确不做：** 不做因果推断、不做预测（只描述关系）。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [决策](./docs/DECISIONS.md)
