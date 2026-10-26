# Database（`infra.db`）

**模块：** `infra.db` · **版本：** `0.3.2`

## 简介

数据库底层。按配置挂一个后端（DuckDB / PostgreSQL / MySQL），管建表、迁移、表级读写。上层模块不直接连数据库，都经 DataManager 或直接经本门面。DuckDB 多进程 worker 池的连接释放 / 恢复也在这里处理。

## 适用场景

- 上层模块需要执行 SQL、建表、批量写入
- 应用升级时跑 schema 迁移

## 模块依赖

- `infra.project_context`：路径与配置

## 设计初衷

- **要解决的问题：** 屏蔽不同数据库后端的差异，上层不用换代码就能换引擎。
- **明确不做：** 不做业务逻辑；不做应用升级编排（那是 `infra.updater`）。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [快速开始](./QUICKSTART.md)
- [决策](./docs/DECISIONS.md)
