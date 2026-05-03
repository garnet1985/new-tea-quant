# V2 API 三层实现说明（FED / BFF / BED）

与 [`API.md`](./API.md) 配套。每个 API 写清：**层**、**函数名**、**输入**、**输出**。**带点号的层级（如 `2.1`、`2.2`）只表示分支 / 情况**；分支内部做事一律用 **step1、step2…** 顺序列出，不把函数编号成 `2.1.1`。

- **FED**：前端（fed）
- **BFF**：Backend for Frontend，在本契约下**主要是 HTTP 门面**：校验、转发、组装信封；**不**承载业务缓存、指纹、命中判断（详见 [`API.md`](./API.md) **「BFF 边界：不做缓存，只做转发与 HTTP 门面」**）。
- **BED**：后端领域与基础设施（`core` 等，非 BFF）；**凡与缓存、指纹、版本落库相关的语义**，只在此处落地。

函数名为**约定名**：实现时可落在具体模块，但全仓应对齐同一套名字，避免「一样的事不同叫法」。

### 文档用语：层标注与调用方向（固定读法）

下文若出现括号标注，**只描述「这一步主要由谁写 / 谁调用谁」**，不是业界通用符号；后来的读者与 agent **一律按本节释义**，不要自行类比 HTTP 报文流向或其它项目的箭头习惯。

| 写法 | 含义 |
|------|------|
| **`### BFF / BED（顺序执行）`** | 该 API 的本段编排同时涉及 BFF 与 BED；步骤从上到下执行。 |
| **`（BFF）`** | 这一步的实现重心在 BFF：解析请求、分支判断、组装 DTO、写 HTTP 信封等；**未写箭头不代表本步不调 BED**，仅表示叙述重心在 BFF。 |
| **`（BED）`** | 这一步的实现重心在领域层 / `core`（仓储、规则）；通常仍由 BFF 在编排里**调用**入口函数，而非前端直连。 |
| **`（BFF → BED）`** | **调用方向**：BFF 在本步内调用 BED 暴露的能力（函数、服务、仓储）。**不是**「数据只能从 BFF 流向 BED」，也**不是**单独一档 HTTP；只是标明**边界在哪一侧落地**。 |
| **`### FED（客户端）`** | 浏览器 / fed 侧调用顺序，与 BFF/BED 编排无关。 |

若某一步只有 **`（BFF）`** 但也读了数据库，仍视为「编排发起方在 BFF」：实际 SQL 可在 BED 仓储中实现，此时可在同一步补充 **`（BFF → BED）`** 以免歧义。

---

## V2-01 `GET /strategy/{strategy_name}/version/latest`

**作用**：取当前策略的 **latest** 工作台版本；无版本时从物理 settings 建首条并落库。响应需含 `version_id`、`settings`、`step_status`、`result_summary` 等（以 `API.md` 为准）。

**请求**：**路径** **`{strategy_name}` 必填**；与 [`API.md`](./API.md) **「`strategy_name`（凡针对某策略的接口，须在 URL 路径中）」** 一致。工作台在存在快照时**以 DB 快照为准**。

### BFF / BED（顺序执行）

**编号含义（别混了）**

- **`1`、`3`、`4`**：主流程上的大块顺序。
- **`2.1`、`2.2`、`2.1.1`…**：只表示**分支 / 子分支**（是哪一种情况），**不是**「第几步做事」。
- **分支里面的做事顺序**：用 **step1、step2、step3…** 从上到下写；一个 step 对应一次函数调用（或一段不可分割的动作）。

**总编排**

1. 先做 **1**（读库有没有 latest）。
2. 再看 **1** 的结果，**二选一**进入 **2.1** 或 **2.2**（只看情况，下面对每个分支里逐步列）。
3. 拿到可用的 `strategy_snapshot` 后做 **3** → **4**。

---

#### 1 — 读库：有没有 latest 快照行

- **做什么**：按 `strategy_name` 查询工作台快照里「当前 latest」对应的一条记录（或等价视图）。
- **目的**：只回答一个问题——**有没有一条可用的候选快照**，从而在后面 **2.1 / 2.2** 二选一。
- **实现落点**：`get_latest_version_snapshot`（BFF 调 BED / 仓储）。
- **触发条件**：本请求**最先**执行；若分支 **2.2** 里 **step2**（删除）成功，**回到本步重新开始**（同一请求内可循环）。
- **输入**：`strategy_name: str`
- **输出**：`null`（无可用 latest），或 `strategy_snapshot: object`（库里最近一条快照行）

---

### 2 — 根据步骤 1 的结果分两种**情况**（互斥）

