# Database 架构文档

**版本：** `0.3.0`（Engine 挂载架构，2026-06）

---

## 模块介绍

`infra.db` 提供 NTQ 的统一数据库基础能力：连接、schema、表级 CRUD、批量/队列写入（按 backend 不同）。

---

## 当前运行时结构（已定案）

```text
DatabaseManager (db_manager.py)
└── Engine (mysql | pgsql | duckdb)     ← factory.create_engine(meta)
    ├── connector      连接池 / 多域文件 / 执行 SQL
    ├── sql_adapter    方言 SQL 文本（无 I/O）
    ├── schema_parser  schema → DDL（经 SchemaManager 委托）
    ├── table_operator 单表 CRUD（DbTableAbc）
    └── duckdb 专有: domain_catalog, write_pipeline, WAL checkpoint

SchemaManager (schema_manager.py)      ← 加载 core/tables、建表、补列
StorageRegistry                        ← 表 → storage_domain（DuckDB 路由）
DbBaseModel (table_queriers/)          ← 业务表模型；优先转发 engine.table_operator
```

```text
初始化:
  DatabaseManager.initialize()
    → create_engine → rebuild_storage_registry
    → (duckdb) rebuild_table_file_map
    → engine.initialize()
    → schema_manager = engine.schema_manager

查询/写入:
  调用方 → DatabaseManager / DbBaseModel
        → engine.table_operator(table) 或 engine.execute_sync_query*
        → connector
```

**已移除（勿再引用）：** `ConnectionManager`、`TableManager`、`table_queriers/adapters/`、`DatabaseAdapterFactory`、`BaseDatabaseAdapter`。

---

## 模块职责与边界

**职责**
- 按配置 mount 一个 backend Engine。
- Schema 加载、DDL、迁移（`migration/`）。
- 表级 CRUD、批量写入、DuckDB 多域与 WAL 策略。

**边界**
- 业务领域逻辑在 `core/modules/*`。
- 升级编排在外层 `userspace/updater/`。

---

## 依赖

- `infra.project_context`：配置与路径。
- 配置合并：`ConfigManager.load_database_config()` → `build_engine_meta()`。

---

## DuckDB 要点

- 三存储域：`data` / `tag` / `strategy`，各域独立 `.duckdb` 文件。
- 表→域来自 schema `storage_domain`；`DuckdbDomainCatalog` 在 init 时动态构建（非逐表 JSON）。
- CHECKPOINT：`DatabaseManager.checkpoint_duckdb()` → `DuckdbEngine.checkpoint()`。

详见 [storage-domains.md](./storage-domains.md)、[engines/ARCHITECTURE.md](../engines/ARCHITECTURE.md)。

---

## 相关文档

| 文档 | 内容 |
|------|------|
| [engines/ARCHITECTURE.md](../engines/ARCHITECTURE.md) | 三 engine 包目录与模块职责 |
| [DESIGN.md](./DESIGN.md) | 历史设计细节（部分章节仍描述旧三层，以本文为准） |
| [DECISIONS.md](./DECISIONS.md) | 决策记录（含三层→Engine 演进） |
| [API.md](./API.md) | 对外 API 说明 |
