# Database 模块设计文档

**版本：** `0.3.1`

本文档描述 `infra.db` 的模块拆分与协作细节；总览见 [ARCHITECTURE.md](./ARCHITECTURE.md)。

---

## 1. 设计原则

- **按 backend 分包**：mysql / pgsql / duckdb 各自 engine，不合并为 server 层。
- **统一入口**：业务经 `DatabaseManager` 或 `DbBaseModel`，不直接碰 connector。
- **字段与方言分离**：`engines/shared/fields` 定义类型语义；`schema_parser` 生成 DDL。
- **性能优先**：参数化 SQL、批量写入、mysql/pgsql 写队列、duckdb WritePipeline。

---

## 2. 模块结构与职责

### 2.1 `DatabaseManager`（`db_manager.py`）

- 解析配置 → `Db.engine.build_meta`（`EngineConfigMeta`）→ `Db.engine.create` → `engine.initialize()`。
- 维护 `StorageRegistry`、`schema_manager`（initialize 后与 engine 共享）。
- 转发：查询、事务、建表、`queue_write`、`checkpoint_duckdb` 等。

### 2.2 Engine（`engines/{mysql,pgsql,duckdb}/engine.py`）

| 子模块 | 职责 |
|--------|------|
| `connector` | 连接池 / 多域 DuckDB 文件、执行 SQL |
| `sql_adapter` | 方言 SQL 文本（占位符、exists 查询） |
| `schema_parser` | schema dict → CREATE TABLE / INDEX / ADD COLUMN |
| `table_operator` | 单表 CRUD（`DbTableAbc`） |
| `write_pipeline`（duckdb） | 每域异步写、CHECKPOINT 策略 |
| `domain_catalog`（duckdb） | 表 → 域 → 文件路径（init 时动态构建） |

mysql/pgsql 另含 `BatchWriteQueue`（经 `_WriteQueueHost` 挂到 engine）。

### 2.3 `SchemaManager`（`schema_manager.py`）

- 从 `core/tables` 加载 `schema.py`；校验 `update_key`、`storage_domain`。
- 建表编排：`create_table_with_indexes` → 各 engine 的 `connection_factory`。
- DDL 生成委托 `get_schema_parser(dialect)`（`engines/*/schema_parser.py`）。

### 2.4 `engines/shared/fields`

- `Field` 子类与 `Field.from_dict`：与数据库无关的列定义。

### 2.5 `DbBaseModel`（`table_queriers/db_base_model.py`）

- 已 initialize 时优先 `engine.table_operator(table_name)`。
- `create_table` / `drop_table` 委托 `engine`。
- 导入导出、批量 upsert 等同理。

### 2.6 批量写入

- **mysql/pgsql**：`table_queriers/services/batch_operation_queue.py` + engine 内 `_WriteQueueHost`。
- **duckdb**：`engines/duckdb/write_pipeline.py`，按域队列；`table_operator.insert/upsert` 入队。

---

## 3. 关键协作流程

### 3.1 初始化

```text
DataManager.initialize()
  → DatabaseManager.initialize()
  → Db.engine.create(meta) / EngineFactory.create(meta)
  → rebuild_storage_registry()
  → (duckdb) engine.rebuild_table_file_map()
  → engine.initialize()
  → schema_manager = engine.schema_manager
  → create_all_base_tables() / _discover_tables() / register_table()
```

### 3.2 查询

```text
DbBaseModel.load / db.execute_sync_query[_for_table]
  → engine.table_operator 或 engine.connector
  → 参数化 SQL → 字典列表结果
```

### 3.3 写入

```text
db.queue_write / model.insert_async
  → engine.queue_write 或 table_operator → WritePipeline / BatchWriteQueue
  → flush_writes / wait_for_writes
```

### 3.4 DuckDB CHECKPOINT

```text
db.checkpoint_duckdb()
  → DuckdbEngine.checkpoint()
  → 各域 connector.checkpoint()
```

---

## 4. 边界与扩展

**边界**：`infra.db` 不提供业务语义；升级编排在 `userspace/system/updater`。

**扩展**：

- 新方言：新 engine 包 + `schema_parser` + `factory` 分支。
- 新字段类型：在 `shared/fields` 增加子类并在 `from_dict` 注册。
- DuckDB 新域：配置 `domains.*.db_path` + schema `storage_domain` 枚举。

---

## 5. 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [storage-domains.md](./storage-domains.md)
- [engines/ARCHITECTURE.md](../core/engines/ARCHITECTURE.md)
- [API.md](./API.md)
- [DECISIONS.md](./DESIGN.md)

---

## 附录：历史决策记录（原 `DECISIONS.md`，已并入）

> 下列内容自独立 DECISIONS 文件迁入，按时间追加保留；新决策请按「设计点」格式写在正文。

# Database 模块决策文档

**版本：** `0.3.1`（2026-06）

本文档记录架构决策及**实现状态**。运行时结构以 [ARCHITECTURE.md](./ARCHITECTURE.md)、[API.md](./API.md) 为准。

---

## 状态总览

| 决策 | 主题 | 状态 |
|------|------|------|
| 1 | 多 backend（PG / MySQL / DuckDB） | ✅ 已实现 |
| 2 | 三层 Connection/Table Manager | ❌ 已废止（见决策 7） |
| 3 | 默认实例 `get_default` | ✅ 已实现 |
| 4 | 队列聚合写入 | ✅ 已实现（backend 差异见下） |
| 5 | 参数化 SQL，无 ORM | ✅ 已实现 |
| 6 | DuckDB 三存储域 | ✅ 已实现 |
| 7 | 按 backend 独立 Engine 包 | ✅ 已实现 |
| 8 | mysql / pgsql 平级目录 | ✅ 已实现 |
| 9 | DbBaseModel 委托 engine | 🔶 部分（`table_operator` 路径已落地） |
| 10 | 跨域 JOIN / 写 | 🔶 部分（跨域写 v1 仍不支持；QueryPlanner 未实现） |
| 11 | DuckDB WritePipeline + 多进程 | 🔶 部分（WritePipeline ✅；`process_pool_scope` / `Db.duckdb.worker_pool` ✅） |
| 12 | DECIMAL 存储 + infra 统一出入库标量契约 | ✅ 已实现 |

---

> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [DESIGN.md](./DESIGN.md)
- [API.md](./API.md)
- [../README.md](../README.md)

