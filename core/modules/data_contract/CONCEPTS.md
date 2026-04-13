# Data 层概念与术语（权威说明）

本文档固定 **名词含义** 与 **目标架构**，避免与实现代码中的历史命名混读。

---

## 1. 为什么需要单独写一份

仓库里同时存在两类容易混淆的说法：

| 说法 | 含义 |
|------|------|
| **目标架构（对外）** | Strategy / Tag 以 **DataKey** 声明依赖；先 **定稿句柄**，再 **按需 load** 数据主体。 |
| **当前实现（`contracts/` 包内）** | 四类规则类上的 **`validate_raw(raw)`**：对**已经取到的裸数据**做校验/形态签发。 |

下文用 **「句柄 issue」**（`issue_handle` → `DataEntity`）与 **「校验 raw」**（`validate_raw`）区分。

---

## 2. 目标架构：四个核心名词

### 2.1 Contract（数据依赖壳 / 句柄形态）

**Contract** 指一种 **类似 dataclass 的壳**（不一定是 Python 的 `@dataclass`，这里是概念）：

- **meta**：稳定身份与语义（对应何种数据、分片方式、时间轴字段约定等）。
- **空的数据匣**：尚未物化时，**不持有**大数据主体（如全量 K 线行）。
- **context / 缓存上下文**：运行期诊断、缓存 key、与 DataManager 协作时需要的旁路信息（可初始为空）。

> **注意**：本仓库 `contracts/base/base.py` 里的 `BaseContract` 是 **规则类**（`validate_raw`）的 MVP；与本文「数据依赖壳」叙事可进一步对齐命名。

### 2.2 DataKey（依赖标识 / 工厂角色）

- **DataKey** 是 **与外部交互的主接口之一**（Strategy、Tag 等只声明 **要什么**，不 switch 字符串去绑表）。
- 系统 **自带** 一批 **core DataKey**（见 `ids/data_keys.py`）；用户通过 **userspace 扩展**（稳定字符串 id + 注册），无需改 core 文件即可扩展。
- **如何「new」出壳子、绑定哪一种 contract 形态**：由 **DataKey 自身约定 + 路由注册** 完成（枚举、注册表、工厂均可）。

### 2.3 句柄 issue（定稿依赖，数据仍空）

**issue（句柄语义）**：

- 输入：**context**、**params**（区间、复权、scenario 名等）。
- 输出：一个 **已完全定稿的 Contract 实例**（或等价句柄）：**meta + context 齐全，数据匣仍空**。
- Strategy **在注入参数阶段**使用的就是这一层 **issue**。

### 2.4 load（物化数据主体）

**load**：

- 使用句柄内的 **meta + context**，经 **DataManager（或等价 loader）** 取得 **裸数据**；
- 再按需做 **预处理** 与 **可信数据校验**（见下节「数据封闭」）。

**仅当 load 成功（或明确为空）后**，才视为「依赖在运行时可用的完整体」。

---

## 3. 「数据封闭」与 `validate_raw`

对 **已取得的裸数据** 做 **字段/形态校验**（fail-closed），由规则类 **`validate_raw(self, raw, *, context=...)`** 实现；**不是** §2.3 的 **句柄 issue**。

`DataContractManager.validate_raw(key, raw, ...)`：**解析 key → 规则类实例 → `validate_raw(raw)`**。句柄定稿请用 **`issue_handle` → `DataEntity`**（见 `runtime/pipeline.py`）。

---

## 4. Strategy 侧 DataManager 的职责（目标）

`StrategyWorkerDataManager`（及同类）在目标形态下主要做：

1. 根据 settings 声明的 **DataKey + 参数**，调用 **句柄 issue** → 得到 **已定稿、数据仍空** 的 contract 句柄。
2. 在 **合适进程与时机**（主进程全局数据 vs 子进程 per-stock 大数据）调用 **`load()`** 物化数据。
3. 物化过程中或之后，对 raw 做 **数据封闭**（上节），再交给策略逻辑。

