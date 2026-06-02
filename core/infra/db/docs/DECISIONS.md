# Database 模块决策文档

**版本：** `0.2.0`

---

## 决策 1：数据库后端支持 PostgreSQL / MySQL

- 背景：数据库适配层需要明确支持范围并控制维护成本。
- 决策：当前模块仅支持 PostgreSQL 与 MySQL。
- 理由：与当前适配器实现和测试覆盖一致。
- 影响：新增数据库方言时需补齐 adapter、配置校验和回归测试。

---

## 决策 2：采用三层管理架构

- 背景：连接、schema、表写入职责差异明显，混合实现难维护。
- 决策：拆分为 `ConnectionManager`、`SchemaManager`、`TableManager`，由 `DatabaseManager` 编排。
- 理由：降低耦合，便于测试与扩展。
- 影响：对外接口保持统一，对内按分层演进。

---

## 决策 3：默认实例机制保留

- 背景：显式传递 db 实例在大量调用链下成本高。
- 决策：保留 `set_default/get_default/reset_default` 机制。
- 理由：减少样板代码并支撑多进程下实例兜底初始化。
- 影响：调用方需管理初始化/释放时机；测试需主动 reset。

---

## 决策 4：写入主路径采用队列聚合

- 背景：高频写入直接落库会导致连接争用与性能抖动。
- 决策：默认写入路径使用 `queue_write` + `BatchWriteQueue`。
- 理由：提高吞吐并减少并发冲突。
- 影响：写入默认为异步；强一致场景需主动 `flush/wait`。

---

## 决策 5：继续使用直接 SQL + 参数化

- 背景：核心数据库路径要求性能可控和调优透明。
- 决策：采用适配器 + 参数化 SQL，不引入 ORM。
- 理由：减少抽象开销，便于性能定位与调优。
- 影响：需要持续维护 SQL 兼容性与文档一致性。

---

## 决策 6：DuckDB 三存储域（data / tag / strategy）

- 背景：嵌入式 DuckDB 单文件多表时全库单写者；`data_source` 批量写入、`strategy` 工作台写快照、多进程回测读行情会争用；不宜用单一 `sys_cache` 承载各域 KV。
- 决策：
  - 默认后端为 DuckDB，按 **`storage_domain`** 拆为三个库文件：`data.duckdb`、`tag.duckdb`、`strategy.duckdb`。
  - 每张表的 `schema.py` 声明 `storage_domain`；表名仍全局唯一，`get_table(name)` API 不变。
  - 缓存分散为各域自有 cache 表（如 `sys_data_cache`），废除集中式 `sys_cache` 语义。
  - 每域独立写管道；子进程回测对 data/tag 使用只读连接。
  - 未来因子挖掘使用预留枚举 `factor`，v1 不建库；tag 保持独立域，不并入 factor。
  - 决策者模式（ROADMAP 0.5.x）会话与曲线等表归入 **strategy** 域，不新增 `decision` domain；大状态走 userspace 磁盘（见 [存储域设计](./storage-domains.md) §9）。
- 理由：与 ROADMAP（tag 降级为分类器、因子模块单列）一致；隔离 renew 与 workbench 写入；域迁移可通过 ATTACH + COPY 按表进行。
- 影响：`DatabaseManager` 需域路由与 ATTACH；`DbCacheService`、`calendar_service`、`PersistenceService` 同步写路径需适配；跨域 SQL 须显式库前缀。
- 运行时：`database_type` 与 `表名 → storage_domain` 在 init 时构建并缓存；`get_table(name)` 对外签名不变，由注册表解析域并注入 model 连接（见文档 §4.4）。
- 详见：[存储域设计](./storage-domains.md)

---

## 决策 7：按 backend 拆分为独立 Engine 包（编排者模式）

- 背景：DuckDB 多域、写管道、多进程与 MySQL/PG 的 server 模型差异过大；原 `ConnectionManager` + 全局 `SchemaManager` / `TableManager` 三层架构中方言与特例分支持续膨胀。
- 决策：
  - 引入 `core/infra/db/engines/`，每种数据库一个 **平级** 包：`duckdb/`、`mysql/`、`pgsql/`。
  - 每个包内 **`engine.py` 为编排者**，组合 `connector`、`schema_parser`、`sql_adapter` 及按需模块（如 `table_ops`、`write_pipeline`）。
  - **`DatabaseManager` 只负责**：解析统一 config → 构造 `EngineConfigMeta` → factory 挂载 engine → 持有 conf 与 mounted engine → **转发**业务调用。
  - 连接、方言 SQL、DDL、写入路径等 **不再在 infra 层统一实现**；各 backend 在各自包内自洽。
  - 不使用胖 `BaseDatabaseEngine` 强迫三 backend 实现同一套 abstract API；挂载面保持 **薄且稳定**（详见 [engines 架构](../engines/ARCHITECTURE.md)）。
- 理由：与「各 db 行为是各自 engine 的行为」一致；避免 `if is_duckdb` 从 Model 挪到基类；DuckDB 专有模块不污染 mysql/pgsql。
- 影响：原决策 2 的三层公开架构（Manager 直暴露 Connection/Schema/Table）**逐步废弃**；`DbBaseModel` 最终只通过 Manager → engine 访问数据库；迁移完成前两套路径可能短期并存。
- 详见：[engines/ARCHITECTURE.md](../engines/ARCHITECTURE.md)

