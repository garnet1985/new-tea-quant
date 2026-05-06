# 策略工作台 API（V2）

本文档**仅**描述 V2 契约与语义，不包含旧接口编号或迁移对照。

## HTTP 前缀与契约编号

- **BFF** 蓝图挂载前缀为 **`/api`**（见 `core/ui/bff/app.py` 中 `register_blueprint(..., url_prefix='/api')`）。
- 路由声明形如 **`/v1/strategy/...`**、**`/v1/strategies/list`** 等，与蓝图拼接后的**完整路径**为 **`/api/v1/strategy/...`**、**`/api/v1/strategies/list`**。
- 下文表格与细则中的路径均省略 **`/api`** 前缀时，仍指上述蓝图下的同一资源。
- **「V2-xx」** 为本契约的接口族编号；URL 中的 **`/v1/`** 仅为 REST 路径版本段，**不表示存在另一套「产品级 API v1」文档**。

## FED 对接说明（实现备忘）

下列条目便于前后端开工对齐；**不改变**上文契约条款。

- **表单选项与 profiles（按选项控制显隐/必填）**  
  **V2-04** 当前保证响应内有 **`items`**（每项至少 **`value` / `label`**）。历史上 SWB 风格的 **`profiles`**（按某个 `value` 给出 `configurable_fields` / `required_fields`）**不在必选契约内**。首期建议 **FED 用静态映射表**与引擎校验规则对齐；若需服务端单一来源，可在后续迭代中扩展 **V2-04** 响应形状（并同步本文档与 BFF）。

- **报告「产品化」UI**  
  股票表分页、K 线、专用对比聚合等 **无单独 V2 资源**。首期可对 **V2-07 / V2-08** 返回的 **`report` / `result_report`** 做解析展示，不足部分 **mock**；**`report` JSON 与 UI 组件期望形状**可在核心模块与 FED 迭代中对齐。若某 **`version_id`** 因物理产物保留策略等原因**无法还原明细**，由 **UI 提示用户重新 run**（产品约定）。

- **恢复工作台到某一版本**  
  无单独「restore」POST。使用 **V2-08** 拉取该 **`version_id`** 的整包快照（与 **V2-01** 同形），将 **`settings` / `step_status` / `result_report`** 填回表单与步骤状态即可；是否在服务端再写入**新快照行**由产品决定（若需要再另立接口或流程）。

- **发布到 userspace**  
  使用 **V2-09**，路径上的 **`version_id`** 指定要落盘的那条快照；**不得**在 body 里用另一套 settings 覆盖该语义（见 V2-09 细则）。

- **枚举复用 / 缓存预判**  
  **不对接**；FED / BFF **不展示** BED 是否命中缓存。

## 核心模型

- **版本（version）** = 策略工作台版本 = **快照（snapshot）**，三者指同一实体。
- **运行（run）** 是**动作**，不是持久化的业务实体。
- **前端不持久化版本列表**；版本的创建、`latest` 指向由**后端**维护。
- 页面状态以 **`version_id`** 为锚点。

### `version_id` 与「本次运行」流水线的关系

- **何时存在**：对**某次** **`POST …/run`** 产生的产出而言，**新的 `version_id`** 仅在 **BED** 侧 **job 成功结束并完成持久化（含写入快照与可缓存的结果）之后**才成立。
- **谁在何时第一次看到它**：**持久化完成后**，**V2-06** 在 **`status` 为已完成且已有快照 id** 时**可以**在响应里带上 **`version_id`**（便于紧接着拉报告）；**取该步明细正文**须再调 **V2-07 `GET …/report?version_id=…`**。**不是**来自 **`POST …/run`**。

### 页面加载时的 `version_id` 与一次 run 结束之后

- **进页时带了 `version_id`**：一般表示**上一次 run 已成功落库**后保存下来的锚点（如路由、会话、或前次 **V2-07** 写入的「当前版本」），**不是**本次还没跑完的工作中间态。
- **进页时不带 `version_id`**：表示还没有任何一次**可展示的成功运行结果**可锚定（或尚未与 **V2-01** 等拉齐首条版本）。
- **本次流水线全部结束（含 BED 持久化完成）之后**：用 **V2-06** 返回的 **`version_id`**（或与之一致的锚点）调用 **`GET …/report?version_id=…`** 拉该步报告；**页面锚点**可在 **report 成功响应** 与 **progress completed** 中择一或双重确认（二者 **`version_id` 一致**）。
- **与进页锚点的先后关系（语义上）**：
  - **未命中缓存、产生新版本行**：新的 **`version_id`** 相对进页时的锚点通常是**更新的一个版本**（存储侧递增的一条快照）。
  - **命中缓存、复用已有快照行**：**不会**产生新的版本行，**`version_id` 可以与进页时相同**；不得以「必须比进页大一号」作为契约。

