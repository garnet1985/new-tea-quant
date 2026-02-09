# Tables 设计对齐记录

本文档记录 data_manager / data_source 共用表定义、表名与前缀、发现与合并、行业表等已对齐的设计，便于后续实现与讨论 entity。

---

## 1. data_manager 与 tables 的关系

- **原状**：表定义（schema + model）内置在 data_manager（base_tables）里。
- **目标**：表定义抽到**公共位置**（core/tables + userspace/tables），data_source 与 data_manager **共用同一套 DB 定义**，data_source 不依赖 data_manager。
- **data_manager 职责**：不变，仍是「连 DB、按表做 CRUD」的 driver；表从公共 tables 发现/注册，不再内置。**清洗数据**（如出库时 NULL → 默认值）属于 data_manager 的读路径职责（见 7.7）。

---

## 2. 表名与前缀（方案 B：表名即全名）

- **方案 B**：表名就是**全名**（含前缀），不做「逻辑名 + 前缀」分离。
  - 例：schema 里 `name = "sys_stock_list"`，建表、get_table、data source 的 table_name 都用同一字符串。
  - **约定**：core 里定义的表统一 **sys_** 前缀；userspace 里定义的表统一 **cust_** 前缀。校验时只检查前缀是否合法。
- **前缀规则**：
  - **core 表**：统一 **sys_** 前缀（如 sys_stock_list、sys_cpi、sys_cache、sys_tag_scenario）。不带 sys_ 的不识别。
  - **用户表（userspace）**：统一 **cust_** 前缀；若使用 sys_，报错拒绝。
  - 目的：区分系统表与用户自定义表，避免重名。

---

## 3. 表名语法（复数/单数）

- 按业界/英语习惯：存多行实体的表用**复数**（如 data_stock_lists、data_stock_klines_daily）；单条/配置类可用单数。
- 具体命名由实现时按此规则统一即可。

---

## 4. 表结构变更（已对齐）

| 变更项 | 说明 |
|--------|------|
| **K 线按 term 拆分** | 三张表：data_stock_klines_daily、data_stock_klines_weekly、data_stock_klines_monthly（仅价格/成交量，无 term 列）。 |
| **K 线与 daily_basic 分离** | daily_basic 数据单独成表（如 data_stock_indicators），renew 方式：K 线 incremental，指标 rolling。 |
| **price_indexes 分表** | 每个 API 一张表：data_cpi、data_ppi、data_pmi、data_money_supply（具体单复数按 3 统一）。 |
| **行业衍生表** | 两张表：**data_industries**（id, value, is_alive）+ **data_stock_industries**（stock_id, industry_id）做「行业–股票」映射；stock 表不再保留 industry 列。 |

---

## 5. 行业表与衍生时机

- **industry 定义表**：data_industries，字段 id、value（行业名）、is_alive。
- **映射表**：data_stock_industries，字段 stock_id、industry_id。
- **填充时机**：在 **stock list 的 data source 做 renew 时** 完成——从 Tushare stock list 返回的 industry 信息做 group，得到 industry 列表与 stock–industry 映射，写入上述两张表。建表先做；具体写入逻辑在实现 stock list handler / pipeline 时接好即可。

---

## 6. 表定义来源与发现、合并

- **来源**：两处——**core/tables** 与 **userspace/tables**（或后续递归 userspace 下目录）。
- **发现**：扫描两处目录，每张表一个子目录，内含 schema（Python，变量名 `schema`）+ model。
- **合并准则**：
  - core 里的表**必须**带 **sys_** 前缀，不带的不识别。
  - 用户表**必须**带 **cust_** 前缀，不能带 sys_，带了则报错拒绝。
  - 这样 core 与 userspace 不会产生重名表。

---

## 7. NULL 与 NaN 支持策略（三库一致）

项目支持三种数据库：**PostgreSQL、MySQL、SQLite**。对 NULL 与 NaN 的约定如下，三库行为一致。