步骤 **1** 已经回答了「库里有没有一条 latest 候选」。下面 **只做其中一种情况**：要么冷启动补首条（**2.1**），要么对已有行做校验 / 删除（**2.2**）。

#### 2.1 — 分支一：冷启动（磁盘 → 第一条快照）

- **这是哪种情况**：步骤 **1** 得到 `null`，库里还没有可用 latest。
- **要达成什么**：确认策略在磁盘存在 → 读物理 `settings` → 写入第一条工作台快照并标 latest。

**step1** — `discover_strategies`（BED）

- **何时做**：已确定走本分支 **2.1**。**若**发现结果里没有当前 `strategy_name` → BFF **404**，后面 step 都不跑。
- **输入**：无；或 `include_disabled?: bool`（工程约定）
- **输出**：`discovered: Map<strategy_name, StrategyDiscoveredInfo>`

**step2** — `get_strategy_settings`（BED）

- **何时做**：step1 已证明策略存在。**若**物理文件缺或加载失败 → **404/500**，不跑 step3。
- **输入**：`strategy_name: str`
- **输出**：`settings: dict`

**step3** — `create_initial_workbench_version`（BED）

- **何时做**：step2 已成功。**写完**之后要不要再过一遍「校验」，见分支 **2.2** 里 **step1** 的**约定 A / B**（新建默认可直接去 **3**，或必须先校验）。
- **输入**：`strategy_name: str`，`settings: dict`
- **输出**：`strategy_snapshot: object`（首条快照；写库在 BED）

---

#### 2.2 — 分支二：库里已有行，先校验，坏了再删

- **这是哪种情况**：步骤 **1** 返回**非** `null`。
- **要达成什么**：判断这条快照能不能展示；不能则删掉并让步骤 **1** 重读（避免坏数据卡死）。

**step1** — `is_version_valid`（BFF）

- **何时做**（二选一写死）：
  - **约定 A（推荐）**：只要步骤 **1** 读出了非 null，就走本步，只校验「库里那一行」。若本轮结果是走 **2.1** 的 step3 **刚新建**的快照，**不**走本步，默认可用，直接去 **3**。
  - **约定 B**：凡进 **3** 之前的任意快照（含 **2.1** 里 step3 新建）都要先本步为 `true`。
- **输入**：`strategy_snapshot: object`
- **输出**：`valid: bool`

**step2** — `delete_version`（BED）

- **何时做**：**仅当**本分支 **step1** 得到 `valid == false`。删成功 → **回到步骤 1**；删失败 → 报错，**不要**死循环。
- **输入**：`strategy_name: str`，和/或 `version_id: str`（契约定）
- **输出**：`ok: bool`

---

#### 3 — 组装：给前端的统一响应体（契约 JSON）

- **做什么**：把分支 **2** 结束时手里的 **`strategy_snapshot`（领域态 / 存储态）**，变成 [`API.md`](./API.md) 规定的**这一条 GET** 的响应 JSON：字段名、嵌套、`settings` 用 UI 可读形态、`step_status` / `result_summary` 等与 FED 约定一致；不该下发的内部字段在此剔除或折叠。
- **目的**：FED **只认一种 DTO**，不必知道数据来自 DB 哪列、也不必耦合 BED 内部字典结构；以后存储演变只改这一层映射。
- **实现落点**：BFF 调用 `to_fed_strategy_workbench_format(strategy_snapshot)`，产出 `workbench_dto`。这是本步里的**核心一段逻辑**，不是单独再来一层「步骤 3.1」——整个第 **3** 步就是在做「领域快照 → 契约 DTO」这件事。
- **触发条件**：已有最终可用的 `strategy_snapshot`：
  - **约定 A**：要么（**1** 非 null 且 **2.2** 的 **step1** 为 `true`），要么（**1** 为 null 且已做完 **2.1** 的 **step3**）；
  - **约定 B**：进 **3** 前须 **2.2** 的 **step1** 为 `true`（含 **2.1** 的 step3 若强制校验）。
- **输入**：`strategy_snapshot: object`
- **输出**：`workbench_dto: dict`

#### 4 — 返回 HTTP 成功信封

- **做什么**：把 **3** 得到的 `workbench_dto` 放进本项目统一的「成功响应」结构（如 `ok(...)` 包装）。
- **目的**：与全站 BFF 错误码、信封格式一致，便于前端拦截器处理。
- **实现落点**：`ok(workbench_dto)`（BFF）。
- **触发条件**：**3** 已成功。
- **输入**：`workbench_dto: dict`
- **输出**：HTTP 200 + body

---

### FED（客户端）

这里不分 `2.1` 这类号；成功路径从上到下 **step1 → step2 → step3**，失败走 **step4**。

