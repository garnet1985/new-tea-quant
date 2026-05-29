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