### 7.0 required 与 nullable 分离（与业界一致）

**业界做法**（JSON Schema、OpenAPI 等）：

- **required**：该**属性必须存在**（key 必须出现在对象里）。约束的是「有没有这个 key」，不是「值能不能是 null」。若 key 缺失 → 校验不通过、拒绝该条。
- **nullable**：该**值是否可以为 null**。约束的是「值能否为 null」，决定存储/列是否允许 NULL。与 required 独立。

组合含义示例：

| required | nullable | 含义 |
|----------|----------|------|
| true | false | 源必须提供该属性，且值不能为 null；列 NOT NULL。 |
| true | true | 源必须提供该属性，值可以为 null；列允许 NULL。 |
| false | true | 源可不提供该属性，值可为 null；列允许 NULL。 |
| false | false | 源可不提供；若提供且值为 null 则需占位或拒绝；列 NOT NULL（常配合 default）。 |

**本项目的约定**：

- **isRequired**（required）：**数据源必须提供该属性**。若第三方返回的数据里**没有这个 key**（属性缺失），则拒绝该行。不决定 DB 列是否允许 NULL。
- **isNullable**（nullable）：**该列是否接受 NULL**。决定建表时列是 `NOT NULL` 还是允许 NULL；入库时若值为 null/None/NaN，仅当 isNullable=true 时才能存 NULL，否则用占位或 default。

实现上：schema 字段应支持两个独立属性，例如 `isRequired`、`isNullable`（或 `nullable`）。建表时 NOT NULL 由 **isNullable** 决定；入库前校验「属性是否存在」由 **isRequired** 决定。当前代码若把两者都压在 `isRequired` 上，需拆分为两处逻辑。

### 7.1 NULL

- **建表**：由 schema 的 **isNullable**（或 nullable）控制，与 isRequired 分离。
  - `isNullable: false`（或未写时按表约定）→ 列定义为 `NOT NULL`。
  - `isNullable: true` → 列**允许 NULL**。
- **结论**：三库都支持 NULL；是否允许 NULL 由字段的 **isNullable** 决定，不由 isRequired 决定。

### 7.2 NaN

- **写入**：当前实现**不**在库中存储 IEEE 754 的 NaN，而是把 NaN 视为“缺失”：
  - 批量写入（`BatchOperation.format_value_for_sql`）：`float('nan')` 被格式化为 SQL 的 `NULL` 写入。
  - 工具方法（`DBHelper.clean_nan_value` / `clean_nan_in_dict` / `clean_nan_in_list`）：NaN 转为 `None`（或调用方指定的默认值），供入库前清洗。
- **读取**：从库中读到的是 NULL，驱动会返回 Python 的 `None`，不会自动变成 NaN。
- **结论**：语义上“支持 NaN”= 把 NaN 转成 NULL 再存，三库一致；物理上不在任一库中存 NaN，避免 MySQL 等对 NaN 行为不一致的问题。

### 7.3 设计取舍

- 若未来需要在库中**原生存 NaN**：PostgreSQL DOUBLE PRECISION、SQLite REAL 支持；MySQL 的 DOUBLE/FLOAT 因版本/模式不同行为不一，需单独测试。当前未走“原生存 NaN”的路径。
- 需要“缺失”语义时：在 schema 中对该字段设 **isNullable: true**，写入时用 `None` 或先对 NaN 做 `clean_nan_*` 再写入即可。

### 7.4 存储事实：入库时清洗，读取时按需清洗

**约定**：库中“缺失”只存一种形式——**NULL**。None、NaN、pandas.NA 等在上层都视为缺失，落库时统一为 NULL。

