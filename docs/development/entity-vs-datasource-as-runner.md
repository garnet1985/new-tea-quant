# 引入 Entity 后：Data Source 如何定义？Entity 做执行单元 vs Entity 只做数据类

两种定义方式：

- **方式 A**：`entity = Entity()` → `entity.renew()` / `entity.fetch()` …；Entity 是执行单元，拥有 renew/fetch 行为。
- **方式 B**：在 Data Source 中执行，Entity 只作为数据类（schema + 表身份），没有 renew/fetch 方法。

下面从执行模型、依赖、与现有架构的契合度做对比，并给出建议。

---

## 1. 两种方式的本质差异

| 维度 | 方式 A（Entity 做执行单元） | 方式 B（Data Source 执行，Entity 只做数据类） |
|------|-----------------------------|-----------------------------------------------|
| **谁在“跑”** | Entity：调度器按实体依赖顺序调用 `entity.renew()`。 | Data Source（Handler）：调度器按 data source 依赖顺序调用 `handler.execute()`。 |
| **Entity 的职责** | 定义“长什么样”（schema/表）+ **如何更新**（renew/fetch）；内部委托给某个“数据源实现”去拉数。 | 只定义“长什么样”和“对应哪张表”（schema + table_name + 唯一键等）；不包含 renew/fetch。 |
| **Data Source 的职责** | 成为 Entity 的“拉数策略”：被 Entity 调用，负责 API 调用 + normalize → 产出符合 Entity schema 的数据；写库可由 Entity 或 Data Source 完成。 | 仍是执行单元：Handler + config + schema（来自 Entity）；负责 fetch + normalize + 写库；消费/产出“Entity 形状”的数据。 |
| **依赖表达** | “Entity A 依赖 Entity B” → 调度器先跑 B.renew()，再跑 A.renew()，并把 B 的结果注入 A。 | “Data source A 依赖 Data source B” → 与现有一致；Entity 仅作为 A/B 产出数据的“类型/形状”。 |

---

## 2. 方式 A（Entity = 执行单元，有 renew/fetch）

**形态**：  
- `entity = StockEntity()`；调度器调用 `entity.renew(dependencies)`。  
- Entity 内部持有“如何拉数”的实现（例如当前 Handler 逻辑），或委托给一个 DataSource 适配器；renew 完成后写到自己对应的表。

**优点**  
- 领域语言统一：“实体”即可更新对象，`entity.renew()` 语义直观。  
- 依赖用实体表达：“Industry 依赖 Stock”即 Industry.renew() 依赖 Stock 的结果，和业务概念一致。

**缺点**  
- 需要新的执行模型：调度器从“按 data source 跑”改为“按 entity 跑”；当前 Handler/Config/Schema 要收拢到 Entity 下，或 Entity 包装现有 Handler。  
- Entity 既管“长什么样”又管“怎么更新”，职责变重；且“怎么更新”里大部分仍是“调 API + normalize + 写表”，和现有 Data Source 高度重叠。  
- 若 Entity.renew() 内部仍是“调用一个 Data Source 式的 pipeline”，则多了一层 Entity 门面，容易变成“Entity 委托 Data Source，调度器再调 Entity”的重复抽象。

---

## 3. 方式 B（Data Source 执行，Entity 只做数据类）

**形态**：  
- Entity = schema + table_name + 唯一键等；**没有** renew()/fetch()。  
- 调度器仍然按 **Data Source** 排序、执行：`handler.execute(dependencies_data)`；Handler 产出符合某个 Entity 的 schema 的数据，并写入该 Entity 对应的表。  
- 依赖仍在 mapping 层用 data source 名表达（如 `depends_on: ["stock_list"]`）；Entity 只作为“这张表/这类数据的契约”。

**优点**  
- **与现有架构一致**：执行单元仍是 Data Source（Handler）；只需把“schema + 表”抽成 Entity 数据类，Handler 绑定到某个 Entity（用其 schema 和 table_name），不改调度、依赖、缓存逻辑。  
- **职责清晰**：Entity = 数据契约（形状 + 表身份）；Data Source = 执行契约（何时跑、依赖谁、如何拉数、写到哪张表）。  
- **渐进引入**：可以先在少数表上引入 Entity 类，Handler 改为“使用 Entity.schema / Entity.table_name”；其余仍用现有 schema.py + config.table_name。  
- **与“schema = 表”统一**：已决定“data source 输出 schema = DB 表结构”；Entity 就是这份 schema 的命名 + 表绑定，不需要再拥有“如何拉数”的逻辑。

