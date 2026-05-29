# 存储域（Storage Domain）设计

**状态：** 研究定案（待实现）  
**日期：** 2026-05-28  
**关联：** DuckDB 嵌入式后端、`DataManager` / `DatabaseManager` 演进

---

## 1. 背景与目标

- **目标：** 用户无需安装 MySQL/PostgreSQL，默认使用嵌入式 DuckDB；保持 `DataManager` / `DbBaseModel` / `data_source` 上层 API 基本不变。
- **放弃：** 不以列式文件（如 Parquet）作为主存储；大结果继续走磁盘（如 strategy 仿真 `results/simulations/`）。
- **动机：** 单 `.duckdb` 多表时，全库单写者；`data_source` 批量 renew、`strategy` 工作台写快照、多进程回测读行情会互相排队或抢锁。按**业务域拆文件** + **每域写管道** 隔离。

---

## 2. 三个 Storage Domain（v1）

| `storage_domain` | 文件（默认路径示例） | 职责 |
|------------------|----------------------|------|
| **data** | `data/data.duckdb` | 外部抓取、行情、宏观、股票主数据、交易日历、供应商指标等 |
| **tag** | `data/tag.duckdb` | 标签场景/定义/值；未来降级为「股票分类器」仍留本域 |
| **strategy** | `data/strategy.duckdb` | 策略运行时 DB 产出（含 `sys_strategy_workbench_snapshot` 等中间缓存） |

**预留（v1 不建库）：** `factor` — 因子挖掘模块上线后再加。

**UI：** 暂无独立 domain；无持久化 UI 表前不单独拆库。

### 2.1 schema 约定

在 `core/tables/**/schema.py`（及 userspace 表）顶层增加：

```python
schema = {
    "name": "sys_stock_klines",
    "storage_domain": "data",  # data | tag | strategy
    ...
}
```

- **唯一真相：** 路由、建表、备份以 `storage_domain` 为准，不以目录路径猜测。
- **表名：** 仍全局唯一（`sys_*`），`get_table("sys_tag_value")` 签名不变。

### 2.2 缓存表（分散，不集中）

废除全局单表 `sys_cache` 承载所有域的 KV。

| 域 | 建议表名 | 典型 key / 用途 |
|----|----------|-----------------|
| data | `sys_data_cache` | `stock_list_last_update`、calendar 日缓存等 |
| tag | `sys_tag_cache` | tag 批处理断点（若需要） |
| strategy | `sys_strategy_cache` | 策略侧短效 KV（若需要；/workbench 主缓存仍是 snapshot 表） |

`sys_meta_info` 建议归属 **data**（系统级 JSON KV，量小）。

`sys_schema_migration_log`：每域独立迁移历史，或指定 **data** 为主 catalog（实现阶段二选一）。

---

## 3. 表归属一览（core/tables）

### data（26 张）

- **股票时序：** `sys_stock_klines`, `sys_stock_indicators`, `sys_adj_factor_events`, `sys_corporate_finance`, `sys_stock_st_periods`
- **主数据与维度：** `sys_stock_list`, `sys_industries`, `sys_boards`, `sys_markets`, `sys_areas`, `sys_stock_*_map`
- **指数：** `sys_index_list`, `sys_index_klines`, `sys_index_weight`
- **日历：** `sys_trade_calendar`
- **宏观：** `sys_cpi`, `sys_ppi`, `sys_pmi`, `sys_gdp`, `sys_lpr`, `sys_shibor`, `sys_money_supply`
- **系统：** `sys_meta_info`（建议）, `sys_data_cache`（新建，替代原 `sys_cache` 中 data 相关 key）

### tag（3 张）

- `sys_tag_scenario`, `sys_tag_definition`, `sys_tag_value`
- `sys_tag_cache`（新建，可选）

### strategy（core + userspace 默认归此域）

**已有 / 规划中的 DB 表：**

- `sys_strategy_workbench_snapshot` — 自动三步（enum / price / capital）工作台快照与 DbCache
- **决策者模式（ROADMAP 0.5.x，规划）：** 交互式按日推进的会话与曲线，**不单独拆 domain**，表名实现时再定，例如：
  - `sys_decision_session` — 会话主记录（策略名、区间、当前 simulation date、状态）
  - `sys_decision_step`（或按日拆分）— 用户每日仓位决策、权益/回撤曲线点
- userspace `cust_*` 自定义表默认 **strategy**，除非 schema 显式声明
- `sys_strategy_cache`（新建，可选）

