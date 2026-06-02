# Database 架构文档

**版本：** `0.2.0`

---

## 模块介绍

`infra.db` 提供 NTQ 的统一数据库基础能力，负责连接、schema 和表写入等通用能力封装。

---

## 模块目标

- 为上层模块提供统一数据库访问入口。
- 支持 PostgreSQL / MySQL 两种数据库方言。
- 提供高吞吐写入能力（批量与队列化写入）。
- 在多进程环境保持实例获取与初始化稳定。

---

## 模块职责与边界

**职责（In scope）**
- 数据库连接管理与事务封装。
- 表结构管理与建表流程。
- 同步查询与批量写入能力。
- 数据库方言差异适配。

**边界（Out of scope）**
- 业务规则与领域逻辑实现。
- 上层模块间业务编排。

---

## 依赖说明

- `infra.project_context`：提供数据库配置读取与项目路径定位能力。

---

## 工作拆分

- `DatabaseManager`（`db_manager.py`）：对外统一入口，编排连接、schema、表管理三层能力，并维护默认实例。
- `ConnectionManager`（`connection_management/connection_manager.py`）：负责适配器创建、连接生命周期、事务和游标上下文。
- `SchemaManager`（`schema_management/schema_manager.py`）：负责 schema 加载、建表 SQL 生成与表结构查询。
- `TableManager`（`table_management/table_manager.py`）：负责查询委托与写入路径（直写/队列）管理。
- `DbBaseModel`（`table_queriers/db_base_model.py`）：提供单表 CRUD、导入导出、批量 upsert 等通用表操作。

---

## 架构/流程图

```text
DatabaseManager
├── ConnectionManager
│   └── DatabaseAdapter (postgresql/mysql)
├── SchemaManager
└── TableManager
    └── BatchWriteQueue
```

```text
初始化: DatabaseManager -> ConnectionManager -> SchemaManager -> TableManager
查询:   调用方 -> DatabaseManager -> ConnectionManager -> Adapter -> DB
写入:   调用方 -> DatabaseManager -> TableManager -> Queue/Direct -> Adapter -> DB
```

---

## 目标架构（已定案，迁移中）

原「Manager + Connection / Schema / Table 三层」将演进为 **Manager 挂载 per-backend Engine**。各 engine 包内自含 connector、schema_parser、sql_adapter 等模块；DuckDB 另含 write pipeline 等专有模块。

- **三个平级 engine 包**：`duckdb/`、`mysql/`、`pgsql/` — **不**合并为 `server/`。
- **DbBaseModel**：绑定 `for_table()` 并转发；extension 仅用白名单 API + `query`（见 engines §9–§10）。
- **DuckDB 写并发**：每域 WritePipeline、域间并行；多进程 Collector（见 engines §8、决策 11）。
- 决策与目录约定：[engines/ARCHITECTURE.md](../engines/ARCHITECTURE.md)、[决策 7–11](./DECISIONS.md)

当前代码仍以本文 §工作拆分 描述的结构运行为主，直至 engines 迁移完成。

---

## 相关文档

- [engines 架构（目标）](../engines/ARCHITECTURE.md)：per-backend Engine 定案与 `_shared/` 规则。
- [详细设计](./DESIGN.md)：与**当前实现**一致的类图、数据流、配置与扩展点说明。
- [存储域设计](./storage-domains.md)：DuckDB 三域（data / tag / strategy）定案与 DataManager 隐患审计。
- [API](./API.md)、[决策记录](./DECISIONS.md)
