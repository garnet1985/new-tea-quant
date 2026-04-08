# Data Contract - 临时设计文档（MVP）

> 目标：在 MVP 前提下，把系统中“必须统一/必须 fail-fast”的数据与依赖，收敛到一套可签发（issue）的 contract 体系。  
> 约束：不引入单独 settings 文件；contract 的必要信息在 `issue(...)` 时显式传入，并在 contract 生命周期内持有。

---

## 1. 核心定义（MVP）

### 1.1 Contract 是什么

Contract 是一套**可执行规则**，把输入的 raw（数据或声明）签发为 contracted（满足约定的输出），否则抛错（fail-closed）。

- **Raw**：来源不重要（DB/API/文件/手工导入都行）
- **Contracted**：结构/字段/时间轴等满足约定，可被 strategy/tag/simulator 等模块消费

### 1.2 Spec 与 Data：不是两种 Contract，而是两个入口/阶段

同一个 contract 一般既需要：

- **Spec（声明）能力**：它需要哪些必要输入、有哪些不可变规则（例如 time_axis 字段、scope 等）
- **Data（数据）能力**：拿到 raw rows 后如何校验/规范化/签发

因此这里的 Spec/Data 是 **contract 的两个入口/阶段**，不是“二选一类型”。

> MVP 优先从“签发依赖（Spec）”切入，最能立刻解决“缺依赖还跑完”的问题。

---

## 2. BaseContract（MVP 基类字段）

> MVP 先不引入 `required/strict`（默认为强约束：fail-closed）。未来确有可选数据源/兼容旧数据需求，再扩展。

建议基类字段（最小集合）：

- **`contract_id`**：机器唯一标识（例如 `strategy.tag_scenario`）
- **`name`**：机器名（稳定，可用于代码内引用）
- **`display_name`**：显示名（面向人，可变）
- **`scope`**：数据分片/作用域
  - `global`：不按 entity_id 分片（如宏观/日历）
  - `per_entity`：按 stock_id 等 entity_id 分片（如 K 线、tag value）
  - `per_category`：按行业/板块等分片（预留）
- **`context`**：dict（用于错误信息、缓存 key、诊断；不参与业务规则）

---

## 3. 子 Contract 类型（MVP：三大类）

MVP 只保留 **3 类 contract**，避免过度设计；后续新增 contract 时，优先归入这三类之一。

> 注意：Spec/Data 不是 contract 类型，而是同一个 contract 的两个入口/阶段（见 1.2）。

### 3.1 `PerEntityTimeAxisContract`（每个实体一份时序）

**定义**
- 固化为 `scope="per_entity"`
- 具备 time axis（时间流逝），可按 `t` 做 point / lookback(as-of) 消费

**典型 raw 输入**
- `entity_id`（如 `stock_id`，可放在 `context` 或作为 issue 入参）
- `rows: List[Dict[str, Any]]`

**私有字段（由具体子类固化，不让外部随意传入修改）**
- `time_axis_field`（例如 K 线是 `date`；tag eventlog 是 `as_of_date`；财务是 `report_date`）
- `time_axis_format`（MVP 建议统一 normalize 到 `YYYYMMDD`）
- `required_fields`（最小字段集合，由子类决定）
- `dedupe_keys`（由子类决定）

**挂载实例（MVP 会用到的具体 contract）**
- `KlineDailyContract`：`time_axis_field="date"`，required_fields 至少 OHLC
- `TagEventLogContract`：`time_axis_field="as_of_date"`，用于 tag_value（只记录变化）
- `FinanceSnapshotContract`：`time_axis_field="report_date"`（MVP 可延后实现）

---

### 3.2 `GlobalTimeAxisContract`（全局一份时序）

**定义**
- 固化为 `scope="global"`
- 具备 time axis，不依赖 entity_id

**典型 raw 输入**
- `rows: List[Dict[str, Any]]`

**私有字段（由具体子类固化）**
- `time_axis_field`（`date` / `quarter`）
- `time_axis_format`
- `required_fields`

**挂载实例（MVP 可延后实现）**
- `GDPContract`
- `LPRContract`
- `TradingCalendarContract`

---

### 3.3 `StaticCategoryContract`（静态分类/属性）

**定义**
- 以“分类/属性”为主，默认不依赖 time axis（或 time axis 显式禁用）
- 用于静态映射、固定权重、固定分类等

**说明**
- 如果某类“分类”会随时间变化（行业变更/成分股变更），应当回归到 `PerEntityTimeAxisContract`（eventlog/snapshot 形态），而不是放在 StaticCategoryContract 中。

**典型 raw 输入**
- `rows: List[Dict[str, Any]]` 或 `mapping: Dict[str, Any]`

**私有字段（由具体子类固化）**
- `key_field`（如 `stock_id` / `category_id`）
- `value_fields`（如 `industry` / `weight`）

**挂载实例（按需求添加）**
- `StockIndustryContract`（若 MVP 需要）

---

## 4. 是否需要再抽象一层基类？

### 4.1 MVP 建议：先平铺，后抽象

先把 `PerEntityTimeAxisContract` 线上的关键实例（如 KlineDaily、TagEventLog）做出来并接入实际调用链后，再抽象公共部分。原因：
- 没有真实调用点时容易过度抽象
- `required/strict`、normalize 细节要靠真实数据校准

### 4.2 未来可抽象的两层（供后续迭代）

- **`TimeAxisContract`（中间基类）**
  - 适用：PerEntityTimeAxisContract / GlobalTimeAxisContract 的共用逻辑
  - 提供：time_axis_field、normalize_time、clip_range、sort、dedupe