**磁盘（userspace，与 workbench 并列）：**

- `results/simulations/...` — 自动模拟大结果（已有）
- `decision_sessions/<session_id>/...`（规划）— 每日完整账户快照、决策者 report 成品；机会列表优先 **读 enum 磁盘产物 + data**，不必重复落库

**写入注意：** 工作台批量写 snapshot 与决策者「下一天」autosave 同属 strategy 域，共用写管道并支持 **交互写高优先级**（见 §4.1）。

---

## 4. 架构要点

```text
DataManager / DbBaseModel
        │
        ▼
DomainRouter（按 schema.storage_domain 选连接）
        │
        ├── data.duckdb     ← Connection + WritePipeline
        ├── tag.duckdb      ← Connection + WritePipeline
        └── strategy.duckdb ← Connection + WritePipeline（可高优先级 UI 写）

跨域 SQL：主连接 ATTACH 其余库，如 tag.main / data.main
```

### 4.1 写并发

- **每域一个写管道**（可复用现有 `BatchWriteQueue` 思路）：同文件禁止多线程裸写。
- **data_source** 的 `PersistenceService.upsert_many` 目前**同步直写**，DuckDB 阶段应接入 data 域管道或在 adapter 层串行化。
- **strategy** 工作台 `update_result_report` / `create_snapshot`：strategy 域管道；UI 关键路径需 `flush`。
- **enumerator/scanner 子进程**：对 **data**（及读 tag 时 **tag**）使用**只读**连接；不写 strategy 库。

### 4.2 读并发

- renew 写 data 时，回测读 K 线：一般可读，可能变慢；data 与 strategy **分文件** 后 UI 写快照不与 K 线 renew 共抢一文件。

### 4.3 跨域 JOIN

- 同域内 JOIN（如 `sys_stock_klines` + `sys_adj_factor_events`）：单库内 SQL，无变化。
- 跨域（如 `workbench` 读 `sys_stock_list`）：`ATTACH data AS data; SELECT ... FROM data.sys_stock_list`。
- 实现前：**禁止**假设 `execute_sync_query` 无前缀表名能跨库 JOIN。

### 4.4 运行时解析（定案）

对外 **`get_table("sys_stock_list")` 等 API 与表名字符串准则不变**；域路由在 `DataManager` / `infra.db` 初始化时一次性建好，进程内只读使用。

#### 4.4.1 启动时缓存「用户使用的数据库类型」

`DataManager.initialize()` → `DatabaseManager.initialize()` 时，通过 `ConfigManager.load_database_config()` 读取配置**一次**，在内存中保留（例如挂在 `DatabaseManager.config` 或 `StorageRegistry`）：

- `database_type`：`mysql` | `postgresql` | `duckdb`
- duckdb 时附加：`domain → db_path`、`domain → ConnectionManager`、每域写管道句柄

运行期间按 `database_type` 分支，**不再重复读配置文件**：

| `database_type` | 行为 |
|-----------------|------|
| `mysql` / `postgresql` | 单 adapter；`storage_domain` 可忽略，全部走同一连接 |
| `duckdb` | 启用三域文件、域路由、ATTACH、每域写管道 |

多进程场景下每个进程各自初始化一份（与现有 `DatabaseManager` 单例语义一致）。

#### 4.4.2 启动时构建 `表名 → storage_domain` 映射

在表发现/注册阶段（`create_all_tables`、`_discover_tables`、`register_table`）读取每张表 `schema.py` 的 `storage_domain`，写入内存注册表，例如：

```text
TableDomainRegistry["sys_stock_list"]     → "data"
TableDomainRegistry["sys_tag_value"]      → "tag"
TableDomainRegistry["sys_strategy_workbench_snapshot"] → "strategy"
```

**构建时机：** 与现有 `register_table` / `_discover_tables` 一致；userspace 晚注册表时**追加**条目并建表，而非仅在首次 init 写死。

**启动校验（fail fast）：**

- 每张表必须声明 `storage_domain`（或项目明确约定的默认值，建议避免静默猜测）
- 枚举合法：`data` | `tag` | `strategy`（将来扩展 `factor`）
- 表名全局唯一（保持现状）
- duckdb 模式下：map 中出现的每个 domain 均已创建对应连接/文件

#### 4.4.3 `get_table` 行为（API 不变）

```text
get_table(table_name)
  → 查 _table_cache 得 Model 类
  → 查 TableDomainRegistry[table_name] 得 domain
  → return ModelClass(db=connection_for(domain))
```

