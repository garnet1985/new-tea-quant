# Entity Data Class 引入后的实体关系与协作

引入统一的 **Entity Data Class** 且采用 **data source ↔ table 一一对应** 后，实体之间会出现哪些关系、如何在 data source 与 entity 大类之间协作，以及还有哪些 use case 需要提前考虑。

---

## 1. 当前实体与依赖的形态（简要）

- **执行依赖**：Handler 的 `depends_on` 是 **data source 名称**（如 `["stock_list", "latest_trading_date"]`）。被依赖的 data source 先执行，其 **normalized 结果** 作为 `dependencies_data` 传给下游。
- **实体列表来源**：per-entity 的 Handler 通过 `result_group_by.list`（如 `"stock_list"`）从 `dependencies_data["stock_list"]` 取到 **实体实例列表**（当前就是「股票列表」），再按实体展开 Job、算日期范围。
- **现状**：`stock_list` 被 kline、corporate_finance、adj_factor_event 等多个 data source 依赖，是典型的 **被多处依赖的实体列表**；`latest_trading_date` 也被多处依赖，提供「最新交易日」这类全局信息。

引入 Entity Data Class 后，可以把「实体类型」（Stock、Industry、TradingDate 等）和「实体实例列表从哪里来」显式化，下面在保留现有执行依赖的前提下，讨论实体之间的关系和协作方式。

---

## 2. 实体之间会出现的关系

### 2.1 执行依赖（A 依赖 B 的输出才能跑）

- **含义**：Data source A 的 **执行** 依赖 B 的 **normalized 结果**（例如 A 需要「实体列表」来做 per-entity 展开）。
- **当前**：`stock_list`、`latest_trading_date` 作为 data source 先跑，结果放进 `dependencies_data`；kline 等从 `dependencies_data["stock_list"]` 取列表。
- **引入 Entity 后**：可以显式声明「A 依赖的实体类型 / 实体表」，例如：
  - 依赖 **实体类型**：`depends_on_entities: ["Stock"]` → 调度层解析为「需要先跑产出 Stock 表的数据源」，并把该表的当前实例列表注入 context；
  - 或继续用 **data source 名**：`depends_on: ["stock_list"]`，但约定 `stock_list` 对应 Entity 类型 `Stock`，产出表 `stock_list`。
- **关系特点**：**多对一**——多个 data source 依赖同一个实体数据源（如 stock_list），所以「stock list 被很多依赖」会长期存在，Entity 设计里应把「谁提供实体列表、谁消费实体列表」说清楚（见下节）。

### 2.2 派生实体（B 从 A 的数据推导出新实体/新表）

- **含义**：实体 B 的 **数据** 不是从外部 API 拉取，而是从已有实体 A 的表中 **推导、聚合、拆分** 得到，并可能产生 **新表**（如 A 的明细表 + B 的主表 + A–B 映射表）。
- **典型需求**：  
  「拿到 stock list，按行业中文名 group 一下，行业单独存成一张表，stock–industry 的映射存成另一张表。」
- **协作方式**：
  - **Entity 层**：定义两类实体及表结构——  
    - **Industry**：表 `industry`（如 `id`, `name_cn`, ...）；  
    - **Stock–Industry 映射**：表 `stock_industry`（如 `stock_id`, `industry_id`）。
  - **Data source 层**：  
    - 新增一个 **不调外部 API** 的 data source，例如 `industry_from_stock_list`（或拆成 `industry` + `stock_industry_mapping` 两个 data source，看是否要 per-table 一一对应）。  
    - 该 data source **依赖** `stock_list`：`depends_on: ["stock_list"]`。  
    - 执行时从 `dependencies_data["stock_list"]` 读当前股票列表，在 Handler 内：  
      - 按 `industry`（中文名）做 distinct → 写入 **industry 表**（如 id = 行业名或自增 id）；  
      - 生成 (stock_id, industry_id) → 写入 **stock_industry 表**。  
  - **Entity 与 Data Source 的分工**：  
    - **Entity 大类**：定义 Industry、Stock、以及「Stock–Industry 关系」的 schema/表结构、唯一键、是否允许空等；可提供「从 Stock 列表推导 Industry 列表 + 映射」的 **规范接口**（输入：Stock 列表，输出：Industry 列表 + 映射表行）。  
    - **Data source**：只负责「何时、何序」执行——先跑 stock_list，再跑 industry_from_stock_list；在 Handler 里调用 Entity 层的推导逻辑，然后按 **一 data source 一表** 或 **一 data source 多表** 的约定写库（若严格 per-table，可拆成两个 data source：一个只写 industry，一个只写 stock_industry）。