**step1** — `requestWorkbenchLatest`

- **何时做**：进入工作台页，或切换当前 `strategyName`；同页无切换则不重复（除非产品「刷新」另议）。
- **输入**：`strategyName: str`
- **输出**：`Promise<WorkbenchLatestDto>`
- **说明**：发起 `GET …/strategy/{strategyName}/version/latest`（`strategyName` 在 path）。

**step2** — `setWorkbenchAnchor`

- **何时做**：step1 **成功**且响应含有效 `version_id`。
- **输入**：`version_id: str`
- **输出**：无

**step3** — `hydrateWorkbenchFromDto`

- **何时做**：step2 之后（或同一成功回调内紧跟 step2）。
- **输入**：`WorkbenchLatestDto`
- **输出**：无（表单、步骤条、`result_summary` 等）

**step4** — `onWorkbenchLatestError`

- **何时做**：step1 **失败**（网络/4xx/5xx）。
- **输入**：`error: ApiError`
- **输出**：无（一般不覆盖已有 `version_id`，除非产品另有约定）

**`WorkbenchLatestDto`**：与 BFF **3** 的 `workbench_dto` 同形。

---

## V2-02 `GET /strategies/list`

**作用**：返回**物理 workspace 里存在的策略**列表，供列表页使用；**必须分页**。请求使用 **`page`、`limit`**（query，默认值与上限按项目约定）；响应必须带 **`total`** 及与 [`API.md`](./API.md)「固定约定」一致的 **`page_info`（或等价结构）**。数据来源只有 core 的 discover；分页（排序、切片、填 `total`）在**步骤 2** 完成，不单独拆步骤。

本接口在 BFF / BED 侧**固定三步**：

---

### BFF（编排 + 出参；discover 在 core/BED）

**步骤 1** — 调用 core 的 discover，拿到**全部**策略（BFF）

- **做什么**：BFF 调 `discover_strategies()`（或项目里统一的 StrategyDiscovery，归属 **BED/core**），得到磁盘扫描结果。
- **目的**：列表与 CLI 同源，只反映「物理上有哪些策略包」。
- **输出**：`discovered`（原始发现结构，以实现为准）

**步骤 2** — 转成前端格式 + **分页**（BFF）

- **做什么**：读取本次请求的 **`page`、`limit`**（可在路由入口解析后传入）；将 `discovered` 映射成契约行；按稳定规则排序；再按 `page`/`limit` **切片得到当前页**；计算 **`total = 全集条数`**；组装分页元数据（`page_info` / `total` 等，形状遵守 [`API.md`](./API.md)）。
- **目的**：返回的是「一页数据 + 分页信息」，不是一次性甩全量。
- **实现落点**：如 `to_response_format` + 分页拼装（可合并为一个入口函数）。

**步骤 3** — 返回 list（BFF）

- **做什么**：用项目统一成功信封包装（如 `ok({ strategies: 本页数组, page_info: ..., total: ... })`，字段名以 [`API.md`](./API.md) 为准）。
- **目的**：HTTP 200 + 响应体。
- **实现落点**：`ok(...)`。

---

### FED（客户端）

请求本接口时**始终传 `page`、`limit`** → 用返回的**本页 list** + **`total` / `page_info`** 渲染表格与分页器；失败则提示。DTO 与 **步骤 3** 响应体同形。

---

## V2-03 `GET /strategy/{strategy_name}/versions`

**作用**：返回**指定策略**下工作台快照版本的**最近 10 条**（固定上限、**不分页**），供「恢复到某一版本」等 **Select** 使用。路径与语义以 [`API.md`](./API.md) **V2-03** 为准。

### BFF / BED（顺序执行）

**总编排**

1. 解析并规范化 **`strategy_name`**（路径参数）。
2. 确认该策略在 workspace **存在**；不存在 → **404**，不再访问库。
3. 从仓储读取该策略的版本行，**按统一排序规则取前 10 条**（仅截取，不提供 `page`/`limit`）。
4. 映射为契约 DTO 列表 → 成功信封。

---

#### 1 — 解析入口参数（BFF）

- **做什么**：读取路径里的 **`strategy_name`**，做 trim / 与工程一致的字符规范化。
- **输出**：`strategy_name: str`

#### 2 — 策略是否存在（BFF → BED）

- **做什么**：判断「物理 workspace / discover 意义下」该 **`strategy_name`** 是否有效（与 V2-01 冷启动分支同一标准即可）。
- **实现落点**：如 `ensure_strategy_exists` 或 `discover_contains_strategy`（BED）。
- **分支**：
  - **2.1** 不存在 → HTTP **404**，本请求结束。
  - **2.2** 存在 → 继续 **3**。