调用方（`data_source`、`strategy`、`DataService`）**无需**传入 domain 参数；`config.table` 仍为 `sys_*` 字符串。

**内部约束：** `DbBaseModel` 实例上的 `self.db` 必须是**该表所属域**的连接管理器，以便同域 `load` / `upsert` / 裸 SQL JOIN 落在正确 duckdb 文件上。仅建 map 却仍让所有 model 使用 `DatabaseManager.get_default()` 单连接，无法达到分域目的。

#### 4.4.4 建议实现载体：`StorageRegistry`

可将下列内容收敛为一个只读注册对象（或作为 `DatabaseManager` 的组成部分）：

```text
StorageRegistry
  .database_type: str
  .table_to_domain: Dict[str, str]
  .domain_connections: Dict[str, ConnectionManager]   # duckdb 时有效
```

`get_table` 多一次 dict 查找，开销可忽略。

#### 4.4.5 与「隐患审计」的关系

- 第 7 节所列多数调用点**无需改 API**；需在 infra 层消费 `TableDomainRegistry` 并正确注入 `model.db`。
- `DataService` 中 `self.db = DatabaseManager.get_default()` 的裸 SQL：应改为使用**当前服务涉及的域**的连接，或保证 default 门面在 duckdb 模式下能按 SQL 路由（第一版推荐前者：model / service 绑域连接）。

---

## 5. 域迁移（未来）

- **改 domain：** 更新 schema 的 `storage_domain` + 用 DuckDB `ATTACH` + `CREATE TABLE xx AS SELECT * FROM old.xx` 迁数据 + 删旧表。
- **整库改名：** 仅当域内**所有表**一起迁移时，可改 `db_path` 配置文件。
- 枚举预留 `factor` 即可，不必提前建空库。

---

## 6. 与 MySQL 的关系

- MySQL/PostgreSQL 仍为可选后端；`storage_domain` 对单库多表模式可忽略或映射到同一 adapter。
- 默认新用户：`database_type=duckdb` + 三域配置（`core/default_config/database/`）。

---

## 7. DataManager 调用面隐患审计

实现三域前，以下调用点需改造或验证（**当前均假设单库单连接**）。

### 7.1 基础设施（必须先改）

| 位置 | 风险 | 建议 |
|------|------|------|
| `DatabaseManager` / `ConnectionManager` | 单 adapter、单配置 | 引入 `DomainConnectionRegistry`；`get_sync_cursor(domain)` 或 model 绑定域连接 |
| `DbBaseModel.__init__` | 所有 model 共用 `DatabaseManager.get_default()` | model 按表 schema 解析 domain，持有对应 `db` 句柄 |
| `SchemaManager.create_all_tables` | 一次建所有表于同一库 | 按 domain 分组建表到对应 duckdb |
| `migration/*` introspection | 单库 information_schema | 每域迁移或主域 catalog + 域版本表 |
| `DataManager.get_physical_table_name` | 仅 PG schema 前缀 | DuckDB 跨 attach 时改为 `data.sys_stock_list` 等形式 |

### 7.2 裸 SQL `execute_sync_query`（跨表同库假设）

| 模块 | 表 | 域 | 说明 |
|------|-----|-----|------|
| `kline_service` | klines + adj_factor_events；list + klines | 均 data | 同域，安全 |
| `stock_service` | list + map + industries + klines | 均 data | 同域，安全 |
| `tag_service` | tag_value + tag_definition | 均 tag | 同域，安全 |
| `workbench_snapshot/model` | 硬编码 `UPDATE sys_strategy_workbench_snapshot` | strategy | 须走 strategy 连接或去硬编码 |
| `adj_factor_events/model` 等 table model | 单表 + 偶发查 stock_list | 多在同域 | 逐文件核对 |

**隐患：** 上述服务里 `self.db = DatabaseManager.get_default()` — 若 default 只指向 data，tag/strategy 的 raw SQL 会打错库。

### 7.3 缓存 `sys_cache`（集中 → 分散）

| 位置 | 现状 | 改造 |
|------|------|------|
| `calendar_service` | `get_table("sys_cache")` | 改为 `sys_data_cache` 或 `DbCacheService.for_domain("data")` |
| `data_source_manager._clear_force_refresh_caches` | `dm.db_cache.delete("stock_list_last_update")` | data 域 cache API |
| `DbCacheService` | 写死 `sys_cache` | 按域路由或拆三个薄封装 |
| `DataService.db_cache` | 单例属性 | 可保留门面，内部按 key 前缀/显式 domain 路由 |