- **关系特点**：**A → B** 的派生；B 的实体实例集合由 A 推导而来，因此 B 的更新顺序必须在 A 之后，用现有的 `depends_on` 即可表达。

### 2.3 同一实体多源（同一张表/同一实体类型，多个 data source 写入）

- **含义**：同一类实体（如 Stock）可能由多个 data source 产出（例如 Tushare 的 stock_list、东财的 stock_list），需要 **合并、去重、冲突策略**。
- **协作方式**：  
  - Entity 层定义 **Stock** 的唯一定义（主键、业务键、合并规则）；  
  - 多个 data source 都声明「产出实体类型 = Stock」或「写入表 = stock_list」；  
  - 调度层可以：按优先级/数据源优先级合并，或约定「一个实体类型只由一个 data source 写入」，其余通过 **entity_id 关联** 只做扩展字段（另一张表）。  
- **关系特点**：多源 → 一实体类型（或一表）；需要在 Entity 层约定合并策略和冲突处理。

### 2.4 实体层级（如 Industry → Sector → Market）

- **含义**：实体之间有层级（行业 → 板块 → 市场），需要「父实体–子实体」或「分类树」。
- **协作方式**：  
  - Entity 层定义层级关系（如 Industry 有 `parent_id` 或 `sector_id`）；  
  - Data source 可以：  
    - 只负责叶子节点（如只写 Industry），父节点由另一个 data source 或派生逻辑填充；  
    - 或一个 data source 写整棵树，但表设计上仍可 per-entity 表（industry 表、sector 表、industry_sector 映射表等）。  
- **关系特点**：树状/层级；派生逻辑可能依赖「先有子再有父」或「先有父再有子」，顺序用 `depends_on` 表达。

---

## 3. 行业 + 股票–行业映射的完整协作示例

需求：**拿到 stock list（里边有行业中文名），按行业 group，行业单独存表，stock–industry 映射另存一张表。**

### 3.1 Entity 层（表结构 / 实体定义）

- **Stock**：已有表 `stock_list`，字段含 `id`, `name`, `industry`（中文）, ...
- **Industry**：新表 `industry`，例如 `id`（主键）, `name_cn`（唯一）, ...
- **Stock–Industry**：新表 `stock_industry`，例如 `stock_id`, `industry_id`，联合唯一。

### 3.2 Data source 层

- **stock_list**（已有）：依赖无或仅 `latest_trading_date`；产出表 `stock_list`；Entity 类型 **Stock**。
- **industry**（新）：  
  - `depends_on: ["stock_list"]`；  
  - 不调 API；  
  - 执行时从 `dependencies_data["stock_list"]` 取列表，在 Handler 内：  
    - 用 Entity 层提供的「从 Stock 列表推导 Industry 列表」得到 `List[Industry]`；  
    - 写入表 `industry`（若 per-table 严格，则此 data source 只写这一张表）。  
- **stock_industry_mapping**（新）：  
  - `depends_on: ["stock_list", "industry"]`（或只依赖 `industry`，若 industry 的 id 可由 name_cn 推导则也可只依赖 stock_list）；  
  - 不调 API；  
  - 从 `dependencies_data["stock_list"]` 和已写入的 `industry` 表（或 `dependencies_data["industry"]` 若调度层把刚跑完的 industry 结果也注入）生成映射行，写入表 `stock_industry`。

若希望 **一个 data source 同时写两张表**（industry + stock_industry），也可以：一个 Handler 内先写 industry，再写 stock_industry，但违反「一 data source 一表」时，需要在设计上明确允许「派生型 data source 写多表」的例外。

### 3.3 调度与 context