#### 3 — 读库：最近 10 条版本行（BFF → BED）

- **做什么**：按 `strategy_name` 查询工作台快照表（或等价仓储），按 **`API.md` 约定顺序**（如新版本在前）排序，**仅取前 10 条**。不要求本接口返回全字段；至少含 **`version_id`** 及供下拉展示的辅助字段（如 `updated_at`，具体列以契约扩展为准）。
- **实现落点**：`list_workbench_versions_recent(strategy_name, limit=10)`（BED / 仓储）。
- **分支**：
  - **3.1** 当前尚无任何版本 → 返回 **`versions: []`**（HTTP **200**），不当作错误。
  - **3.2** 有一条及以上 → 继续 **4**。

#### 4 — 组装契约 DTO（BFF）

- **做什么**：将仓储行转为前端统一列表项形状（字段名与 [`API.md`](./API.md) 对齐；剔除内部主键等）。
- **实现落点**：如 `to_fed_version_list_item(rows)` → `version_items: array`。

#### 5 — 返回 HTTP 成功信封（BFF）

- **做什么**：`ok({ strategy_name, versions: version_items })`（外层字段名以最终实现与 `API.md` 为准）。
- **输出**：HTTP 200。

---

### FED（客户端）

**step1** — `requestWorkbenchVersionsRecent`

- **何时做**：打开「恢复到某一版本」下拉，或进入依赖该列表的交互；**同一 `strategyName` 未切换时可缓存**，避免重复请求（产品另有「刷新」再议）。
- **输入**：`strategyName: str`
- **输出**：`Promise<WorkbenchVersionsRecentDto>`
- **说明**：发起 `GET …/strategy/{strategy_name}/versions`。

**step2** — `applyVersionOptionsToRestoreSelect`

- **何时做**：step1 成功。
- **输入**：`WorkbenchVersionsRecentDto`
- **输出**：无（填充 Select 的 options；通常展示 `version_id` + 时间等文案）。

**step3** — `onWorkbenchVersionsRecentError`

- **何时做**：step1 失败（含 404 策略不存在）。
- **输入**：`error: ApiError`
- **输出**：无（提示；清空或保留上次列表依产品约定）。

---

## V2-10 `GET /strategy/{strategy_name}/versions/range`

**作用**：在同一策略下，按**时间段**筛选历史版本，**必须分页**；用于「按日期浏览 / 检索」而非下拉框固定 10 条。路径、query、分页形状以 [`API.md`](./API.md) **V2-10** 为准。

### BFF / BED（顺序执行）

**总编排**

1. 解析 **`strategy_name`** 与 query：**`start`**、**`end`**（时间窗口，语义以契约定稿为准）、**`page`**、**`limit`**。
2. 校验策略存在；不存在 → **404**。
3. 校验时间参数与分页参数（缺省、上限、`start`/`end` 先后关系等）；不合法 → **400**。
4. BED 按窗口 + 分页查询，得到本页行与 **`total`**。
5. 映射 DTO → 成功信封。

---

#### 1 — 解析入口参数（BFF）

- **做什么**：路径 **`strategy_name`**；query **`start`**、**end**（可选或必填组合以实现为准）、**`page`**、**`limit`**。
- **输出**：规范化后的参数对象。

#### 2 — 策略是否存在（BFF → BED）

- **做什么**：同 **V2-03** 步骤 **2**。
- **分支**：不存在 → **404**；存在 → **3**。

#### 3 — 校验 query（BFF）

- **做什么**：校验时间边界与分页（例如 `limit` 上限、`page` 正整数、仅传一端时的语义）。细则在契约定稿后写死。
- **分支**：非法 → **400**；合法 → **4**。

#### 4 — 仓储查询：窗口内版本 + 总数（BFF → BED）

- **做什么**：按 `strategy_name` + 时间过滤条件，数据库侧或仓储侧 **COUNT 得 `total`**，再 **LIMIT/OFFSET（或等价）** 取当前页。排序规则固定（如按 `updated_at` 降序）。
- **实现落点**：`list_workbench_versions_in_range(strategy_name, start, end, page, limit) -> { rows, total }`（BED）。
- **分支**：
  - **4.1** 窗口内 0 条 → **`total: 0`**，本页空数组，仍 **200**。
  - **4.2** 有数据 → 继续 **5**。

#### 5 — 组装响应（BFF）

- **做什么**：行 → 列表项 DTO；填入 **`page_info`（或等价）**、**`total`**，与 [`API.md`](./API.md)「固定约定」一致。

