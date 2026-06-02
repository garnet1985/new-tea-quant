# Database Engines 架构（定案）

**状态：** 已定案，逐步迁移中  
**版本：** `1.2.0`  
**日期：** 2026-05-28（§8 库单元/Pipeline §9–§10 DbBaseModel/JOIN 定案）

本文档记录 `core/infra/db/engines/` 的目标结构与职责边界。实现尚未完全落地；当前运行时仍以 `DatabaseManager` + 三层管理（Connection / Schema / Table）为主，见 [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)。

---

## 1. 设计原则

1. **各 backend 自管行为** — MySQL、PostgreSQL、DuckDB 的差异在各自 engine 包内实现，不在 infra 层用统一逻辑强行对齐。
2. **外层只挂载、只转发** — `DatabaseManager` 负责发现配置、构造 meta、选型挂载 engine，并把业务调用委托给当前 engine。
3. **三个平级 engine 包** — `duckdb/`、`mysql/`、`pgsql/` 目录结构对称、边界清晰，便于新人按 backend 阅读全貌。
4. **重复优于过早抽象** — MySQL 与 PostgreSQL 相似处允许复制；仅在重复造成维护痛点时，才抽到可选的 `_shared/`  helpers。
5. **禁止隐式「第三 backend」** — 不得将 mysql/pgsql 合并为 `server/` 或 `BaseServerEngine` 等中间层，以免边界再次模糊。

---

## 2. 目录结构（定案）

```text
core/infra/db/engines/
├── ARCHITECTURE.md          # 本文档
├── meta.py                  # EngineConfigMeta（Manager 构造，Engine 只读）
├── factory.py               # 按 engine_key 挂载具体 Engine
├── _shared/                 # 可选：无方言、无 backend 分支的纯工具（见 §6）
├── duckdb/
│   ├── engine.py            # 编排入口
│   ├── connector.py
│   ├── schema_parser.py
│   ├── sql_adapter.py       # 方言化 SQL（命名可与现有 adapter 对齐）
│   ├── table_ops.py         # 表级读写、队列等（按需）
│   ├── write_pipeline.py    # DuckDB 特有
│   └── worker_scope.py      # 多进程 / 只读域等（按需）
├── mysql/
│   ├── engine.py
│   ├── connector.py
│   ├── schema_parser.py
│   ├── sql_adapter.py
│   └── table_ops.py
└── pgsql/
    ├── engine.py
    ├── connector.py
    ├── schema_parser.py
    ├── sql_adapter.py
    └── table_ops.py
```

**明确不做：**

- 不设立 `engines/server/` 作为 mysql+pgsql 的共享 engine 层。
- 不设立塞满 abstract 方法的胖 `BaseDatabaseEngine`，强迫三 backend 实现同一套能力（如 checkpoint、multiprocess scope 等 DuckDB 专有项）。

`base_engine.py`（若仍存在）为早期草案，**不以本文档为准**；迁移完成后应删除或替换为极薄的挂载 Protocol（若有）。

---

## 3. 层次职责

### 3.1 DatabaseManager（外层）

| 负责 | 不负责 |
|------|--------|
| 读取 `userspace/system/config/database`，解析为统一 config + **EngineConfigMeta** | 连接细节、SQL 方言、DDL 生成 |
| 按 `engine_key` 通过 factory **挂载** 一个 engine | 在 engine 内部实现 backend 分支 |
| 持有当前 engine 的 conf 与 mounted engine 引用 | Schema migrate 的业务 SQL（可委托 engine 或独立 migration 模块） |
| 对外暴露 `database_type` 等**外层业务判断**（若上层需要） | 用 `is_duckdb` 等标志驱动 engine 内部逻辑 |
| 将 `DbBaseModel` / 业务层的数据库调用 **转发** 给 mounted engine | DuckDB write pipeline、IPC 等实现细节 |

### 3.2 Engine（各 backend 的 `engine.py`）

Engine 是**编排者**，组装本包内模块，对外提供挂载面（方法集合由迁移阶段与 `DbBaseModel` 需求共同收敛，保持薄且稳定）。