### BFF 边界：不做缓存，只做转发与 HTTP 门面

- **任何「命中缓存 / 指纹复用 / 结果可否短路」** 均为 **BED（含引擎与存储）** 的内部策略；**BFF 不参与决策，也不实现业务缓存**。
- **BFF** 在本工作台契约下的职责限于：**解析与校验 HTTP**、**必要时把 body 交给 BED 做 normalize**、**调用 BED 领域入口**、**把 BED 返回值装入统一响应信封**。既往若在 BFF 层做过「缓存加速」「缓存命中判断」等，**与 V2 契约不符**，应迁入 **BED** 或删除。
- **推论**：编排文档里凡涉及「是否缓存」，**实现落点一律写在 BED**；**BFF** 条目里不得出现「缓存命中分支」。
- **编排允许的 BFF 行为**：除上述外，**将请求体交给 BED 做 `normalize`、调用 BED 返回再封信封**，属于门面职责，**不**视为「业务缓存」。

## 生命周期规则

### `latest` 的初始化

- `GET /strategy/{strategy_name}/version/latest`（V2-01）**始终**返回一条有效的「当前最新版本」。
- **尚无任意版本时**：后端读取磁盘上的物理策略 settings，生成**第一个**版本并作为 `latest`。

### 一次「运行」的三段式（FED / BFF 不感知是否命中缓存）

**是否走缓存、如何算指纹、是否落库 version**，**仅 BED 内部**决定；**BFF 与 FED 均不分支「命中 / 未命中」**，只按下面三步编排：

| 阶段 | 接口 | 职责 |
|------|------|------|
| 启动 | **`POST …/run`（V2-05）** | **只负责触发 job**；响应**不**含本次将产生的新 **`version_id`**；成功时 **`is_triggered`** 且须返回 **`job_id`**（供 **V2-06** 轮询）。 |
| 轮询 | **`GET …/progress`（V2-06）** | **只读进度**；**到 100%** 表示本条任务在后端已完结；**已完成且落库后**响应中**可以**含 **`version_id`**（与快照一致）。 |
| 取结果 | **`GET …/report?version_id=…`（V2-07）** | **在已有 `version_id` 后**调用（通常来自上一步 **V2-06 completed**，或 V2-03 / 进页锚点），取该 **`step`** 的报告正文；响应**回显** **`version_id`**。 |

- **走缓存时**：上述三步都会在很短时间内结束（进度仍可能被建模为 0→100，只是更快）。
- **不走缓存时**：时间主要花在 **V2-06** 轮询上。

**FED**：只做 settings + 策略上下文上报（**V2-05**）、轮询 **V2-06**，在 **completed** 且已有 **`version_id`** 后请求 **`GET …/report?version_id=…`** 拿该步报告；**不**做 normalize；**不**理解指纹。

**BFF**：校验与转发（门面）；对 **`settings`** 可调 **BED** 做 **normalize** 再交给 **BED** 启动 job；**不**参与指纹判断；**不**做任何业务缓存（见上文 **「BFF 边界」**）。

## API 清单（V2）

| 编号 | 方法 | 路径 | 用途 |
|------|------|------|------|
| V2-01 | GET | `/strategy/{strategy_name}/version/latest` | 获取 latest；**路径** `strategy_name` **必填**；响应含 `version_id`、`settings`、`step_status`、`result_report` 等 |
| V2-02 | GET | `/strategies/list` | 策略列表（分页） |
| V2-03 | GET | `/strategy/{strategy_name}/versions` | 某策略工作台版本的**最近 10 条**（固定条数、不分页），用于「恢复到某一版本」下拉框 |
| V2-04 | GET | 多个明确路径（见下） | 选项类 / profile 类全量数据；**非**单一泛化 `/strategy/{entity}`，implementation 按资源拆路由 |
| V2-05 | POST | `/strategy/{strategy_name}/{step}/run` | **启动**一步对应的 job（仅表示触发成功与否；结果见 progress → report） |
| V2-06 | GET | `/strategy/{strategy_name}/{step}/progress` | **轮询**该步骤 job 的**进度**（不区分缓存；到 100% 后去拉 report） |
| V2-07 | GET | `/strategy/{strategy_name}/{step}/report` | **必填** query **`version_id`**（``v3`` / ``3``）；响应含该步 **`report`** 并回显 **`version_id`** |
| V2-08 | GET | `/strategy/{strategy_name}/version/{version_id}` | 按 **`version_id`** 读完整快照；**路径** `strategy_name` **必填**；响应与 **V2-01** 同形（切换版本后用；内含汇总 summary，见「V2-07 与 V2-08」） |
| V2-09 | POST | `/strategy/{strategy_name}/apply-settings/{version_id}` | 将某工作台版本的 **`settings` 快照** **永久化**到该策略目录的 **`settings.py`**（反向写磁盘）；**路径** `strategy_name` **必填** |
| V2-10 | GET | `/strategy/{strategy_name}/versions/range` | 按**时间段**筛选版本列表，**必须分页**（浏览 / 检索历史版本） |