#### 6 — 返回 HTTP 成功信封（BFF）

- **做什么**：`ok({ strategy_name, versions, total, page_info, ... })`。

---

### FED（客户端）

**step1** — `requestWorkbenchVersionsInRange`

- **何时做**：用户设定日期范围并查询、或时间轴视图翻页。
- **输入**：`strategyName`，`start`，`end`，`page`，`limit`
- **输出**：`Promise<WorkbenchVersionsRangeDto>`

**step2** — `renderWorkbenchVersionsTable`

- **何时做**：step1 成功。
- **输入**：本页 `versions` + `total` / `page_info`
- **输出**：无

**step3** — `onWorkbenchVersionsRangeError`

- **何时做**：step1 失败。

---

## V2-04 选项类 GET（多条路径）

**作用**：为策略工作台 **settings 表单**提供**枚举型选项**的只读全量数据（分配方式、采样策略等）。**一个资源一条固定 URL**，与 [`API.md`](./API.md) **V2-04** 及「选项类家族」细则一致；**不**做泛化动态段。

### 共性（所有子路径共享）

**BFF / BED 编排**（子路径无额外分支时，固定四步）

1. **（BFF）** 匹配到该资源的 route handler（无路径参数或仅有与资源无关的 query，以具体条为准）。
2. **（BFF → BED）** 调用 BED 侧**该资源对应**的选项装配函数（见下各子路径**实现落点**），得到领域态列表（如 `tuple` / 行结构 / 内联常量）。
3. **（BFF）** 映射为契约 DTO：``items: [{ value, label, ... }]``，键名与 [`API.md`](./API.md) **V2-04 家族共性**一致。
4. **（BFF）** `ok({ items })`；必要时可增加 **`resource`** / **`kind`** 等辅助字段，须在 `API.md` 同步。

**分支（尽量少）**

- **情况 A** — BED 组装异常或结果不可用 → BFF **500**（与「无选项可展示」区分）。
- **情况 B** — 合法的空列表 → **`items: []`**、**200**。

**与 V2-02 / V2-10 的边界**：选项类 **不走** `page`/`limit`；版本列表 **不走** 本家族。

---

### 子路径 — `GET /strategy/settings/capital-allocation-strategies`

**用途**：资金分配等相关控件的可选值（如 equal_capital、kelly 等），供表单绑定 **`value`**、界面展示 **`label`**。

**step1** — `get_allocation_mode_options`（BED）

- **做什么**：返回预先定义的分配模式枚举列表（来源可为常量表、配置或后续 DB；对本接口调用方为黑盒）。
- **输入**：无；若将来需要 locale/query，在契约增补后再列。
- **输出**：`options_raw`（ iterable：每项至少可映射出 `value` + `label` ）

**step2** — `to_fed_settings_option_items(options_raw)`（BFF）

- **做什么**：映射为 ``{ items: [...] }`` 中的每一项。
- **输出**：`items: array`

**step3** — `ok(payload)`（BFF）

- **输出**：HTTP 200；`payload` 至少含 **`items`**。

---

### 子路径 — `GET /strategy/settings/sampling-strategies`

**用途**：采样策略枚举（如 continuous、stratified 等），供表单与校验层共用同一套稳定 **`value`**。

**step1** — `get_sampling_strategy_options`（BED）

- **输入**：无（同上，将来扩展需在 `API.md` 写明）。
- **输出**：`options_raw`

**step2** — `to_fed_settings_option_items(options_raw)`（BFF）

- **说明**：可与上一子路径**共用**同一映射函数，只要输出契约一致。

**step3** — `ok(payload)`（BFF）

---

### FED（客户端）

**共性**

**step1** — `requestStrategySettingsOptions(resourceKey)`

- **何时做**：打开依赖该选项集的表单区域、或工作台首次需要渲染对应控件时（可按 `resourceKey` 缓存，避免重复请求）。
- **输入**：`'capital-allocation-strategies' | 'sampling-strategies' | …`（与路由或模块常量对齐，不求与 URL 字符串强行同一）。
- **输出**：`Promise<StrategySettingsOptionsDto>`（与 **`items`** 契约同形）。

**step2** — `bindSettingsOptionItems`

- **何时做**：step1 成功。
- **输入**：`items` + 目标表单控件（Select / RadioGroup 等）
- **输出**：无

**step3** — `onStrategySettingsOptionsError`

- **何时做**：step1 失败；通常提示错误并保持控件不可用或展示占位。

**`StrategySettingsOptionsDto`**：至少 ``{ items: Array<{ value: string; label: string }> }``；扩展字段与 `API.md` 一致。

---

## V2-05 `POST /strategy/{strategy_name}/{step}/run`