- **`RowSchemaContract`（中间基类）**
  - 提供：required_fields 校验、field_map、type coercion（如 float/bool）

---

## 5. 集成点（MVP）

### 5.1 preprocess（签发 spec）
- 从 Strategy settings 中提取 `tag_scenario` 依赖，调用 `TagScenarioContract.issue(...)`
- 失败：直接中断（替代“子进程刷 warning + 0 结果”）

### 5.2 取数后、注入前（签发 data）
- raw rows（kline / tags） -> issue 对应 data contract -> contracted rows
- 下游（strategy worker）只消费 contracted data

---

## 6. 设计原则（MVP）

- **Fail-closed**：任何不满足契约的输入都应明确失败（MVP 默认强约束）
- **显式输入**：contract 必要信息由 `issue(...)` 显式传入，不依赖隐式全局配置
- **弱依赖 IO**：尽量通过 callable 注入“存在性查询”，避免 contract 直接绑死 DataManager
- **先解决真实痛点**：优先 contract 化 tag scenario 依赖与 time axis 相关问题

---

## 7. Tag 的多态（由元信息声明）

Tag 是一个特殊但常见的“多态数据”：

- 它可能是 **时序**（随时间变化）：例如 eventlog（只记录变化）、snapshot（不连续但可 as-of）
- 它也可能是 **分类/属性**（弱时间或无时间）：例如静态分类、固定权重等

### 7.1 决策：由 Tag 作者在元信息中声明类型

为避免让 strategy/调用方承担额外学习成本，也避免外部传错类型导致语义偏移：

- **Tag 类型由创建 tag 的人（scenario/definition）在元信息中声明**
- Strategy 侧只引用 `scenario_name/tag_name`，不声明 tag_kind

建议在 `sys_tag_scenario` 或 `sys_tag_definition` 中持久化以下元信息（MVP 可先内存/配置，后续入库）：

- `tag_kind`: `eventlog | snapshot | category | timeseries`
- `time_axis_field`: 默认 `as_of_date`（仅对时序类 tag 有意义）

### 7.2 Contract 侧处理：固定小集合分发（不会随 tag 数量膨胀）

`TagContract`（或 Tag 相关 contract）在 issue 时读取元信息，按 `tag_kind` 选择固定的处理分支：

- `eventlog` -> `TagValueEventLogContract`（per_entity + as_of_date）
- `snapshot` -> 仍走 per_entity time-axis，但消费方式偏 `as_of(t)`（最近一期）
- `category` -> `CategoryContract`（static 或弱时间）
- `timeseries` -> per_entity time-axis（每天都有值的序列）

> 这里的分发分支数是固定的小集合（数据形态），不会变成“每加一个 tag 就加一个 case”。

---

## 8. `core/tables/` 表归类映射（按三大 Contract 类型）

> 目的：让 contract 设计与现有系统表结构强绑定，避免实现阶段再争论归类。

| 表名（table） | 主键/关键字段（简写） | 推荐 Contract 类型 | time_axis | 备注 |
| --- | --- | --- | --- | --- |
| `sys_stock_klines` | `(id, term, date)` | `PerEntityTimeAxisContract` | `date` | K 线时序；`term` 为附加维度 |
| `sys_adj_factor_events` | `(id, event_date)` | `PerEntityTimeAxisContract` | `event_date` | 复权事件（eventlog） |
| `sys_tag_value` | `(entity_id, tag_definition_id, as_of_date)` | `PerEntityTimeAxisContract` | `as_of_date` | Tag 值（通常 eventlog/snapshot）；tag_kind 由元信息声明 |
| `sys_corporate_finance` | `(id, quarter)` | `PerEntityTimeAxisContract` | `quarter` | 低频时序（snapshot）；quarter 形如 `YYYYQn` |
| `sys_stock_index_klines` | `(id, term?, date)` | `PerEntityTimeAxisContract` | `date` | 指数行情（按指数 id 分片） |
| `sys_index_weight` | `(id, date, stock_id)` | `PerEntityTimeAxisContract` | `date` | **权重/成分随时间变化**，不要误归为静态分类 |
| `sys_gdp` | `(quarter)` | `GlobalTimeAxisContract` | `quarter` | 全局宏观时序 |
| `sys_lpr` | `(date)` | `GlobalTimeAxisContract` | `date` | 全局利率时序 |
| `sys_cpi` / `sys_ppi` / `sys_pmi` / `sys_shibor` / `sys_money_supply` | `(date/quarter)` | `GlobalTimeAxisContract` | `date/quarter` | 宏观全家桶（同一类） |
| `sys_stock_list` | `(id)` | `StaticCategoryContract` | - | 股票静态属性（name/is_active/last_update） |
| `sys_industries` / `sys_boards` / `sys_markets` | `(id)` | `StaticCategoryContract` | - | 分类字典（全局静态） |
| `sys_stock_industry_map` / `sys_stock_board_map` / `sys_stock_market_map` | `(stock_id, category_id)` | `StaticCategoryContract` | - | 映射表（若未来引入生效日期，应迁移为时序 eventlog/snapshot） |
| `sys_tag_scenario` / `sys_tag_definition` | `(id)` | `StaticCategoryContract` | - | Tag 元信息（其中包含 tag_kind 等多态声明） |
| `sys_cache` / `meta_info` | `(key/...)` | `StaticCategoryContract` | - | 系统元信息/缓存；MVP 视为静态结构即可 |