- **入库时清洗（必须）**  
  写入前把缺失统一成“要写 NULL”：Python 的 `None`、`float('nan')`、pandas 的 NA 等，在拼 SQL / 绑参数时一律变成 SQL 的 NULL。  
  - 这样库里**事实唯一**：缺失 = NULL，不会出现 NaN 或多种表示，三库一致。  
  - 实现上：批量写入已由 `BatchOperation.format_value_for_sql` 把 NaN 转成 NULL；若在别处写库（如单条 insert），应在写入前用 `DBHelper.clean_nan_value` / `clean_nan_in_dict` 等做一次清洗，再写库。

- **读取时清洗（按需）**  
  读出的 NULL 由驱动变成 Python 的 `None`。是否再“清洗”取决于下游：  
  - 若下游要 `None` 表示缺失：直接使用即可，无需再处理。  
  - 若下游要 `NaN`（如 pandas、numpy）：在读取后对指定列做一次 `None` → `NaN` 的转换即可，在业务层或薄封装里做，不入库层约定。

**结论**：遵守“库里只存 NULL”的事实，**在入库时清洗**（None/NaN/NA → NULL）；读取时只做**按需**的表示转换（如 None→NaN），不做强制统一。

### 7.5 第三方数据：属性缺失 vs 值为 null

数据来自第三方时，要区分两种情况：

1. **属性缺失**：源里**没有这个 key**（字段不存在）。
2. **值为 null**：源里**有 key**，但 value 为 null/空/NaN。

**isRequired** 管的是 (1)：若 `isRequired: true` 且源**没给该属性**（key 缺失）→ **拒绝该行**（主键/唯一键缺失无法用占位替代；其他 required 字段若也缺失，同上）。  
**isNullable** 管的是 (2)：若源**给了该属性但值为 null**，则仅当 `isNullable: true` 时存 NULL；若 `isNullable: false` 则不能存 NULL，用占位/default 写入。

**约定：时序 renew 下不因“值为 null”就拒绝该行。**

- 我们是**时序、incremental renew**：若因**值为 null**就拒绝整行，该日/该实体的记录会丢，长期缺数。因此**值为 null 时不拒绝该行**，按 isNullable 存 NULL 或占位。
- **属性缺失**（key 不存在）：若 isRequired=true，则**拒绝该行**（符合“必须字段、缺失就拒绝”的语义）；主键/唯一键缺失必拒绝。

**具体做法**：

| 情况 | 处理 |
|------|------|
| 源没给该属性（key 缺失）+ isRequired=true | **拒绝该行**（缺失就拒绝）。 |
| 源给了该属性、值为 null/NaN + isNullable=true | 存 **NULL**。 |
| 源给了该属性、值为 null/NaN + isNullable=false | 用 **default / missing_value_sentinel** 写入，不拒绝该行。 |

- 数值/字符串的占位建议：在 schema 或配置里声明 **default** 或 **missing_value_sentinel**（如 0、-999、`''`、`'__MISSING__'`），下游按约定解读。
- 若希望某字段“值为 null 时存 NULL”，则设 **isNullable: true**，无需占位符。

### 7.6 清洗时如何转化 Null、库里存什么？

**原则**：库中“缺失”只存 **NULL**（见 7.4）；列是否允许 NULL 由 **isNullable** 决定（见 7.0、7.1）。属性是否必须存在由 **isRequired** 决定，缺失则拒绝该行（见 7.5）。

**按列是否可空（isNullable）**：

| 列约束 | 源给了该属性、值为 None/NaN | 写入 DB 的值 |
|--------|-----------------------------|--------------|
| **可空**（`isNullable: true`） | 视为缺失 | 存 **NULL**。 |
| **不可空**（`isNullable: false`） | 视为缺失 | **不能**存 NULL：用 **default / missing_value_sentinel** 写入，库里存该非 NULL 值。 |

**转化流程（入库前）**：

1. **校验存在性**：若某字段 `isRequired: true` 且源**没给该 key** → **拒绝该行**，不写入。  
2. **统一缺失值**：源给了 key 但值为 None/NaN/空 → 在内存里统一成 `None`。  
3. **按 isNullable 写库**：  
   - isNullable=true：拼 SQL 时写成 NULL → **库里存 NULL**。  
   - isNullable=false：用 schema/配置里的 default 或 missing_value_sentinel 写入 → **库里存该占位值**。

