# Data Contract（`modules.data_contract`）

**模块：** `modules.data_contract` · **版本：** `0.4.3`

声明式取数。用 `DataKey` 签发契约，分成 meta、runtime、specific 三层；对外门面为 `ContractIssuer`。不做业务调度，只管"按声明要什么、就拿到什么"。类声明级缓存由契约层统一管理。

## 适用场景

- Strategy / BacktestEngine / Tag 等模块需要**按声明**取某张表 / 某个 key 的数据，而不关心底层怎么加载

## 模块依赖

- `infra.project_context`
- `infra.utils`
- `modules.data_manager`：数据管理模块：提供统一的数据访问门面，支持对不同数据源的访问和查询。
## 设计初衷

- **要解决的问题：** 把"要什么数据"从"怎么拿到"里抽出来，让上层只写声明，加载逻辑在本层。
- **明确不做：** 不缓存原始数据（只缓存类声明）；不做业务调度。

## 常见问题

**Q：我该 import 什么？**
A：`from core.modules.data_contract import ContractIssuer`；DataKey 与基类从 `contracts` 导入。

## 相关文档

- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