**缺点**  
- 领域语言上，“可更新的是 Data Source”而不是“Entity”；若希望对外说“更新 Stock 实体”，需要多一层薄门面（如 `renew_stock()` 内部调 stock_list 这个 data source），但实现简单。

---

## 4. 依赖与调度在两种方式下的表现

- **方式 A**：  
  - 依赖图是“Entity 依赖图”；调度器对 Entity 做拓扑排序，依次调用 `entity.renew(deps)`。  
  - 若 Entity.renew() 内部再调“某条 Data Source pipeline”，则等价于“每个 Entity 绑定一个 Data Source”；调度从“按 Data Source 排序”变成“按 Entity 排序”，本质仍是“谁先跑、谁后跑、谁把结果给谁”。

- **方式 B**：  
  - 依赖图保持“Data Source 依赖图”；调度器对 Handler 排序，`handler.execute(dependencies_data)`。  
  - Entity 不参与排序，只定义“结果长什么样、落到哪张表”；“Industry 依赖 Stock”体现为“industry 这个 data source 依赖 stock_list 这个 data source”，与当前实现一致。

两种方式在“执行顺序 + 依赖注入”上能力等价；方式 B 不需要新增“Entity 调度器”，复用现有 Data Source 调度即可。

---

## 5. 建议：**采用方式 B（Data Source 执行，Entity 只做数据类）**

**理由简述**  

1. **改动最小、落地最快**：不引入新的执行单元；Entity 只作为“表契约”的载体（schema + table_name + unique_keys 等），Handler 继续是唯一“跑”的单元，绑定到某个 Entity 即可。  
2. **职责单一**：Entity = 数据契约；Data Source = 执行与写库。避免 Entity 既管结构又管拉数、与 Data Source 职责重叠。  
3. **与“schema = 表”一致**：已选“data source 与 DB 共用一个 schema”；那“这份 schema + 表名”就是 Entity 的全部职责，不需要再拥有 renew/fetch。  
4. **依赖保持现有表达**：继续用 data source 名做 depends_on；若将来要做“按实体类型依赖”的配置，可以在 mapping 里用“实体类型”到“data source 名”的映射解析，而不必把 Entity 变成执行单元。  
5. **行业/股票例子**：  
   - “industry 依赖 stock_list” = industry 这个 data source 的 `depends_on: ["stock_list"]`；  
   - industry 的 Handler 从 `dependencies_data["stock_list"]` 读数据，产出 Industry / stock_industry 形状，写入对应表。  
   - 不需要 `Industry.renew()`，只要“industry 这个 data source”在 stock_list 之后执行即可。

**若仍希望领域语言是“更新实体”**：  
- 可在应用层提供薄门面，例如 `renew_entity("Stock")` → 查 mapping 得到 data source 名 `stock_list`，再调现有“按 data source 执行”的入口；Entity 仍不包含 renew/fetch 方法。

---

## 6. 小结

| 项目 | 方式 A（Entity.renew()） | 方式 B（Data Source 执行，Entity 仅数据类） |
|------|--------------------------|--------------------------------------------|
| **执行单元** | Entity | Data Source（Handler） |
| **Entity** | 数据契约 + 更新行为（renew/fetch） | 仅数据契约（schema + table_name + 唯一键等） |
| **调度/依赖** | 需 Entity 依赖图与 Entity 调度器 | 沿用 Data Source 依赖图与现有调度器 |
| **与当前架构** | 需较大调整 | 小改即可，渐进引入 |
| **建议** | 不采纳 | **采纳** |

结论：**引入 Entity 时，采用“在 Data Source 中执行，Entity 只作为数据类”的定义方式更合适**；Entity 负责“长什么样、对应哪张表”，Data Source 负责“何时跑、依赖谁、如何拉数、写到哪张表”。