| 模块 | 职责 |
|------|------|
| **connector** | 连接池生命周期、事务/游标、**执行**已准备好的 SQL（无方言分支以外的 I/O） |
| **sql_adapter** | **仅方言**：占位符、`?`→`%s`、exists/introspection SQL 文本、upsert 片段等（**无 I/O**） |
| **schema_parser** | 将项目 schema 定义转为本方言 DDL / introspection |
| **table_operator**（或 `table_ops.py`） | 表级 CRUD；调用 connector + sql_adapter / `BatchOperation(database_type=…)` |
| **engine.py** | 编排上述模块；**不**放入 `_shared/` 与其它 backend 合并 |
| **其它（按需）** | DuckDB：`write_pipeline`、`worker_scope`；其它 backend 仅在本包内扩展 |

Engine **只消费** Manager 传入的 meta，**不**向上声明「我是 duckdb/mysql」；上层通过 Manager 获知 backend 类型。

### 3.3 与现有模块的对应关系（迁移参考）

| 现状 | 目标归属 |
|------|----------|
| `ConnectionManager` | 各 engine 的 **connector**（私有化，不再作为 Manager 的公开子系统） |
| `table_queriers/adapters/*` | 各 engine 的 **connector**（旧名 adapter；re-export 兼容） |
| `SchemaManager` 中的方言分支 | 各 engine 的 **schema_parser** |
| `TableManager` + `BatchWriteQueue` | mysql/pgsql 的 **table_ops**；DuckDB 的 **table_ops** + **write_pipeline** |
| `StorageRegistry` / 表→域 | Manager 或 **duckdb engine** 私有（server DB 无此概念） |
| `schema_management/field/*` | 仍为跨 backend 的 **schema 语言**；parser 负责 field → DDL |

---

## 4. 挂载契约（薄接口）

各 engine 对外暴露的方法名应一致 enough 供 `DatabaseManager` 转发，但**实现完全 per-backend**。

典型入口（名称可在实现阶段微调）：

- 生命周期：`initialize(meta, context)` / `close()`
- 数据面：`query_for_table(...)`、`upsert_many(...)`、`cursor_for_table(...)` 等 — 以 `DbBaseModel` 实际调用为准

不在公共基类上规定 DuckDB 专有 API；专有能力通过 duckdb 包内模块由 engine 编排，或仅 Manager 在已知 duckdb 配置下调用 engine 的扩展点（仍不污染 mysql/pgsql 包）。

---

## 5. EngineConfigMeta 与配置

**合并**仍在 `project_context.ConfigManager.load_database_config()`（`core/default_config` + `userspace/system/config` + env），**不在** engine 包内读 JSON。

`DatabaseManager` → `DBHelper.parse_database_config` → `build_engine_meta()` 解析为类型化配置：

| 字段 | 说明 |
|------|------|
| `engine_key` | factory 选型 |
| `raw_config` | merge 后的完整 dict |
| `backend` | `MysqlSettings` / `PgsqlSettings` / `DuckdbSettings`（各 engine 包内 `settings.py`） |
| `batch_write` | `BatchWriteSettings`（`infra/db/settings/common.py`） |
| `backend_config` | merge 后的 backend dict 视图（兼容） |
| `options` | 运行时开关（verbose、DuckDB checkpoint 等） |

Engine / connector 优先使用 `meta.require_mysql()` 等，不再散落 `config.get(...)`。

---

## 6. `_shared/` 使用规则（定案）

仅当**同时满足**以下条件时，才将代码放入 `engines/_shared/`：

1. 逻辑对三 backend **完全相同**，且无方言差异。
2. 预期**不会**按 backend 分叉；若将来分叉，应迁回各自 engine 包。
3. **禁止**在 shared 模块内出现 `engine_key`、`database_type` 或 `if postgresql` 类分支。

允许 shared 的内容示例：纯字符串工具、与方言无关的重试 helper、测试 fixture。

**不允许** shared 的内容：connector 生命周期、schema→DDL、batch write 语义、transaction 策略。

默认策略：**先在各 engine 包内复制，第三次重复再考虑抽 shared 函数** — 不抽 `BaseServerEngine`。

---

## 7. 与 DuckDB 存储域的关系

DuckDB 三存储域（data / tag / strategy）的**产品决策**见 [决策 6](../docs/DECISIONS.md) 与 [storage-domains.md](../docs/storage-domains.md)。

在 engines 架构下：

- 域路由、多文件连接、写管道、子进程只读 — **全部在 `duckdb/` 包内**。
- `DatabaseManager` 可持有表→域映射并注入 runtime context，但不在 mysql/pgsql engine 中出现 domain 概念。