**总结**：  
- “转化 Null”在入库前完成：**isRequired** 管“有没有 key”（缺则拒绝）；**isNullable** 管“值为 null 时存 NULL 还是占位”。  
- **库里只存两种**：NULL（isNullable 且值为 null）或具体值（含占位符）。

### 7.7 NULL 存库 vs 入库前转默认值：业界与建议

**两种做法**：

| | 入库就存 NULL，出库再转默认值 | 入库前把 NULL 转成默认值再存 |
|--|------------------------------|------------------------------|
| 数据完整性（读时） | 需下游处理 null，多一步 coalesce/清洗 | 读出来即“完整”，少一步清洗 |
| IO/CPU | 读路径多做 coalesce，读多时成本增加 | 写时做一次，读时少处理 |
| 补数/排查缺失 | **直观**：`WHERE col IS NULL` 即缺数，补救明确 | **不直观**：已是默认值，只能靠业务逻辑猜哪里缺 |
| 数据真实性 | **清晰**：NULL = 缺失，0/'' 等 = 真实值 | **模糊**：默认值无法区分“真缺”还是“真是这个值” |

**业界常见做法**：

- **数仓 / 事实表度量**：多保留 **NULL**（Kimball 等），聚合函数按 NULL 处理不扭曲结果；用 0 替代会扭曲 SUM/AVG。缺失一目了然，便于补数和审计。
- **维度属性**：有时用“Unknown”“Not Applicable”等**有语义的默认值**替代 NULL，便于分组、过滤一致（不同库对 NULL 的 group/where 行为不一）。本质是“有语义的占位”，不是任意 0/''。
- **原则**：**能存 NULL 的列，优先存 NULL**；只在“必须非空列”或“展示/分组需要统一占位”时，在 ETL 里选**有语义的默认值**并文档化。

**本项目建议**：**可空列存 NULL，出库时再按需转默认值。**

- **理由**：我们是时序、incremental renew，**补数需求强**：存 NULL 则 `WHERE col IS NULL` 直接定位缺失，补完再跑即可；若入库就写成默认值，缺数位置难以精确定位，只能靠时间范围/业务规则猜。
- **代价**：读路径多一次 coalesce 或下游清洗；可通过“读时统一做一次默认值填充”（如 SQL `COALESCE(col, default)` 或 reader 层薄封装）收敛到一处，IO/CPU 可接受且可优化。
- **例外**：列设为 **isNullable: false** 时，入库就必须写占位/default（见 7.5、7.6），此时库里无 NULL；这类列本身就不表达“缺失”，补数需靠主键/时间范围等推断。

**结论**：**入库存 NULL（可空列），出库再按需转默认值**；优先保证“缺失可查、补数直观”，读路径成本在可控范围内。

**约定：清洗属于 data manager 职责，采用出库时清洗。**

- **清洗数据**：属于 **data_manager** 的职责（读路径上做 coalesce/默认值填充等）。
- **模式**：采用 **出库时清洗**（可空列存 NULL，读时再按需转默认值），不再在入库前把 NULL 转成默认值。
- **当前需做的改动**：目前多为入库前清洗；需改为在 **data manager 读路径**（如 get_table().load、或统一 reader 层）做 NULL → 默认值/清洗，入库前只做「缺失统一为 NULL」与 isRequired/isNullable 校验，不写入默认值占位。

---

## 8. Table schema 与 data source 额外配置（date_format 等）

**问题**：data source 除 table schema 的字段外，还需要额外信息（如 **date_format**、time_zone、field_mapping 等）。是给 data source 单独再立一份配置，还是写在 table schema 里？

**约定：table schema 只做 DB 列定义；data source 专用信息放在 data source 配置。**