---

## 决策 8：MySQL 与 PostgreSQL 保持平级目录，不合并为 server/

- 背景：MySQL 与 PostgreSQL 实现相似，曾考虑 `engines/server/` 共享 connector / table_ops，以降低重复。
- 决策：
  - **禁止**将 mysql/pgsql 合并为 `server/` 或 `BaseServerEngine` 等隐式「第三 backend」。
  - 目录上对新人友好：`duckdb/`、`mysql/`、`pgsql/` **三目录对称**，改哪个 backend 只打开对应包。
  - 允许 **包内重复**；若重复维护成本过高，可抽到 `engines/_shared/`，且 shared 内 **不得** 含方言或 `engine_key` 分支（规则见 engines 架构 §6）。
- 理由：清晰边界优于 DRY；`server/` 易重新引入跨 backend 统一行为与 `if` 分叉，与决策 7 冲突。
- 影响：mysql/pgsql 可能有并行实现；抽 shared 需严格评审，默认 **先复制后抽取**。
- 详见：[engines/ARCHITECTURE.md](../engines/ARCHITECTURE.md) §2、§6

---

## 决策 9：DbBaseModel 委托表级 Engine，extension 仅用白名单 API

- 背景：`DbBaseModel` 内 `is_duckdb` 分支与直接调用 `DatabaseManager` 底层 API，与 engines 拆分目标冲突；需保证 `get_table` / 业务 Model 对外兼容。
- 决策：
  - `DbBaseModel` 构造时绑定 `self.engine = manager.mounted_engine.for_table(table_name)`。
  - 所有表操作 **转发** `self.engine.*`（`load` / `save` / `query` 等）；BaseModel 内禁止 backend 分支与直连 `connection_manager`。
  - 表作者（含 userspace）**仅允许** BaseModel 公开方法 + 受控 `query`（及可选 `cursor` / `transaction`）；领域方法内部只调白名单 API。
  - 业务 Model 仍继承 `DbBaseModel`；不继承 backend engine 类。
- 理由：对外破坏性最小；engine 只需实现白名单即可 cover 三 backend；extension 契约清晰。
- 影响：现有 `self.db.execute_sync_query` 等用法需逐步改为 `self.query`；`DataManager.get_table` 建议显式传入 `db=self.db`。
- 详见：[engines/ARCHITECTURE.md](../engines/ARCHITECTURE.md) §9

---

## 决策 10：JOIN 与 DuckDB 跨域查询（v1 不支持跨域写）

- 背景：DuckDB 多文件分域后，extension 作者在 Model 里写 JOIN 可能连错库；跨域写还涉及 write pipeline 与锁。
- 决策：
  - **MySQL/PG / DuckDB 同域**：表 Model 的 `load` / `query` 与同库（同域）JOIN **支持**。
  - **DuckDB 跨域读 JOIN**：由 duckdb engine **QueryPlanner** 负责（注册表名 → domain → ATTACH → qualify）；无法安全解析时 fail fast。随 engines 迁移实现。
  - **DuckDB 跨域写 SQL**（含跨文件 `INSERT…SELECT…JOIN` 等）：**v1 不支持**；当前无产品用例。写路径使用单表 `upsert` / `upsert_many` 等白名单 API。
  - 复杂跨表 JOIN 仍 **优先 DataService**（与现有 core 一致）。
- 理由：跨域读可透明路由；跨域写需 write planner 与 pipeline 协同，v1 不做；避免 silent 写错库。
- 影响：extension 文档须说明跨域写限制；未来若需要跨域写，单独立项设计 write planner。
- 详见：[engines/ARCHITECTURE.md](../engines/ARCHITECTURE.md) §10、[storage-domains.md](./storage-domains.md) §4.3

---

## 决策 11：DuckDB 每域 WritePipeline + 多进程 Collector

- 背景：DuckDB 单文件单写者；多进程 Tag 等同文件争用导致文件锁、WAL 回放失败与 stall；需与三 storage_domain 拆分一致。
- 决策：
  - **Per-domain WritePipeline**：`data` / `tag` / `strategy` **各一套**写队列；**域内串行、域间并行**；禁止 global 单 pipeline 锁三文件。
  - **库单元不变量**：并发/备份按 `.duckdb` + `.wal` + RW 持有者整体考虑。
  - **CHECKPOINT 策略**：批末/sync flush 后积极 `CHECKPOINT` 缩短 WAL；不手删 WAL；CHECKPOINT **不**视为已释放文件占锁。
  - **多进程写**：worker **不直连**写库；主进程 **Result Collector** → 按表 domain 入对应 pipeline 批量写。
  - 实现模块：`duckdb/write_pipeline.py`、`duckdb/worker_scope.py`、`duckdb/connector.py`（见 engines 架构 §8）。
- 理由：三域并行保留 renew/tag/workbench 吞吐；同文件避免多进程 connect；与 MySQL server 模型切割清晰。
- 影响：Tag `ProcessWorker` 等需改为结果回传 + 主进程写；`PersistenceService` 接入 data pipeline。
- 详见：[engines/ARCHITECTURE.md §8](../engines/ARCHITECTURE.md)、[storage-domains.md §4.1–§4.2](./storage-domains.md)