---

## 8. DuckDB：库单元、CHECKPOINT 与写 Pipeline（定案）

### 8.1 库单元（不变量）

并发、备份、拷贝时，始终以 **库单元** 为单位，而非仅 `xxx.duckdb`：

```text
库单元 = xxx.duckdb + xxx.duckdb.wal（若存在）+ 谁占 RW 连接
```

- 只拷贝 `.duckdb` 而忽略 `.wal` 可能丢未 checkpoint 的已提交数据。
- **CHECKPOINT 成功 ≠ 文件已无人占用**；主进程 RW 仍开着时，子进程连同一文件仍可能失败（尤其 macOS）。

### 8.2 CHECKPOINT（运行策略）

- `CHECKPOINT` 为 **同步** SQL：将 WAL 中 **已提交** 数据合并进主库；成功后 WAL 由 DuckDB 截断/清空，**禁止**手删 `.wal`。
- 策略：**批末积极 CHECKPOINT**（renew 每批、pipeline flush、`close()`），缩短 WAL 尾巴；设计上 **仍假设** WAL 可能存在（崩溃、批间窗口）。
- 实现沿用 `duckdb_wal_policy.py`；duckdb `connector` / `write_pipeline` 在批边界调用。

### 8.3 Per-domain WritePipeline（域间并行、域内串行）

**不是** 全 DuckDB 一个 global pipeline。**每个 storage_domain 一套**：

```text
data.duckdb      → DataWritePipeline
tag.duckdb       → TagWritePipeline
strategy.duckdb  → StrategyWritePipeline
```

| 范围 | 规则 |
|------|------|
| **跨域** | 三 pipeline **可同时写**（renew data ∥ Tag 写 tag ∥ workbench 写 strategy） |
| **同域** | 该文件 **单写者路径**；写 job **队列串行**（可 batch 合并 upsert） |
| **单进程多线程** | 同域仍需 adapter 锁 + pipeline（线程锁，非 OS 多进程文件锁） |

模块归属：`duckdb/write_pipeline.py`（每域队列 + flush + checkpoint 钩子）、`duckdb/connector.py`（RW 连接生命周期）。

MySQL/PG engine **无** 此文件锁 pipeline（server 管并发）。

### 8.4 多进程：Worker 不连库 + Result Collector

OS 级文件锁问题主要出现在 **多进程同时 `connect` 同一 `.duckdb`**。

| 做法 | 说明 |
|------|------|
| **Worker** | 不算库 / **不写库** / 理想情况 **不连库**；只返回可序列化结果 |
| **主进程 Collector** | 汇总 worker 结果，按目标表 **domain** 入对应 **WritePipeline** |
| **禁止** | 多 worker 各自 `upsert` 同一 tag.duckdb（即使「排队领锁」仍低效且易死锁） |

模块归属：`duckdb/worker_scope.py`（子进程禁直连契约；与 Tag `ProcessWorker` 等集成）。

回测子进程若必须读 **data**：优先 spawn 前预加载 / 只读快照；若只读连库，须与主进程 renew 写 **错开** 或 checkpoint 后短暂开窗（仍非首选）。

### 8.5 与 §7 的关系

§7 定三域拆分动机；本节定 **WAL + 写并发 + 多进程** 在 `duckdb/` 包内的实现契约。详见 [storage-domains.md §4.1–§4.2](../docs/storage-domains.md)。

---

## 9. DbBaseModel 与表级 Engine 绑定（定案）

### 9.1 绑定方式

- `DatabaseManager.initialize()` 按 config 挂载 **一个** backend engine（如 `MySQLEngine`）。
- `DbBaseModel(table_name, db=manager)` 构造时绑定：

```text
self.db = manager
self.engine = manager.mounted_engine.for_table(table_name)
```

- `self.engine` 是 **表级门面**（per-table）；在 BaseModel 内部统一此名，底层实现因 backend 而异。
- 对外 **`DbBaseModel` 公开 API 不变**；`get_table("sys_xxx")` 仍返回业务 Model 子类实例。

### 9.2 委托规则

`DbBaseModel` 的表操作 **一律转发** `self.engine.*`，例如：

```text
DbBaseModel.load(...)   →  self.engine.load(...)
DbBaseModel.query(...) →  self.engine.query(...)
```