### V2-04 说明（选项类家族）

- **不是**单一泛化路由（禁止 `/strategy/settings/{entity}` 一类运行时拼接）；**每个选项资源一条固定的 GET 路径**，路由与 handler 在实现里显式注册。
- **当前契约已锁定的示例子路径**见下表（响应字段以 **契约细则 · V2-04 家族共性** 为准；新增资源时在本表与 [`API_LAYER_STEPS.md`](./API_LAYER_STEPS.md) 各增一行）。

| 子路径 | 用途 |
|--------|------|
| `GET /strategy/settings/capital-allocation-strategies` | 资金分配方式等枚举选项（表单下拉 / radio） |
| `GET /strategy/settings/sampling-strategies` | 采样策略等枚举选项 |

- **与「profiles」**：见上文 **「FED 对接说明 · 表单选项与 profiles」**；本表接口**不隐含**返回 SWB 式 `profiles`，除非后续扩展并写明字段。
- 其它选项资源：**路径命名与上表同一风格**（`/strategy/settings/...`），上线前完成上表与编排文档的同步增补。

## 契约细则

### V2-01 `GET /strategy/{strategy_name}/version/latest`

- **路径参数 `strategy_name`**：与 **V2-03** / **V2-05** 等相同，标识目标策略；**须**出现在 URL 中（**不得**仅依赖 query/body 传策略名取代路径）。
- **语义**：返回当前策略工作台的 **latest 快照**（与 **V2-08** 同形 DTO，区别为按「最新一条」而非按 id）。
- **尚无任意快照时**：见 **「`latest` 的初始化」**（可由物理 `settings` 冷启动首条）；一旦存在快照行，**正常工作台状态一律以 DB 快照为准**。

### V2-05 `POST /strategy/{strategy_name}/{step}/run`

- **路径参数 `strategy_name`**：与 **V2-03** / **V2-10** 相同，标识目标策略；**请求体不得**用另一策略名覆盖（若 body 含 `strategy_name` 作校验，则**必须**与路径**完全相同**，否则 **400**；推荐实现为**只认路径、忽略或禁止 body 中的** `strategy_name`）。
- **路径参数 `step`**：要触达的目标步骤，取值限定为 **`enum` | `price` | `capital`**（与前端步骤条、引擎管线一致；大小写按实现统一，建议全小写）。
- **请求体（JSON）**（字段以实现校验为准，以下为语义必备集）：
  - **`settings`**：`object`，**必填**。须为 FED 事先通过 **GET**（如 **V2-01** `GET /strategy/{strategy_name}/version/latest`）加载并与表单绑定后的 **API 形态 settings**；POST 时随请求提交。**若缺失、为 `null` 或非 object** → **400**（或 **422**，项目统一即可），服务端**不**再读库用「当前最新快照」兜底。
  - **`is_force`**：`boolean`，默认 `false`。含义由 **BED** 统一实现（如是否绕过可复用结果、强制重算），**BFF/FED 不解释业务分支**。

#### 响应（本接口的语义终点 =「是否成功触发 job」）

- **成功**响应至少包含 **`is_triggered: true`**，表示 job 已被后端接受并进入可被 **V2-06** 观察的状态。
- **不要求**、**通常也不返回** **`version_id`**；**不**在本接口返回最终报告正文。
- **须**返回 **`job_id`**，供 **V2-06** 必填 query 关联；可不返回 **`run_id`**（与本实现无关）。
- **失败**响应：`is_triggered: false`，`reason: object | string`。

### V2-06 `GET /strategy/{strategy_name}/{step}/progress`

