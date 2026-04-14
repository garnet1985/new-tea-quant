# Database 模块（`infra.db`）

数据库基础设施层，负责 NTQ 在 PostgreSQL/MySQL 上的统一连接、schema 与表写入能力。

## 适用场景

- 上层模块需要统一执行 SQL 查询。
- 需要批量写入与异步写入队列能力。
- 需要根据 schema 自动建表和表结构管理。
- 需要在多进程场景中使用默认数据库实例。

## 快速定位

```text
core/infra/db/
├── module_info.yaml
├── db_manager.py
├── connection_management/
├── schema_management/
├── table_management/
├── table_queriers/
├── helpers/
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN.md
    ├── API.md
    └── DECISIONS.md
```

## 模块依赖

- `infra.project_context`：用于读取数据库配置与项目路径上下文。

## 当前实现说明（代码对齐）

- 当前支持数据库类型：`postgresql`、`mysql`。
- 不包含 SQLite 适配器与配置解析支持。
- 默认实例通过 `DatabaseManager.set_default/get_default` 管理。

## 相关文档

- `docs/ARCHITECTURE.md`
- `docs/DESIGN.md`
- `docs/API.md`
- `docs/DECISIONS.md`