**作用**：**仅启动 job**。成功后 FED 始终再走 **V2-06 → V2-07**；**指纹 / 缓存 / 是否新建 `version_id`** 全系 **BED**，**BFF 与 FED 不感知**。详见 [`API.md`](./API.md) **一次「运行」的三段式**。

### 各层职责（谁干什么）

| 层 | 负责 | 不负责 |
|----|------|--------|
| **FED** | 提交 **`strategy_name`**、**`step`**、**`settings`**、**`is_force`**；根据 **`is_triggered`** 决定是否进入 **V2-06** 轮询 | **不** normalize；**不**猜是否缓存 |
| **BFF** | 校验请求；必要时 **`normalize`** 后调用 **BED**「启动 job」；封装 **`is_triggered` / `reason`**；可选回传 **`job_id`**（若契约需要） | **不**比对指纹；**不**决定缓存 |
| **BED** | **独占**：指纹、缓存命中与否、启 job、写进度、完成后落 **`version_id`** / report（[`API.md`](./API.md) 不写实现分支表） | — |

---

### BFF / BED（顺序执行）

本接口编排**不**展开「命中 / 未命中」——那是 **BED** 内部实现。**BFF** 只做门前 → 接纳 **`settings`** → **normalize** → 调 **BED** `start_job_for_step(...)` → 返回 **`is_triggered`**。

**总编排**

1. **1** — 解析路径/body；**`step`** 合法；策略存在；互斥槽可用（无冲突 job）。
2. **2** — body **`settings`** 必填且通过 **`validate_settings_for_strategy`**。
3. **3** — **`normalize_settings_for_fingerprint`** → **`normalized_settings`**。
4. **4** — **`start_job_for_step(strategy_name, step, normalized_settings, is_force)`**（BED）：**仅此一步**在服务端触发「含指纹判断在内的」job；BFF **只收**成功/失败与可选 **`job_id`**。
5. **5** — **`ok({ is_triggered: true, ... })`**；**不得**要求响应中带 **`version_id`**。

任一步失败：**`is_triggered: false`** + **`reason`**。

---

#### 1 — 入口与策略可执行性（门前）

**step1** — `parse_run_request`（BFF）

**step2** — `ensure_strategy_exists`（BFF → BED）→ 否则 **404**

**step3** — `assert_strategy_run_slot_available`（BFF → BED）→ 否则 **409**

---

#### 2 — 接纳 body `settings`（必填）

**step1** — 缺/**null**/非 object → **400**

**step2** — `validate_settings_for_strategy` → **`api_settings`**

---

#### 3 — `normalized_settings`（BED）

**step1** — `normalize_settings_for_fingerprint`

---

#### 4 — 启动 job（BED；黑盒）

**step1** — `start_job_for_step(...)`：内部可含指纹比对、缓存短路、异步回测等；对 **BFF** 仅暴露「已受理 / 拒绝」及可选 **`job_id`**。

---

#### 5 — 响应（BFF）

**step1** — **`is_triggered: true`**（及契约允许的 **`job_id`**）；**无** **`version_id`**。

---

### FED（客户端）

**step1** — `requestStrategyStepRun` → **V2-05**

**step2** — **`is_triggered`** 为 true 则 **`pollStepProgress`（V2-06）** 直至 **100%** 或失败（缓存命中时也会很快到 **100%**）。

**step3** — **`pollStepProgress`（V2-06）** 至 **100%** 后，调用 **`GET …/summary`**（**无** path **`version_id`** 的 **V2-07**），从**响应体**读取本次新的 **`version_id`** 与报告 —— 这是 **FED 本条流水线首次拿到新 `version_id`**（[`API.md`](./API.md) **「`version_id` 与「本次运行」流水线的关系」**）。

**step4** — 失败则 **`onStrategyStepRunRejected`**

**`StrategyStepRunDto`**：至少 **`is_triggered`**；可选 **`job_id`**；**无** **`version_id`**（与 [`API.md`](./API.md) 一致）。

---

## V2-06 `GET /strategy/{strategy_name}/{step}/progress`

**作用**：**轮询**；**只读**进度，**不**作为 FED **首次**获得新 **`version_id`** 的接口。与 [`API.md`](./API.md) **V2-06** 一致。**`step`** 为枚举，与 **三种回测**一一对应；对外命名可与产品对齐，但与 **V2-05 / V2-07** 须同一套值。

### 各层职责

| 层 | 负责 |
|----|------|
| **FED** | **V2-05** 成功后按间隔请求，直到 **100%** 或失败，再调 **无 `version_id` 的 V2-07** 取结果与首次 **`version_id`** |
| **BFF** | 透传 **BED** 的进度 DTO |
| **BED** | 维护 **0→100%** 进度；**不**在契约上要求用本接口向 FED **首次颁发** 新 **`version_id`** |

