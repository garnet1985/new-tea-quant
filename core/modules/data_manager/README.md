# Data Manager（`modules.data_manager`）

**模块：** `modules.data_manager` · **版本：** `0.2.3`

统一数据访问门面。上层模块（Strategy / DataSource / Tag / SeriesRelation）不直接连 `infra.db`，经 `DataManager` 取日历、股票、行业、指数、宏观等各类数据。

## 适用场景

- 需要股票列表、K 线、行业映射、交易日历等通用数据，不想知道底层表名
- 需要统一配置不同数据源（本地 DuckDB vs PostgreSQL）

## 模块依赖

- `infra.cmd_layout`
- `infra.db`
- `infra.discovery`
- `infra.project_context`
- `infra.utils`
## 设计初衷

- **要解决的问题：** 把多数据源（DB / DataSource renew）的读取入口收在一处，上层只调门面。
- **明确不做：** 不做抓取（属 DataSource）；不做数据转换（属 DataContract）。

## 常见问题

**Q：怎么拿股票 K 线？**
A：`DataManager.get_service("stock").get_klines(entity_id, start, end)`；具体 API 见 [API.md](./API.md)。

## 相关文档

- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
