# Database 模块设计文档

**版本：** `0.5.0`

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

**边界**：`infra.db` 不提供业务语义；升级编排在 `userspace/updater`。

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

## 决策 1：数据库后端支持 PostgreSQL / MySQL / DuckDB

- **背景**：适配层需明确支持范围并控制维护成本。
- **决策**：模块支持 **PostgreSQL**、**MySQL**、**DuckDB**（默认本地三域文件）。
- **理由**：DuckDB 为 NTQ 默认嵌入式后端；server 库用于部署可选。
- **影响**：新方言须新增 `engines/<backend>/` 包、`schema_parser`、factory 分支与测试。
- **实现**：`engines/mysql`、`engines/pgsql`、`engines/duckdb`；配置经 `parse_database_config` + `EngineConfigMeta.from_raw_config`（公开：`Db.engine.build_meta`）。

---

## 决策 2：三层管理架构（已废止）

- **原决策（v0.2）**：`ConnectionManager` + `SchemaManager` + `TableManager`，由 `DatabaseManager` 编排。
- **废止原因**：方言与 DuckDB 特例在统一层膨胀；与「每 backend 自洽」目标冲突。
- **取代**：**决策 7**（Engine 挂载）。代码已删除 `ConnectionManager`、`TableManager`、`table_queriers/adapters/`。
- **保留**：`SchemaManager`（`schema_manager.py`）负责加载 `core/tables` 与建表编排；连接与表 CRUD 在各 **Engine** 内（`connector` + `table_operator` + 写队列 / WritePipeline）。

---

## 决策 3：默认实例机制保留

- **决策**：保留 `DatabaseManager.set_default` / `get_default` / `reset_default`。
- **理由**：减少样板代码；支持惰性自动 `initialize()`。
- **影响**：测试需 `reset_default`；长生命周期进程须在退出时 `close()`。
- **实现**：`db_manager.py`。

---

## 决策 4：写入主路径采用队列聚合

- **决策**：高频写入默认走异步聚合，而非逐条同步落库。
- **实现差异**：
  - **mysql / pgsql**：`BatchWriteQueue` + engine `_WriteQueueHost`。
  - **duckdb**：`WritePipeline`（按 `storage_domain` 分域队列）。
- **影响**：强一致场景须 `flush_writes` / `wait_for_writes`；DuckDB 另见 `checkpoint_duckdb`。
- **实现**：`table_queriers/services/batch_operation_queue.py`、`engines/duckdb/write_pipeline.py`。

---

## 决策 5：继续使用直接 SQL + 参数化

- **决策**：Engine `connector` + 参数化 SQL；不引入 ORM。
- **理由**：性能可控、方言可调。
- **影响**：DDL 由 `schema_parser` 维护；业务优先 `DbBaseModel` / `table_operator`。
- **实现**：各 `sql_adapter`、`table_operator`；`engines/shared/row_sql` 辅助批量拼装。

---

## 决策 6：DuckDB 三存储域（data / tag / strategy）

- **决策**：按 `storage_domain` 拆为三库文件；表名全局唯一；`get_table(name)` API 不变。
- **实现**：`StorageRegistry`、`DuckdbDomainCatalog`、`engines/duckdb/paths.py`；init 时 `rebuild_table_file_map`。
- **详见**：[storage-domains.md](./storage-domains.md)

---

## 决策 7：按 backend 拆分为独立 Engine 包（编排者模式）

- **决策**：
  - `core/infra/db/core/engines/{duckdb,mysql,pgsql}/`，每包 `engine.py` 编排 `connector`、`schema_parser`、`sql_adapter`、`table_operator` 等。
  - `DatabaseManager`：解析配置 → 挂载 Engine → 转发业务调用。
  - 无胖 `BaseDatabaseEngine`；共享逻辑仅放 `engines/shared/`（无 `engine_key` 分支）。
- **实现**：✅ 已完成（v0.3.0）；根目录 `schema_manager.py`、`migrate_manager.py`；无 `helpers/` 兼容层。
- **详见**：[engines/ARCHITECTURE.md](../core/engines/ARCHITECTURE.md)

---

## 决策 8：MySQL 与 PostgreSQL 保持平级目录

- **决策**：禁止合并为 `server/`；允许包内重复，抽 shared 须无方言分支。
- **实现**：`engines/mysql/` 与 `engines/pgsql/` 对称；共享项见 `_shared/`（fields、ddl_executor、dialect 等）。

---

## 决策 9：DbBaseModel 委托表级 Engine（进行中）

- **目标**：
  - 表操作经 `engine.table_operator(table_name)`（或等价薄封装）。
  - Model / extension 仅使用白名单 API；禁止 `if is_duckdb` 与直连已删的 connection 层。
- **已实现**：
  - `DbBaseModel._uses_engine_table_operator()`；读写、`insert_many` 等转发 `table_operator`。
  - DuckDB 查询/游标经 `get_sync_cursor_for_table` / `execute_sync_query_for_table`。