**BFF / BED**：`get_step_job_progress(strategy_name, step, job_id?)` → 进度体（`progress_pct`、`is_success`、`reason` 等；**无**必填 **`version_id`** 字段）。

---

## V2-07 `GET /strategy/{strategy_name}/{step}/summary` 与 `GET …/summary/{version_id}`

**作用**：**取结果**。**首次**新 **`version_id`** 仅来自 **无 path `version_id`** 的这一条在 **100%** 之后的响应体。与 [`API.md`](./API.md) **V2-07** 一致。

### `GET …/summary`（无 `version_id`）

| 层 | 负责 |
|----|------|
| **FED** | **V2-06** **成功完结（100%）**后调用；从**响应体**拿到 **`version_id`** + 报告，更新锚点；若响应表示**本轮无可锚定 `version_id`**（失败/无产出），**不**展示结果、**不**让该步骤条进成功态，允许用户 **重新 run**（[`API.md`](./API.md) **V2-07** 失败路径） |
| **BFF** | 转发 **BED**「本轮 job 产出」查询 |
| **BED** | 在 job **已成功持久化**后返回 summary；**响应须含本次 `version_id`** |

**BFF / BED**：`get_step_summary_current(strategy_name, step, job_id?)` → summary DTO；**成功路径**下 **必含 `version_id`**。失败或无产出时**不得**用假 **`version_id`** 冒充成功。

**与 V2-08**：**run 整条结束后**用本条（按 **`step`**）；用户**切换 snapshot** 后用 **V2-08** 拉整包（内含汇总 summary，通常已含各 step 结果）。详见 [`API.md`](./API.md) **「V2-07 与 V2-08」**。

### `GET …/summary/{version_id}`

| 层 | 负责 |
|----|------|
| **FED** | 已知 **`version_id`** 时（对比、历史、列表点选）拉取 |
| **BED** | 按版本读存储 |

**BFF / BED**：`get_step_summary_for_version(strategy_name, step, version_id)` → summary DTO（回显 **`version_id`**）。

---

## V2-08 `GET /strategy/{strategy_name}/version/{version_id}`

**作用**：按 **`strategy_name` + `version_id`** 读取**一条**工作台快照并映射为与 **V2-01** **完全相同形状**的契约 DTO，供 FED **把界面恢复到该版本**（表单、`step_status`、`result_summary` 等）。编排与 **V2-01** **基本一致**，区别是 **步骤 1** 按 **`version_id`** 查行，且 **无** 「库空则从磁盘冷启动造首条」的 **2.1**；[`API.md`](./API.md) **V2-08**。

### BFF / BED（顺序执行）

**编号含义**：主序 **1→2→3→4** 与 **V2-01** 对齐；本节 **2.1 / 2.2** 仅表示「快照行**有效 / 无效**」，**不要**与 **V2-01** 里「冷启动」的 **2.1** 混淆。

**总编排**

1. 解析路径 **`strategy_name`**、**`version_id`**（均必填）。
2. 做 **1**（按 `strategy_name` + `version_id` 读**指定**快照行，非 latest）。
3. 若 **null** → **404**（**不**走磁盘冷启动）。
4. 若命中行 → **2**，与 **V2-01** 分支 **2.2** **同构**：**`is_version_valid`**，无效则 **`delete_version`** 后可约定是否允许重试或直返 **404/422**（与 **V2-01** 约定 A/B 对齐）。
5. **3** — **`to_fed_strategy_workbench_format(strategy_snapshot)`** → `workbench_dto`（与 **V2-01** **3** 同一函数/DTO）。
6. **4** — **`ok(workbench_dto)`**。

**约定函数名**

| 约定名 | 摘要 |
|--------|------|
| `get_version_snapshot_by_id(strategy_name, version_id)` | **1**，替代 latest |
| `is_version_valid` / `delete_version` | 与 **V2-01·2.2** 一致 |
| `to_fed_strategy_workbench_format` | **3**，与 **V2-01** 共用 |

---

#### 1 — 读库：指定 `version_id` 的快照行

- **做什么**：按 **`strategy_name`** + **`version_id`** 加载一行（或等价）。
- **输出**：`null` → **404**；否则 `strategy_snapshot`。

---

### 2 — 行是否可用（与 V2-01 **2.2** 同构）

#### 2.1 — 分支：行有效

- **step1** — `is_version_valid` → `true` → 进 **3**。

#### 2.2 — 分支：行无效

