# Database（`infra.db`）

为 New Tea Quant（简称 **NTQ**）提供统一的数据库基础设施：按配置挂载一个后端引擎（Engine：DuckDB / PostgreSQL / MySQL）、schema 管理、表级读写与（DuckDB）多存储域协作。对外门面类（Facade）为 `Db`；表模型等契约见 `contracts.py`。词条见 [glossary.yaml](./glossary.yaml)。

## 适用场景

- 上层模块需要统一执行 SQL、表级 CRUD 或批量写入。
- 需要按 `core/tables` 管理 schema，并在升级时做结构迁移。
- 多进程场景下与 DuckDB worker 池协作（释放 / 恢复主进程连接等）。

## 模块依赖

- `infra.project_context`：读取数据库配置与项目路径

## 设计初衷

- **要解决的问题：** 用单一挂载入口屏蔽多后端差异，并把 schema / 迁移收在基础设施层。
- **明确不做：** 业务领域逻辑；应用升级流水线编排（在 updater）；GUI。

## 常见问题

**Q：现在该 import 什么？**  
A：门面 `from core.infra.db import Db`；类型 `from core.infra.db.contracts import DbBaseModel, Field, DatabaseManager`。包根**只**导出 `Db`。

**Q：实现代码在哪？**  
A：全部在 `core/` 子包；跨模块请经 `Db` / `contracts`，勿依赖 `core.infra.db.core...` 深路径。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [存储域](./docs/storage-domains.md)
- [测试用例](./__test__/TEST_CASES.md)
