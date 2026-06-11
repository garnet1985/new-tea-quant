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
| 11 | DuckDB WritePipeline + 多进程 | 🔶 部分（WritePipeline ✅；`worker_scope` / Collector 待做） |
| 12 | DECIMAL 存储 + infra 统一出入库标量契约 | ✅ 已实现 |

---

## 决策 1：数据库后端支持 PostgreSQL / MySQL / DuckDB

- **背景**：适配层需明确支持范围并控制维护成本。
- **决策**：模块支持 **PostgreSQL**、**MySQL**、**DuckDB**（默认本地三域文件）。
- **理由**：DuckDB 为 NTQ 默认嵌入式后端；server 库用于部署可选。
- **影响**：新方言须新增 `engines/<backend>/` 包、`schema_parser`、factory 分支与测试。
- **实现**：`engines/mysql`、`engines/pgsql`、`engines/duckdb`；配置经 `parse_database_config` + `build_engine_meta`。

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
- **实现**：各 `sql_adapter`、`table_operator`；`engines/_shared/row_sql` 辅助批量拼装。

---

## 决策 6：DuckDB 三存储域（data / tag / strategy）

- **决策**：按 `storage_domain` 拆为三库文件；表名全局唯一；`get_table(name)` API 不变。
- **实现**：`StorageRegistry`、`DuckdbDomainCatalog`、`engines/duckdb/paths.py`；init 时 `rebuild_table_file_map`。
- **详见**：[storage-domains.md](./storage-domains.md)

---

## 决策 7：按 backend 拆分为独立 Engine 包（编排者模式）

- **决策**：
  - `core/infra/db/engines/{duckdb,mysql,pgsql}/`，每包 `engine.py` 编排 `connector`、`schema_parser`、`sql_adapter`、`table_operator` 等。
  - `DatabaseManager`：解析配置 → `create_engine` → 转发业务调用。
  - 无胖 `BaseDatabaseEngine`；共享逻辑仅放 `engines/_shared/`（无 `engine_key` 分支）。
- **实现**：✅ 已完成（v0.3.0）；根目录 `schema_manager.py`、`migrate_manager.py`；无 `helpers/` 兼容层。
- **详见**：[engines/ARCHITECTURE.md](../engines/ARCHITECTURE.md)

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

## 决策 11：DuckDB 每域 WritePipeline + 多进程 Collector（部分）

- **已实现**：
  - 每域 `WritePipeline`；`wal_policy`；批末 / SIGINT / `checkpoint_duckdb`。
  - `connector` 多域连接、`domain_catalog` 动态表→文件映射。
- **待实现**：
  - `duckdb/worker_scope.py`：子进程不直连写库，主进程 Collector 按域入队（见 engines 架构 §8）。
  - Tag 多进程等场景与 Collector 的完整对接。
- **详见**：[engines/ARCHITECTURE.md §8](../engines/ARCHITECTURE.md)、[storage-domains.md](./storage-domains.md)

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
  - 外部 API、pandas DataFrame、CSV 等**数据源边界**的 `float()` 转换（如 `data_source` handler）。
  - 表级**业务舍入**（如 `adj_factor_events/precision.py`）：入库前按配置 quantize，且**只接受 `float`/`int`**，不接受 `Decimal`。
- **禁止旁路**：
  - 业务代码绕过 `DatabaseManager` / connector 直连 `pymysql` 读 `DECIMAL`。
  - 在 `DbBaseModel`、Service、回测引擎中新增 `_to_float_or_none` 类补丁。
- **实现**（2026-06）：
  - `engines/_shared/query_rows.py` — 读/写标量规范
  - `engines/_shared/row_sql.py` — 写入口 `normalize_write_rows` / `rows_to_value_tuples`
  - `engines/{mysql,pgsql,duckdb}/connector.py` — 读出口
  - `table_queriers/services/batch_operation.py` — SQL 字面量格式化
  - `engines/_shared/schema_introspection.py` — DuckDB 去 pandas
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
