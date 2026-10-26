# Project Context（`infra.project_context`）

**模块：** `infra.project_context` · **版本：** `0.2.0`

项目根推断、语义路径、约定式配置发现与默认/用户配置合并。对外门面为 `ProjectContext`（`path` / `config` / `discovery` / `meta` / `cache` 五个 namespace）。

## 适用场景

- 各模块需要统一的 `userspace` / 策略 / Tag / data_source 目录路径，不各自算一遍
- 需要合并 `core/default_config` 与 `userspace/config`，且支持按模块名路由到对应配置块

## 模块依赖

无硬依赖
## 设计初衷

- **要解决的问题：** 路径和配置发现是"任何模块都可能要"的原语，不能散落在各处。
- **明确不做：** 不持有业务状态；不写配置回 userspace（配置写入由具体模块负责）。

## 常见问题

**Q：该 import 什么？**
A：`from core.infra.project_context import ProjectContext`；单模块路径用 `ProjectContext.path.get_xxx_directory()`。

## 相关文档

- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