BaseModel 内 **禁止** `if is_duckdb` / 直接访问 `connection_manager` / `execute_sync_query`。

### 9.3 业务 Model 白名单（extension 契约）

继承 `DbBaseModel` 的表作者（含 userspace 扩展）**只允许**使用：

| 允许 | 说明 |
|------|------|
| BaseModel 公开方法 | `load`, `load_one`, `count`, `save`, `upsert`, `upsert_many`, `delete`, `create_table`, `load_schema` 等（以实现为准） |
| 受控 raw query | `query(sql, params)`；可选 `cursor()`, `transaction()` |
| 领域方法 | 自定义 `load_by_*` 等，**内部只调上表 API** |

| 禁止 | 说明 |
|------|------|
| `self.db.connection_manager` | 绕开 engine 路由 |
| `self.db.execute_sync_query` 等底层 API | 同上 |
| `self.db.is_duckdb` 分支 | backend 判断属于 Manager / infra |
| 直接连库 / 直接 import adapter | 破坏挂载契约 |

Engine 只需实现白名单对应能力；表作者遵守契约即可保证三种 backend 可被 handle。

### 9.4 业务 Model vs backend Engine

- **表作者**继承 `DbBaseModel`，写领域查询方法。
- **infra 作者**实现 `duckdb/engine.py` 等 backend 包。
- 表作者 **不** 继承、不依赖 mysql/duckdb engine 类。

---

## 10. 查询、JOIN 与 DuckDB 跨域（定案）

### 10.1 MySQL / PostgreSQL

- 单库连接；表 Model 的 `load` / `query` 与同库 **JOIN** 无额外限制。
- `query` 经 engine 执行即可。

### 10.2 DuckDB 同 storage_domain（同 `.duckdb` 文件）

- 单域内多表 **JOIN**（如 `sys_stock_klines` ⋈ `sys_adj_factor_events`）：**支持**。
- 与 MySQL 语义相同，走该域 connector。

### 10.3 DuckDB 跨 storage_domain（跨 `.duckdb` 文件）— 读

- 技术上可通过 **ATTACH** + 表名 qualify（如 `data.main.sys_stock_list`）执行 **只读** JOIN。
- 因表名 **全局唯一**，engine 可实现 **QueryPlanner**：扫描 SQL 中注册表名 → 映射 domain → ATTACH → qualify → 执行。
- **实现优先级：** 随 engines 迁移逐步落地；extension 作者可写不含 domain 前缀的 SQL，由 duckdb engine 负责路由（详见 [storage-domains.md §4.3](../docs/storage-domains.md)）。
- 复杂 SQL 无法安全解析时：**fail fast**，提示拆查询或改用 Service。

### 10.4 DuckDB 跨 storage_domain — 写（v1 不支持）

- **跨域写 SQL**（含 `INSERT … SELECT … JOIN` 跨 data/tag/strategy 文件、跨域 `UPDATE`/`DELETE` 等）：**v1 明确不支持**。
- 理由：需协调多域 write pipeline、写锁与误写防护；**当前产品无此用例**。
- 表 Model 的写路径应使用 **`upsert` / `upsert_many` 等 Base 白名单 API**（单表、单域）。
- 跨表/跨域 **读** JOIN 优先放在 **DataService**；现有 core 代码亦以 Service 层 JOIN 为主。
- 若未来出现跨域写需求，单独设计 **write planner**（识别写目标 domain、走对应 pipeline），不与读 query 共用「静默 ATTACH」路径。

### 10.5 JOIN 职责小结

| 场景 | 表 Model（DbBaseModel 子类） | Service 层 |
|------|------------------------------|------------|
| 同域 / 单库 JOIN | ✅ `query` | ✅ |
| DuckDB 跨域读 JOIN | ✅ `query`（engine planner，待实现） | ✅ 推荐 |
| DuckDB 跨域写 JOIN | ❌ v1 不支持 | ❌ v1 不支持；改用单域 upsert 或分批写 |

---

## 11. 相关文档

- [../docs/DECISIONS.md](../docs/DECISIONS.md) — 决策 7–11
- [../docs/storage-domains.md](../docs/storage-domains.md) — DuckDB 存储域、§4.2 并发与 WAL
- [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) — 当前（迁移前）三层架构说明