- **职责**：**只读进度**；**不**区分是否命中缓存。
- **路径参数 `strategy_name`**：与 **V2-05** 一致。
- **路径参数 `step`**：**枚举**，与引擎侧 **三种回测步骤**一一对应（当前契约占位 `enum` | `price` | `capital`）。**必填** query **`job_id`**（与 **V2-05** 返回一致）。
- **`version_id`（可选呈现）**：当 **`status`** 为已完成且本次运行已写入快照 **`snapshot_id`** 时，响应**可以**包含 **`version_id`** / **`snapshot_id`**，供紧接着调用 **V2-07 `GET …/report?version_id=…`**（与之一致）。
- **轮询**：FED 在 **V2-05** 成功后重复请求，直到 **100%**（或失败）；随后用得到的 **`version_id`** 拉 **V2-07**。
- 进度数值保留 **两位小数**；可含 `is_success`、`reason`。
- **卡住进度超时**属前端行为；网络超时按全局 HTTP。
- **同一 `strategy_name`** 与 **`step`**（及给定 **`job_id`**）对应唯一一条任务记录；同屏至多一条 active job，与 **V2-05** 互斥一致。

### V2-07 `GET /strategy/{strategy_name}/{step}/report`

- **Query**：**必填** **`version_id`**（`v3` 或 `3`）。典型来源：**V2-06** 在任务完成且已落库后返回的 **`version_id`**；或 **V2-03** / 进页锚点等「已知版本」场景。
- **语义**：读取该快照 **`result_report`** 中与 **`step`** 对应的槽位（`enum` / `price_factor` / `capital_allocation`），作为 **`report`** 返回；**`strategy_name`** 须与快照一致，否则 **404**。
- **调用时机**：须在已有可信 **`version_id`** 之后（通常 **progress** 已为 **completed** 且带回 **`version_id`**）。
- 响应须**回显** **`version_id`**；**失败 / 无快照** → **404**。

### V2-08 `GET /strategy/{strategy_name}/version/{version_id}`

- **路径参数 `strategy_name`**：与 **V2-01** 相同；**须**出现在 URL 中。
- **路径参数 `version_id`**：工作台快照的主键/展示 id（如 `v3`，格式与 **V2-01** 等一致）。
- **语义**：读取**指定版本**的完整工作台快照并映射为与 **V2-01** **同一形状**的契约 DTO（含 **`version_id`**、`settings`、`step_status`、`result_report` 等），供 FED **恢复到该 snapshot 的 UI 状态**（与 **latest** 的区别仅在于**按 id 取行**，不按「最新一条」）。
- **与 V2-01 的差异**：**不**存在「无快照则冷启动从磁盘造首条」的 **2.1** 分支；若 **`version_id`** 不存在、或与 **`strategy_name`** 不匹配 → **404**。行损坏时的校验 / 删除 / 重试可与 **V2-01** 分支 **2.2** 同构（约定 A/B），见 [`API_LAYER_STEPS.md`](./API_LAYER_STEPS.md)。
- **缓存/指纹**：由 **BED** 决定；**BFF** 仅转发与映射（见 **BFF 边界**）。

### V2-09 `POST /strategy/{strategy_name}/apply-settings/{version_id}`

- **路径参数 `strategy_name`**：目标策略；**须**出现在 URL 中（与 **V2-01** 等一致）。
- **路径参数 `version_id`**：要落地到磁盘的那份工作台快照版本。
- **工作台数据模型**：页面加载与版本列表等工作台功能**一律以快照（DB）为准**，除非尚无任何快照（此时走 **V2-01** 冷启动首条等分支）。
- **语义**：将该 **`version_id`** 对应的 **`settings_snapshot`（API 形态经 BED 规范化后）** **写入**该策略目录下的物理 **`settings.py`**（覆盖用户空间文件），即把「仅存在于工作台 DB / 临时缓存语义下的版本」**永久化**到 repo 内策略包；**不等价**于一次新的 **`POST …/run`**。
- **`latest` 与物理最后写入对齐**：**apply 成功**后，BED **须更新**该 **`version_id`** 对应快照行的 **`updated_at`（last update）**，使得 **`GET /strategy/{strategy_name}/version/latest` 与「磁盘 settings 最后一次由工作台写出」在版本语义上指向同一快照**（避免 latest 仍指向旧行而磁盘已是另一意图）。
- **请求体**：可为空对象 **`{}`**，或含实现支持的选项（如 **`pretty`** 是否美化写出）；**不得**在 body 里再传一整套 **`settings`** 覆盖路径上的 **`version_id`**（除非后续契约显式允许，默认 **不允许**）。
- **成功**：至少 **`applied: true`**（及 **`strategy_name`** 等辅助字段，形状与项目信封一致）。
- **失败**：版本不存在、与策略不匹配、校验失败、写盘失败等 → **4xx/5xx** 按约定；**不**应留下半写入的损坏文件（建议先备份再原子写，见编排文档）。
- **副作用**：直接修改用户仓库内文件；调用前应在前端二次确认（产品侧）。

### V2-03 `GET /strategy/{strategy_name}/versions`

