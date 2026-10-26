# Data Source（`modules.data_source`）

**模块：** `modules.data_source` · **版本：** `0.4.0`

配置驱动的数据抓取：对接 Tushare / Yahoo / 自建 Provider 等外部数据源，按 `renew_config` 周期把数据落进 `infra.db` 的约定表。

## 适用场景

- 首次拉全量、或每日/每周增量更新股票、指数、宏观等数据
- 对接新的外部数据源，只需写 Provider + Handler，不改主流程

## 模块依赖

- `infra.cmd_layout`
- `infra.db`
- `infra.discovery`
- `infra.project_context`
- `infra.utils`
- `modules.data_manager`：数据管理模块：提供统一的数据访问门面，支持对不同数据源的访问和查询。
## 设计初衷

- **要解决的问题：** 把"和外部打交道"从"本地取数"里分离，抓取周期、并发、速率限制在本层统一。
- **明确不做：** 不缓存数据（靠 `infra.db` + `data_manager`）；不做声明式取数（属 DataContract）。

## 常见问题

**Q：怎么加一个新数据源？**
A：在 `userspace/extensions/data_source/<provider_id>/` 下放 Handler + 配置；Discovery 会自动加载。详见 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

## 相关文档

- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