- **step1** — `is_version_valid` → `false`。
- **step2** — `delete_version`；是否同 **V2-01** 回到 **步骤 1** 再读，由项目约定（通常指定 id **404** 即可，避免与用户「指向明确版本」冲突）。

---

#### 3 — 组装 DTO（BFF）

- 同 **V2-01** **3**。

#### 4 — 成功信封（BFF）

- 同 **V2-01** **4**。

---

### FED（客户端）

**step1** — `requestWorkbenchVersion`

- **何时做**：用户从 **V2-03** 列表选「恢复」、或路由带 **`version_id`** 进入工作台。
- **输入**：`versionId`，及 **`strategyName`**（query 或与 latest 同源）
- **输出**：`Promise<WorkbenchVersionDto>`
- **说明**：`GET …/strategy/{strategyName}/version/{versionId}`。

**step2** — `setWorkbenchAnchor`

**step3** — `hydrateWorkbenchFromDto`

**step4** — `onWorkbenchVersionError`

**`WorkbenchVersionDto`**：与 **V2-01** **`workbench_dto`** **同形**。

---

## V2-09 `POST /strategy/{strategy_name}/apply-settings/{version_id}`

**作用**：把 **`version_id`** 对应的快照 **`settings`** **写入**该策略 workspace 下物理 **`settings.py`**，完成「工作台临时态 → 用户目录永久落盘」。**指纹/缓存不在 BFF**；写盘与校验在 **BED**。详见 [`API.md`](./API.md) **V2-09**。

### BFF / BED（顺序执行）

**总编排**

1. **1** — 解析路径 **`strategy_name`**、**`version_id`**（均必填）。
2. **2** — **`ensure_strategy_exists`**；加载 **`version_id`** 下行；若不存在或不属于该策略 → **404**。
3. **3** — 从行取出 **`settings_snapshot`**，**BED** **`normalize`/`validate`** 为可写入 Python 文件的 **runtime 形态**。
4. **4** — **备份**现有 **`settings.py`**（若存在）。
5. **5** — **原子写**入 **`settings.py`**。
6. **6** — **BED** 更新该 **`version_id`** 对应快照行的 **`updated_at`**（及若工程需要则维护 **latest** 指针），使 **`GET /strategy/{strategy_name}/version/latest` 与本次物理写出语义一致**（[`API.md`](./API.md) **V2-09**）。
7. **7** — **`ok({ applied: true, strategy_name, ... })`**。

任一步失败：**不**应留下半截损坏文件（先备份、再原子写；失败则保持原文件或按项目约定回滚）。

---

#### 1 — 解析入口（BFF）

- **做什么**：path **`strategy_name`**、**`version_id`**；body（可选 **`pretty`** 等）。
- **若**路径参数缺失或非法 → **400**。

---

#### 2 — 解析快照与归属（BFF → BED）

**step1** — `load_version_snapshot(strategy_name, version_id)`

- **若**无行 → **404**。

**step2** — 校验 **`version_id`** 归属 **`strategy_name`**（防止 cross-strategy 路径参数攻击）。

---

#### 3 — 规范化为可落盘内容（BED）

**step1** — `snapshot_settings_to_runtime_for_file(strategy_name, settings_snapshot)`

- **若**非法 → **422**。

**step2** — `build_settings_py_text(runtime_settings, pretty?)`（BFF 或 BED，实现择一）

---

#### 4 — 备份（BFF → BED / 文件助手）

**step1** — `backup_strategy_settings_file(strategy_name)`

---

#### 5 — 写入（BFF → BED / 文件助手）

**step1** — `atomic_write_strategy_settings_file(strategy_name, content)`

---

#### 6 — 响应（BFF）

**step1** — **`ok({ applied: true, strategy_name })`**

---

### FED（客户端）

**step1** — `confirmApplySettingsToDisk`

- **何时做**：用户明确确认「写入物理 settings」（二次确认文案由产品定）。

**step2** — `requestApplySettingsToDisk`

- **输入**：`versionId`，`strategyName`，可选 body 选项
- **输出**：`Promise<ApplySettingsDto>`
- **说明**：`POST …/strategy/{strategyName}/apply-settings/{versionId}`。

**step3** — `onApplySettingsSuccess` / **`onApplySettingsError`**

**`ApplySettingsDto`**：与 **`API.md`** 成功响应同形（至少 **`applied: true`**）。

---

## 维护约定

- 新增或修改某 API 时：在本文件为该 API 增补**分级标题 + 输入/输出**；必要时先改 [`API.md`](./API.md)。
- **函数名**冲突时：以本文件与 BED 模块导出名为准，在 PR 里说明重命名。