- **Table schema**（core/tables/xxx/schema.py）：只描述 **DB 列**——name, type, isRequired, isNullable, default, length, comment 等。供 data_manager（建表、校验、读写）与 data_source（知道目标表结构）共用，**不混入采集侧语义**。
- **Data source 配置**（现有 config / 专门配置）：放 **采集侧** 独有信息，例如：
  - **date_format**：API 返回的日期格式（如 `%Y-%m-%d`、`%Y%m%d`），用于解析与标准化；
  - time_zone、field_mapping（API 字段 → schema 字段）、apis、renew_mode、table_name 等。
- **理由**：同一张表可能被不同数据源写入（不同 API、不同日期格式）；「日期格式」是**数据源/API 的约定**，不是表结构本身。若写进 table schema，会混淆「存什么」与「从哪来、怎么解析」，且 data_manager 建表、清洗时用不到 date_format。业界常见做法也是：**schema = 结构与类型**，**connector/config = 来源与解析方式**（如 OpenAPI schema vs 各 client 的 serialization format）。
- **实现**：沿用或扩展现有 **DataSourceConfig**（或 per-handler 的 config），在其中声明 date_format、time_zone 等；table schema 保持仅 DB 列定义，不新增 date_format 等字段。

---

## 9. 下一步可讨论内容

- **entity** 与 tables 的配合：谁引用谁、是否用 entity 作为「表名/主键/唯一键」的唯一定义等。
- 实现顺序：先完成 core/tables 新表名与 schema/model 迁移，再接 data_manager 发现与 data source 的 table_name 使用，最后接 userspace/tables 发现与合并。

---

## 10. 改动评估：合理性、复杂度与效率、性价比

本节评估「tables 抽离 + 表结构/命名调整 + entity/时序/矩阵」这一套改动的合理性、是否降低复杂度与提升效率，以及性价比。改动面不小，需心里有数再推进。

### 10.1 合理性

- **表定义公共化**：data source 与 data manager 共用一套 DB 定义（core/tables + userspace/tables），避免「采集侧」和「存储侧」各说各话，是常见做法，合理。
- **表名与前缀**：表名即全名（含 data_/sys_/cache_/cust_），系统表与用户表边界清晰，命名冲突可防，合理。
- **K 线按 term 拆表、daily_basic 独立、price_indexes 分表**：与「一 data source 一表、renew 方式按表区分」一致，已在 per-table 文档里论证过能降 handler 复杂度，合理。
- **行业两表（industries + stock_industries）**：维度表 + 映射表，stock 表不再冗余 industry 列，合理。
- **Entity = 固定结构、时序 = per record group、矩阵仅内存**：不改变表结构，只统一「类型/形状」和 simulator 的加载形态，合理。

结论：**方向合理**，没有明显「为改而改」；和「per-table、schema=表、data source 不依赖 data manager」等既定目标一致。

### 10.2 是否降低复杂度、提高效率

**会降低复杂度的部分**

| 项目 | 说明 |
|------|------|
| 表/schema 单一来源 | 表结构只在 core/tables（及 userspace/tables）定义一次，data source 与 data manager 都从这里取；减少两处定义不一致带来的心智和 bug。 |
| K 线 / 指标 / price_indexes 分表 | Handler 不再做「多 API 合并进一张宽表」；每个 data source 单表、单 schema，renew 按表配置（incremental / rolling），逻辑更简单。 |
| 前缀与发现规则 | 系统表必须带前缀、用户表只能用 cust_，发现与合并规则明确，重名和误用系统表的问题可从命名层面避免。 |
| Entity 作为类型契约 | 一种 entity = 一张表 = 一个 schema；校验、清洗、入库都「跟表走」，边界清晰，后续扩展新表/新类型时更一致。 |

**会提高效率的部分**