**不应**再依赖大量 **`entity_type` 字符串 switch + 直接 DataManager.xxx.load** 作为主要扩展方式。

---

## 5. MVP：规则/句柄形态（当前共识）

为降低复杂度与内存风险，**先只强调两种**（strategy + tag 的主路径）：

| 形态 | 含义（直观） |
|------|----------------|
| **单实体 · 时序** | 绑定 **一个** `entity_id`；主体为 **时间轴上的 records**（如 K 线、tag value 按 `as_of_date`）。 |
| **单实体 · 非时序** | 绑定 **一个** `entity_id`；**无**统一时间轴维度的 per-entity 数据（如 category 类输出）。 |

- **「单实体」**指 **一次 issue 只绑定一个 entity**，不是「一个 contract 里塞多个 entity」。对外话术优先用 **「按实体分片 / entity-scoped」**，少用易误解成「一次多个」的「每个 entity」单独当标题。
- **全局列表、宏观时序、多实体批量** 等：需要时再扩展 **Global / Multi-entity** 等形态或单独 DataKey 策略；**不阻塞**当前 MVP。

---

## 6. Scope 标记（如 `global`）与谁调用 `load`

- **`global` / `per_entity`（或 entity-scoped）** 在句柄上首先是 **语义标记**：决定 **校验规则**（要不要 `entity_id`）、**路由到哪类 loader**、**缓存键怎么拼**。
- **也可作为编排参考**：提示「这类依赖通常适合主进程全量一份 vs 子进程按股票拉」，但 **不是**「框架自动替你全局 load」。
- **`load()` 只由外部编排调用**（主进程 strategy、子进程 worker、tag job 等）；句柄 **不**在 issue 时隐式拉数。是否缓存、何时释放主体 / `reload`，也由外层策略决定。

---

## 7. 与本文档相关的代码位置（过渡）

| 内容 | 位置 |
|------|------|
| Core DataKey 白名单 | `ids/data_keys.py` |
| Userspace 路由合并 | `discovery/userspace.py`、`userspace/data_contract/` |
| 规则类 + 「校验 raw」 | `contracts/**/*.py` 上的 `validate_raw` |
| 路由表 + `DataContractManager` | `registry/route_registry.py`、`registry/manager.py` |
| 句柄壳 / loader / 主链路说明 | `runtime/data_entity.py`、`runtime/loader_registry.py`、`runtime/pipeline.py` |

---

## 8. 本文档的维护约定

- **调整目标语义**：先改 **CONCEPTS.md**，再改实现与旧文档交叉引用。
- **DESIGN.md**：保留表结构、集成思路等历史细节；**易混点以本文为准**。

---

## 9. Userspace 扩展：必须一次性声明的三件事（目标）

用户新增一种可被 Strategy / Tag 声明的数据依赖时，**至少**要明确下面三段（缺一则不应视为完整扩展）：

| 要素 | 含义 |
|------|------|
| **1. `id`** | 新数据类型的 **稳定字符串标识**（全局唯一；可与 core 白名单并列，由注册表合并）。 |
| **2. `meta` / `contract`（形态）** | 这类数据的 **规则与形状**：单实体时序 / 单实体非时序、时间轴字段、必填列、scope 标记等（对应「是什么」）。 |
| **3. `loader`（怎么取）** | **如何 load**：从 DataManager / 服务 / API 取 raw，如何组装；运行期 **`DataEntity.load()` 委托给对应 loader**（对应「怎么拿」）。 |

推荐把三者打成 **一个注册单元**（概念上 `register(type_spec, loader)`），避免出现「只有 id 没有形态」或「有形态没有 loader」的半注册状态。

**与穷举的关系**：业务代码里不写 `if tag elif kline`；**穷举发生在注册表初始化**（`id -> loader`，可 core + userspace 合并）。运行时 **O(1) 查表 + 委托**。