- **未完全对齐文档初稿**：
  - 未使用 `mounted_engine.for_table()` 命名；实际为 `table_operator`。
  - 部分路径仍保留 `self.db.execute_sync_query` 等转发，而非单一 `query()` 入口。
- **影响**：新代码优先 `table_operator` 与 `DatabaseManager` 转发方法；逐步收拢旧调用。

---

## 决策 10：JOIN 与 DuckDB 跨域查询（部分）

- **决策**：
  - 同域 JOIN：支持（业务/DataService 组织 SQL）。
  - DuckDB 跨域读：计划由 engine **QueryPlanner**（ATTACH + qualify）— **尚未实现**。
  - DuckDB 跨域写 SQL：**v1 不支持**；写路径用单表白名单 API。
- **当前**：按表路由域读写；跨域复杂查询仍建议 DataService 层组装。

---

## 决策 11：DuckDB 每域 WritePipeline + 多进程 worker 池协作（部分）

- **已实现**：
  - 每域 `WritePipeline`；`wal_policy`；批末 / SIGINT / `checkpoint_duckdb`。
  - `connector` 多域连接、`domain_catalog` 动态表→文件映射。
  - `duckdb/process_pool_scope.py`：多进程 worker 池期间主进程释放/恢复句柄（公开：`Db.duckdb.worker_pool`）。
- **仍开放**：
  - Tag 等多场景与 Collector 的完整对接（若产品仍需要独立 Collector 叙事）。
- **详见**：[engines/ARCHITECTURE.md §8](../core/engines/ARCHITECTURE.md)、[storage-domains.md](./storage-domains.md)

---

## 决策 12：DECIMAL 存储 + infra 统一出入库标量契约

- **背景**：
  - MySQL / PostgreSQL 的 `DECIMAL` / `NUMERIC` 列经驱动读出为 Python `decimal.Decimal`，与回测路径中的 `float` 混算会产生比较、序列化、前链校验等隐蔽错误。
  - DuckDB 读路径曾使用 `fetchdf()` → pandas，导致 `numpy` 标量类型与 MySQL/PG 不一致。
  - 在业务层分散写 `float()` / `_to_float_or_none` 等「兼容」无法覆盖 raw SQL、JOIN、新 Model，且责任边界不清。
- **决策**：
  1. **存储**：schema 继续使用 `DecimalField` → `DECIMAL(p,s)`（库内定点语义清晰）；**不**因应用算 float 而改回 `DOUBLE`。
  2. **读出口（唯一）**：所有 backend 的 `connector.execute_query` 返回前调用 `query_rows.normalize_query_rows`：
     - `Decimal` → `float`
     - `numpy` 标量 → 原生 `int` / `float` / `bool`
     - `float` NaN → `None`
  3. **写入口（统一）**：`row_sql.rows_to_value_tuples` / `to_upsert_params` / `BatchOperation.format_value_for_sql` 经同一套 `normalize_cell_value` 规范化后再落库。
  4. **DuckDB 读路径**：禁止 pandas；`fetchall()` + `description` / `columns` → `List[Dict]`，再经读出口规范化。
  5. **应用层契约**：`load` / `execute_sync_query` / `execute_raw_query` / JOIN 结果中的数值字段**已是 `float`/`int`**；业务代码**禁止**再写 Decimal/float 混用兼容层。
  6. **责任归属**：若应用层在「经 infra 读出的行」上仍遇到 `Decimal` 与 `float` 混算错误，**视为 `infra/db` bug**，应在 connector / `row_sql` 修，而非业务打补丁。
- **明确不在本决策范围**：
  - 外部 API、pandas DataFrame、CSV 等**数据源边界**的 `float()` 转换与业务舍入（如 `adj_factor_event` handler 的 `precision.py`：Tushare/AKShare 爬取专用，非 tables/infra 职责）。
- **禁止旁路**：
  - 业务代码绕过 `DatabaseManager` / connector 直连 `pymysql` 读 `DECIMAL`。
  - 在 `DbBaseModel`、Service、回测引擎中新增 `_to_float_or_none` 类补丁。
- **实现**（2026-06）：
  - `engines/shared/query_rows.py` — 读/写标量规范
  - `engines/shared/row_sql.py` — 写入口 `normalize_write_rows` / `rows_to_value_tuples`
  - `engines/{mysql,pgsql,duckdb}/connector.py` — 读出口
  - `table_queriers/services/batch_operation.py` — SQL 字面量格式化
  - `engines/shared/schema_introspection.py` — DuckDB 去 pandas
  - 测试：`__test__/test_query_rows.py`、`test_decimal_contract.py`、`test_row_sql_write.py`
- **影响**：
  - 新表 `decimal` 列无需在业务层处理 `Decimal`。
  - 旧代码中的 `float(row["factor"])` 应逐步删除（非数据源边界）。
  - 集成测试可用 DuckDB / MySQL 验证往返后类型为 `float`。

---

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [DESIGN.md](./DESIGN.md)
- [API.md](./API.md)
- [../README.md](../README.md)