### 7.4 data_source

| 位置 | 说明 |
|------|------|
| `PersistenceService.save` | `get_table(config.table)` — 依赖路由；data 表为主 |
| `renew_*` / `date_range_helper` | 按表名读最新日期；表在 data 居多 |
| `execute` 多线程 `batch` 保存 | 同表并发写 → **data 域写管道** 必须覆盖 `upsert_many` 同步路径 |

### 7.5 strategy 模块

| 位置 | 域 | 说明 |
|------|-----|------|
| `SimulatorResDbCacheService` / `workbench.py` | strategy 写 | 高频更新 `reports` JSON |
| `workbench.py` `get_table("sys_stock_list")` | 读 data | **跨域**；需 ATTACH 或经 `DataManager.stock.list` 走 data 连接 |
| `StrategyDataInjectionService` / `DataContract` loaders | 读 data（+ tag） | 子进程只读；Contract 不感知 domain，loader 内部用 DataManager |
| `ProcessWorker` 多进程 | 读 data、写 strategy（主进程） | 子进程禁止打开 strategy 写连接；data 只读 |
| 磁盘 `results/simulations/` | 非 DB | 不受三域影响 |

### 7.6 tag 模块

| 位置 | 说明 |
|------|------|
| `tag_manager` / `base_tag_worker` | 写 `sys_tag_value` → tag 域管道 |
| `TagDataService` | 三表均在 tag；raw SQL 安全若连接正确 |
| `TagDataManager` | 通过 DataContract 读 data — 与 strategy 类似，只读 data |

### 7.7 其它

| 位置 | 说明 |
|------|------|
| `backup_and_restore_service` | 默认备份 `_table_cache` 全部表 → 需**按域分目录**或逐 duckdb 备份 |
| `demo_exporter` | 排除 cache/tag/snapshot；导出逻辑需知三文件路径 |
| `userspace/extensions/tables` | 注册时读 `storage_domain`，默认 strategy |
| 测试 / `DataManager()` 多处新建实例 | 多进程各一套连接；DuckDB 同文件多写者需避免 |

### 7.8 低风险（契约良好）

- **DataContract loaders：** 通过 `DataManager` 服务访问，不直接拼跨库 SQL；实现域路由后多数**无需改 loader**。
- **同域 JOIN：** kline/list/tag 服务现有 SQL 可保留，仅确保 `execute_sync_query` 使用**该域**连接（已 ATTACH 其它库时可用限定名）。

---

## 8. 建议实现顺序

1. schema 增加 `storage_domain` + 域内 cache 表设计；文档与校验脚本（lint 未填 domain）。
2. `infra/db`：DuckDB adapter + 域注册 + 每域写管道。
3. `DbBaseModel` / `get_table` 路由；`create_all_tables` 分域。
4. 分散 cache；改 `calendar` / `data_source` / `DbCacheService`。
5. `ATTACH` 与跨域读（workbench → stock_list）。
6. 迁移工具：MySQL → 三 duckdb；回归 renew + workbench + enumerator。

---

## 9. 决策者模式与存储域（定案）

ROADMAP 核心功能：用户沿交易日手动推进，查看每日机会池、自行分配仓位，累积盈利/回撤曲线。与自动 `capital_allocation` 同属策略模拟最后一环，但为 **人在回路** 的长会话。

| 问题 | 定案 |
|------|------|
| 是否新建 `decision` domain？ | **否**，归入 **strategy** |
| 行情与机会从哪读？ | **data**（K 线、日历）；机会池来自 **enum 结果**（磁盘或 workbench 元数据），一般不写入 data 域 |
| DB 存什么？ | 会话、游标、每日决策、曲线点（可查询、可恢复） |
| 盘存什么？ | 大快照、决策者 report（对齐现有「DB 索引 + 磁盘正文」） |
| 与 UI 域关系 | 无独立 UI 域；非界面配置，是 strategy 运行时状态 |

不新增第四种 duckdb 文件；`TableDomainRegistry` 与三域枚举保持不变。

---

## 10. 相关文档

- [Database 架构](./ARCHITECTURE.md)
- [Database 决策](./DECISIONS.md) — 决策 6
- [Data Manager 架构](../../modules/data_manager/docs/ARCHITECTURE.md)
- [ROADMAP 0.5.x 决策者模式](../../../../ROADMAP.md)