- **策略作用域**：路径参数 **`strategy_name`** 必填；表示「哪一个策略」的工作台快照版本。
- **条数**：服务端**固定返回至多 10 条**，按版本从新到旧（或按 `updated_at` 降序，实现阶段择一并在 BED 固定）；**不支持**客户端改 `limit`（避免与「下拉专用」语义混淆）。
- **用途**：恢复版本下拉、对比目标列表的快速数据源（与其他「全量浏览」接口区分）。

### V2-10 `GET /strategy/{strategy_name}/versions/range`

- **策略作用域**：路径参数 **`strategy_name`** 必填。
- **筛选**：须支持按时间窗口过滤版本（边界语义实现阶段落定，建议 query：**`start`** / **`end`**，ISO 8601 字符串，表示 **`created_at` 或 `updated_at` 落在区间内**——二选一写死在契约里）。
- **分页**：与「固定约定」一致，请求 **`page`、`limit`**，响应 **`total`** + **`page_info`（或等价）**；**不得**依赖客户端一次性拉全量。

### V2-04 选项类 GET（家族共性）

- **作用域**：一般为**工作台表单用的静态或半静态枚举目录**，**不**按 `strategy_name` 区分（若某选项将来策略相关，须**新开路径**并在本文档单列，禁止在同一资源下混用两种语义）。
- **分页**：**不分页**；单次响应返回该资源的**完整选项列表**（体量由产品控制在可接受范围内）。
- **响应**：成功信封内至少包含 **`items: array`**；每项至少包含 **`value`**（提交 / 写入 settings 用的稳定键）与 **`label`**（展示文案）。允许附加 **`description`**、**`disabled`** 等扩展字段，以各子路径在 `API_LAYER_STEPS` 中的约定为准。
- **错误**：配置缺失或组装失败时 **5xx**；目录合法为空时 **`items: []`**、**200**（是否允许空列表由产品定，默认允许）。

## 固定约定

### `strategy_name`（凡针对某策略的接口，须在 URL 路径中）

- **原则**：凡操作**某一具体策略**工作台（读 latest、读指定版本、apply、run、progress、report、版本列表等），**`strategy_name` 必须作为路径段出现**（统一写作 **`/strategy/{strategy_name}/…`**），**不得**仅靠 query 或 body 作为唯一策略定位（校验字段除外）。
- **例外**：**不**针对单一命名策略资源的接口（如 **V2-02** 策略列表、**V2-04** 全局选项目录）**不带** `{strategy_name}`，符合产品设计即可。

---

- **分页**：查询参数与响应结构沿用本项目内对 **`page` / `limit` / `total`** 的既有约定（含 `page_info` 或等价字段的具体形状在实现时与现有列表接口对齐）。**V2-02** `GET /strategies/list`、**V2-10** `GET /strategy/{strategy_name}/versions/range` **必须按此分页**（非全量一次返回；除非后续契约显式改为一页拉全量）。
- **选项类接口**：各选项资源的 **URL 拆分方式** 与现有 settings 相关 GET 约定对齐；不在本文档中新增「运行时动态展开泛型路径」的规则。

## V2-07 与 V2-08：何时调用、数据关系

| 接口 | 典型时机 | 内容侧重 |
|------|----------|----------|
| **V2-07** | **在已持有 `version_id` 后**（多来自 **V2-06 completed**，或列表/锚点） | **按步骤**的 report（路径含 **`step`**，query **`version_id`**） |
| **V2-08** | 用户在 UI **切换到某一 snapshot（`version_id`）** 之后，拉**整份工作台快照**以恢复表单与步骤状态 | 与 **V2-01** **同形**的整包 DTO |

- **包含关系**：**V2-08**（及 **V2-01**）返回的版本体中的 **`result_report`（或等价聚合字段）** 应**汇总**各步骤结果；其中**包含**与各 **`step`** 对应的 **V2-07** 所能提供的摘要内容（不必重复单独拉 **V2-07**，除非产品要单独刷新某一 `step` 的明细）。

## 对比与基准（业务语义，非额外接口）

- **基准侧（base）**：来自当前 **`latest`** 对应的 `version_id`，通过 **V2-01** / **V2-08** 拉整包快照（内含汇总 summary）；**run 结束后**可按需再调 **V2-07** 看该 **`step`** 的明细。
- **对比目标**：从 V2-03（或 V2-10）任选 `version_id`，再经 **V2-07**（按 step）及 **V2-08**（整包）对照。

---

*细节字段（V2-01 响应体的完整 JSON 形状、各 `step` 对外命名与展示文案等）在后续迭代中补齐。*