| 项目 | 说明 |
|------|------|
| Simulator 内存与序列化 | 从 list of dicts 改为 headers + records 矩阵，减少重复 key 和对象开销，降低内存占用和序列化成本。 |
| 列式/矩阵仅内存 | 不要求改 DB 存储格式，只在加载给 simulator 时做一次「行 → 矩阵」转换，收益集中、实现面可控。 |

**可能增加复杂度的部分**

| 项目 | 说明 |
|------|------|
| 发现与合并 | 需实现「扫描 core/tables + userspace/tables、校验前缀、合并注册」；逻辑清晰但多一层，需测试充分。 |
| 迁移 | 表重命名、data_manager 发现源从 base_tables 改为 tables、各调用点改用新表名；**无需兼容**，可直接破坏性改动（当前无用户），成本为一次性迁移与回归。 |
| Entity 层 | Entity 提供类型契约与可选工具（见 10.4）；不要求「所有数据都先变 entity 再落库」，复杂度可控。 |

**综合**：在**分阶段**实施的前提下，整体上会**降低系统复杂度**（单一表定义、分表减 handler 逻辑、规则清晰），并在 **simulator 路径上提高效率**（矩阵形态）。

### 10.4 Entity 的定位与用法（对齐）

- **可脱离 entity 处理数据**：写入/读取可以始终以「表 + schema」为主，不强制经过 entity。
- **Entity 提供可选工具**：校验、时间格式处理、数据加工等，可以是 **静态方法**，无需实例化即可使用。这些能力也可以放在**独立 module**，完全不依赖 entity，按需二选一即可。
- **在 data source 里用 entity 的原因**：主要是**时间格式等声明与处理方便**（在「数据变成实体」前需要声明时间格式等条件，且这些不只 data source 用）。用 entity 是图方便，**不用也行**。
- **不做「必须经 entity 才落库/加载」**：不要求所有数据都先包成 entity 再写库或再读；entity 是类型契约 + 可选工具（含静态方法），用不用、用多少由各模块自选。

### 10.3 性价比与实施建议

**收益（中长期）**

- 单一事实来源、少漂移、易维护、易扩展。
- Handler 与 data source 更简单（分表、无宽表合并）。
- Simulator 内存与序列化更省。
- 系统表/用户表边界清晰，利于多租户或插件式用户表。

**成本（一次性为主）**

- 表重命名与数据迁移；所有引用表名处（get_table、config、SQL 等）改为新名。
- 发现/合并实现与测试；data_manager（及必要时 data_source）接入新发现逻辑。
- Entity 层实现（类型 + schema 绑定 + 可选静态工具 + to_matrix）；simulator 改为消费矩阵。

**兼容性**：**不考虑兼容**，可直接做破坏性改动；当前软件无外部用户。

**性价比结论**

- **分阶段做**：性价比**高**。先做「tables 抽离 + 新表名 + 发现」，再做 entity 与 simulator 矩阵，每步可独立验证。
- **一步到位全做**：收益在，无兼容包袱，可按需选择一步或分阶段。
- **Entity**：作为类型契约 + 可选工具（静态校验、时间格式、加工等）；不要求「所有数据都经 entity 才落库/加载」，data source 用 entity 图的是时间格式等便利，不用也行；工具也可放在独立 module，与 entity 解耦。

**建议实施顺序**

1. **Phase 1**：core/tables（及约定好的 userspace/tables）落地；新表名与前缀；data_manager 改为从 tables 发现并注册；表结构变更（K 线拆表、indicators、price_indexes 分表、行业两表）与数据迁移。
2. **Phase 2**：data source 的 table_name 与 config 全部切到新表名；必要时做 userspace 发现与合并。
3. **Phase 3**：Entity/TimeSeriesEntity（类型契约 + 可选静态工具 + to_matrix）；simulator 改为 headers + records；data source 可按需使用 entity 做时间格式等声明与处理，非强制。

---

*记录时间：按当前对话对齐。后续若有变更可在此文档增补或另开章节。*
