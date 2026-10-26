# Data Manager（`modules.data_manager`）

**模块：** `modules.data_manager` · **版本：** `0.2.3`

## 简介

本地数据访问的统一入口。上层模块不直接连数据库，都从这里拿——交易日历、股票列表、K 线、行业映射、指数、宏观数据。底层用什么引擎（DuckDB / PostgreSQL / MySQL）对上层透明。

## 适用场景

- 策略跑回测前拿某只股票的 K 线
- 标签计算需要全股票列表或行业映射表
- 不同环境想用不同数据库，改一处配置就行

## 模块依赖

- `infra.cmd_layout`：终端展示
- `infra.db`：底层数据库操作
- `infra.discovery`：自动发现数据服务实现
- `infra.project_context`：路径与配置
- `infra.utils`：通用工具

## 设计初衷

- **要解决的问题：** 把底层数据访问集中到一处，上层不直接连数据库。
- **明确不做：** 不抓取外部数据（那是 `data_source`）；不做数据格式转换（那是 `data_contract`）。

## 相关文档

- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