> **现状**：本仓库仍以 `registry/route_registry`（`ContractRouteRegistry`）承载 **规则类** 路由；上表中的 **loader 注册与 `DataEntity` 句柄管线** 为 **演进目标**，落地后 userspace 扩展应迁移到「三要素」一致的一套 API。

---

## 10. 设计决议（与实现对齐，可直接废除旧不一致部分）

以下结论 **不考虑与早期半成品兼容**；与本文冲突的旧代码/旧文档以本文为准。

| # | 决议 |
|---|------|
| **1** | **不保留**与当前设计明显不一致的旧路径；可删可换，不做迁移层。 |
| **2** | **声明统一为 `data_id` + `params`**（名称以最终实现为准）。框架提供 **默认 params**；调用方只在需要覆盖时传入 **params**（合并/覆盖规则在实现里写死一处）。 |
| **3** | **子进程**内句柄随进程结束销毁即可，**不强制** `release` API；若主进程/long-lived 缓存持有大对象，再单独考虑释放策略。 |
| **4** | **`id` 全局唯一**：core 与 userspace 合并注册时 **禁止同名**；重复 **报错并退出**（启动期或注册期 fail-fast）。 |
| **5** | **先打通主链路**（issue → load → 下游消费）。**校验 raw** 可先 **空函数/占位**，不挡主线；后续再加强。 |
| **6** | **可观测性**（见下）：非主线，**当前阶段可不建**。 |
| **7** | **Tag 依赖形态**：见 **§10.2 / §10.3**（单一 `data_id` + params；形态 issue 时钉死）。 |
| **8** | **测试策略**：当前阶段 **不纳入**实现门槛。 |

### 10.1 关于 §6「可观测性」想表达什么

指多进程排障时，建议在关键路径打 **结构化信息**（例如 `data_id`、`entity_id`、耗时、行数），便于查「哪只股票、哪个依赖、哪一步慢/空」。**不是功能必需**；你们可先不做，等主链路稳定再加。

### 10.2 Strategy 依赖 Tag：单一 key + params（已定）

- **`data_id` 仍为 tag 侧统一标识**（例如 `tag` / `tag.scenario`，名称以最终实现为准）。
- **区分不同 tag 依赖**：靠 **params**（如 `scenario_name`、以及 issue 时足以判定形态的字段）；**issue 时**根据 params +（必要时）scenario **元数据** 选定 **哪一种 contract 形态**（单实体·时序 vs 单实体·非时序）。
- **loader 可共用**：取数路径不因「时序/非时序」而换实现；差异在 **contract 形态与校验**，不在「去哪张表」的穷举上换 loader。

### 10.3 Tag 形态不可热切换

- **时序 ↔ 非时序** 不能在同一 **已 issue 句柄** 上靠改字段「切来切去」。
- 若业务上 tag 从时序变为非时序（或反之）：必须 **重新 issue**（新句柄），再 **load**。
- 理由：句柄上绑定的 **contract 形态** 与缓存键语义在 issue 时已闭合；热切换会导致静默错读或缓存污染。

### 10.4 Tag scenario 元数据默认 vs Strategy `params` 覆盖

- **Scenario 侧**可声明「是否时序 / kind」等：主要表达 **存法与默认消费语义**（数据如何落库、默认按什么形态理解）。
- **现实业务**中，同一类标签可能既像「分类」又随时间变化；**存储仍可为时序**（多期、带 `as_of_date`），与策略本次想怎么用无关。
- **Strategy 声明**里通过 **`params` 覆盖** scenario 默认值，表达 **本次 issue/load 的视图**：例如只要 **当前** 分类、只要 **as_of=T**、只要某段历史等；**不改变**物理存储，只收窄 **本次返回的数据切片与消费约定**。
- **合并规则**：与 §10 第 2 条一致——**scenario / 框架默认** 为底，**strategy `params` 显式覆盖优先**；具体字段名（如 `as_of`、`mode=latest_only`、窗口）在实现里集中定义一处。