- 执行顺序：`stock_list` → `industry` → `stock_industry_mapping`（或 `industry` 与 `stock_industry_mapping` 合并为一个 data source，顺序则为 `stock_list` → `industry_and_mapping`）。
- Context / dependencies_data：  
  - 下游 Handler 通过 `dependencies_data["stock_list"]` 拿到当前股票列表；  
  - 若需要「当前已计算出的行业列表」，可约定 `dependencies_data["industry"]` 由调度层在 industry 跑完后注入（与现有「依赖 data source 的 normalized 结果」一致）。

这样，**data source 负责「何时、从哪拿数据、写哪张表」**，**Entity 层负责「表结构、唯一性、以及从 Stock 列表推导 Industry + 映射」的规范**，二者通过「实体类型 / 表名」和「dependencies_data」协作。

---

## 4. 其他值得考虑的 Entity 间 use case

| Use case | 简要说明 | 与 Data source / Entity 的协作 |
|----------|----------|--------------------------------|
| **依赖注入的实体列表可配置** | 除 `stock_list` 外，未来可能有 `industry_list`、`index_list` 等作为 per-entity 的遍历列表 | 用 `result_group_by.list` 或 `depends_on_entities` 指向提供该列表的 data source 名；Entity 层对「实体类型」命名统一（Stock / Industry / Index），便于扩展 |
| **软依赖 / 可选依赖** | 例如：有 stock_list 就按股遍历，没有就跳过或只跑全局 Job | 调度层允许 `depends_on` 中部分缺失时仍执行，Handler 内根据 `dependencies_data` 是否为空分支；Entity 层不强制「必须有某实体表存在」 |
| **同一实体多源合并** | 多数据源写同一实体类型（如 Stock），需要合并、去重、主从源策略 | Entity 层定义合并规则（主键、业务键、覆盖策略）；Data source 层标记「主源 / 补充源」，或写入不同的「扩展表」再在 Entity 层做视图/合并 |
| **实体层级 / 分类树** | 行业–板块–市场等层级 | Entity 层定义父子表或自关联；Data source 按依赖顺序写各层表，或一个派生 data source 写整棵树 |
| **跨实体校验** | 例如：写入 kline 前校验 stock_id 必须在 stock_list 中存在 | 可在 Entity 层提供「存在性校验」接口；Data source 在写入前调用，或由 DB 外键 + Entity 约束统一保证 |
| **按实体类型做增量/全量策略** | 不同实体类型有不同的 renew 策略（如 Stock 全量刷新，Kline 按股增量） | 已在现有 renew_mode 中按 data source 配置；Entity 层可对「实体类型」绑定默认策略，供 config 继承 |
| **实体版本 / 快照** | 例如：stock list as of 某日、历史行业映射 | Entity 层表结构支持 as_of_date 或版本号；Data source 写带版本的表，或由单独「快照」data source 按日/版本写入 |
| **派生仅依赖 DB 不依赖其他 data source** | 例如：每天收盘后从 kline 表聚合出「每日全市场统计」表 | 该 data source 不依赖其他 data source，但依赖「某表已存在」；可从 DB 读 kline，聚合后写新表；Entity 层定义该统计表为独立实体类型 |

---

## 5. 小结

- **执行依赖**：会长期存在「一个实体数据源被多个 data source 依赖」（如 stock_list）；引入 Entity 后，可显式区分「依赖的是哪个实体类型 / 哪张表」，便于扩展 `industry_list`、`index_list` 等。
- **派生实体**：像「从 stock list 按行业 group → industry 表 + stock_industry 映射表」这类需求，用 **依赖 stock_list 的、不调 API 的 data source** 即可；Entity 层负责表结构和「从 Stock 列表推导 Industry + 映射」的规范，Data source 层负责执行顺序与写入哪张表。
- **协作边界**：**Entity 大类** 管实体类型、表结构、唯一性、派生规则（如从 Stock 列表生成 Industry 列表）；**Data source** 管执行顺序（depends_on）、从哪里取输入（dependencies_data）、调用哪个 API 或哪个派生逻辑、写哪张表。二者通过「实体类型 / 表名」和「dependencies_data」协作，即可覆盖当前依赖、派生、多源、层级、校验、版本等 use case。

若你愿意，下一步可以针对「industry + stock_industry 这两个表」单独写一版 **Entity 表结构 + 一个派生 data source 的配置与 Handler 伪代码**，方便直接落地实现。
