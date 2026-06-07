# Data Contract：设计决策（issue / 缓存 / 参数）

**版本：** `0.3.3`（决策 1–7、8–10：**已实现**；决策 11：**Strategy 枚举已实现**，Tag 旁路清理待做）

本文档记录 **对外 API 与缓存语义** 的已定决议，实现以 `DataContractManager` 与 `ContractIssuer` 为准；与泛化概念叙述冲突时，**以本文与代码为准**。

> **0.3.0 说明：** 决策 8–11 扩展 **PER_ENTITY plural issue / load_batch**，不改变 GLOBAL singleton 语义。落地顺序见 [`ROADMAP.md`](ROADMAP.md)。

---

## 决策 1：单一对外入口 `issue`

**背景（Context）**  
Strategy、Tag 等需要统一方式获取「数据句柄」并可选命中缓存。

**决策（Decision）**  
应用层以 **`DataContractManager.issue(...)`** 为主入口，得到 **`DataContract`**。是否命中进程内缓存由 DCM 内部决定，调用方不区分缓存分支。

**理由（Rationale）**  
避免重复暴露 `load_contract_data` 等多入口；缓存细节集中在 DCM。

**影响（Consequences）**  
所有扩展仍通过 `DataKey` + mapping 表达，不通过旁路 API 注入任意缓存键。

---

## 决策 2：`issue` 参数形态

**背景（Context）**  
需要显式维度，避免开放式 `context` 污染缓存键空间。

**决策（Decision）**  
签名形如：

```text
issue(
    data_id: DataKey,
    *,
    entity_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    **override_params,
) -> DataContract
```

- `data_id` 之后为 **keyword-only**。
- **`override_params`** 仅应为各 `DataKey` 在 mapping 中声明的 **loader 参数**（如 `adjust`、`term`、`filtered`）；实现侧可对未知键报错（推荐）。

**理由（Rationale）**  
`entity_id` 表示实体分片，**不是**自由业务上下文；时间与覆盖参数可枚举、可序列化进缓存键。

**影响（Consequences）**  
禁止「用户自定义 context 大字典」式扩展。

---

## 决策 3：时间与校验

**背景（Context）**  
时序与非时序对 `start`/`end` 要求不同。

**决策（Decision）**  
- **非时序**：不要求 `start`/`end`；内部用固定占位参与 cache key。  
- **时序**：可同时省略 `start`/`end`（语义为 **全量/全历史**，与「区间请求」区分）；若传则 **必须成对**，否则 **`ValueError`**。

**理由（Rationale）**  
避免半开区间与单侧参数歧义。

**影响（Consequences）**  
调用方须遵守「双传或双不传」。

---

## 决策 4：`issue` 返回时是否已带 `data`

**背景（Context）**  
GLOBAL 可共享数据适合预物化；按实体的大表不适合在 `issue` 时默认拉满。

**决策（Decision）**  

| 典型 mapping | `issue` 返回 |
| --- | --- |
| 可缓存的 GLOBAL（非时序在 GLOBAL 层；GLOBAL 时序在 PER_STRATEGY 层） | 命中缓存或本次 loader 后 **`data` 已填充** |
| `PER_ENTITY` 及 policy 为 `NONE` 的项 | **未物化**，`data` 为空，需 **`load(...)`** |

**理由（Rationale）**  
内存与语义：只有「全局可共享」类数据在 `issue` 时即物化。

**影响（Consequences）**  
调用方对 `PER_ENTITY` 必须再 `load`（或依赖 DCM 在可缓存路径写回 `data` 的规则）。

---

## 决策 5：缓存与清理职责

**背景（Context）**  
多进程与多策略 run 需要可预测的缓存边界。

**决策（Decision）**  
`ContractCacheManager` 持有 **global** / **per-strategy** 分桶；**何时** `enter_strategy_run` / `exit_strategy_run` / `clear_global` / `clear_all` 由 **应用编排**（Strategy、Tag 等）决定，**contract 包不绑定具体业务词**。

**理由（Rationale）**  
Tag 与 Strategy 使用同一套 API，差异仅在调用时机。

**影响（Consequences）**  
遗漏清理可能导致 per-strategy 层陈旧数据残留。

---

## 决策 6：禁止开放式用户 context

**背景（Context）**  
自由 `Mapping` 会导致缓存键不可控、误命中。

**决策（Decision）**  
不提供可塞任意键值的开放式 context；必要信息通过 **`entity_id`** 与各 key 允许的 **`override_params`** 传递。

**理由（Rationale）**  
显式、可枚举、可哈希。

**影响（Consequences）**  
扩展需求应通过新 **`DataKey`** 或文档化的新 **params** 完成。

---

## 决策 7：旧 API

**背景（Context）**  
历史上可能存在独立 `load_contract_data` 类入口。

**决策（Decision）**  
统一为 **`issue`**（可缓存 GLOBAL 可直接得到 `contract.data`；`PER_ENTITY` 再 **`load`**）。

**理由（Rationale）**  
单一心智模型。

**影响（Consequences）**  
迁移代码时删除对旧入口的依赖。

---

## 决策 8：PER_ENTITY 统一 plural（`entity_ids` → `by_entity`）

**状态：** 已定稿并实现（0.3.0）

**决策（Decision）**  
- **`ContractScope.PER_ENTITY`**：`issue` 的 canonical 输入为 **`entity_ids: Sequence[str]`**（非空）；仅一股时亦为 **`entity_ids=["A"]`**，不在 DCM 内保留单独的 single 加载路径。
- **语法糖**：允许 **`entity_id="A"`**，实现侧规范化为 **`entity_ids=["A"]`**，便于调用方迁移。
- **`entity_id` 与 `entity_ids` 互斥**；同时传入 → **`ValueError`**。
- **`ContractScope.GLOBAL`**：**不变**，不要求 `entity_ids`；误传 entity 维度在 DCM 内忽略（与现行为一致）。

**理由（Rationale）**  
一股与多股共用一条 PER_ENTITY 管线，batch 只是 `len(entity_ids) > 1` 的特例；避免 single/batch 两套返回类型。

**影响（Consequences）**  
现有只传 `entity_id` 的调用方需逐步改为 `entity_ids` 或继续用糖；Strategy / Tag 的 hydrate 逻辑以 map 为主键取 contract。

---

## 决策 9：单一 `issue` 入口与 `IssueResult` 信封

**状态：** 已定稿并实现（0.3.0）

**决策（Decision）**  
仍只暴露 **`DataContractManager.issue(...)`** 一个入口；返回值统一为 **`IssueResult`**：

| `spec.scope` | `IssueResult` 字段 |
| --- | --- |
| `GLOBAL` | **`contract: DataContract`**（含 `meta` + 物化后的 `data`，规则同决策 4） |
| `PER_ENTITY` | **`by_entity: Mapping[str, DataContract]`**（键为 `entity_id`；每个句柄含该 entity 的 `meta` 与 `data`） |

辅助方法（推荐）：**`entity_count`**、**`entity(entity_id)`**、**`require_one()`**（恰有一个 entity 时）。

**理由（Rationale）**  
GLOBAL 为 singleton、PER_ENTITY 为 map，与「有无 entity 维度」一致；调用方不必 `if is_batch`。

**影响（Consequences）**  
当前返回裸 **`DataContract`** 的 API 在 0.3.0 中 breaking change；迁移期可在 wrapper 或适配层提供 `.contract` / `.require_one()` 兼容。

---

## 决策 10：`load_batch` 优先，无则循环 `load`

**状态：** 已定稿并实现（0.3.0）

**决策（Decision）**  
- mapping 仍只有 **`loader: Type[BaseLoader]`** 一个字段。
- **`BaseLoader`** 增加可选 **`load_batch(entity_ids, params, context) -> Mapping[str, Any]`**（键为 entity_id，值为该 entity 的 raw rows / payload）。
- **默认实现**：对每个 `entity_id` 调用现有 **`load(...)`**（context 注入该 id），组装 map。
- **DCM 在 PER_ENTITY 物化时**：若 loader **override 了 `load_batch`**（相对默认实现），则 **优先 `load_batch`**；否则走默认 fallback（等价于循环 `load`）。
- Loader **内部** 调用 `DataManager` 的 bulk API（如 `kline_service.load_batch`）；**Strategy / Tag 不得**对已声明的 `DataKey` 直调 DataManager。

**理由（Rationale）**  
load 逻辑仍只写在一处（loader）；有无 batch IO 优化对 DCM 透明。

**影响（Consequences）**  
未实现 `load_batch` 的 loader 行为与 today 一致（N 次 IO）；实现后自动获得 batch 路径，无需改 mapping 结构。

---

## 决策 11：应用层不得绕过 contract 加载**已声明**数据

**状态：** Strategy 枚举路径 **已实现**（0.3.0）；Tag `tag_batch_stage` 等待对称改造

**背景（Context）**  
Tag `tag_batch_stage`、Strategy 历史 `_preloaded_klines` 等路径直调 `DataManager`，削弱「声明 → loader 自动注入」模型。同时，回测编排（股票池、日历、元数据）若强行全部 contract 化，会混淆「用户声明的数据依赖」与「引擎基础设施」。

**决策（Decision）**  

### 范围（什么走 contract）

仅 **用户在 settings / scenario 中显式声明** 的 `DataKey` 必须经 contract 注入：

| 来源 | 字段 |
| --- | --- |
| Strategy | `data.base_required_data` + `data.extra_required_data_sources` |
| Tag | scenario `data.required`（及等价 extras） |

对上述声明：

1. **只** 解析声明项；
2. **只** 通过 **`DataContractManager.issue`**（多 entity job 传 `entity_ids`）获取 **`IssueResult`**；
3. **只** 从 **`IssueResult.by_entity`** 或 **`IssueResult.contract`** 装填 `DataCursor` / worker inject。

禁止：对**同一已声明** `DataKey` 在 worker / stager 内再写 **`DataManager.*.load_*`** 旁路（实验脚本与 **loader 实现内部** 除外）。

### 范围外（回测器 / 编排自行 DataManager）

**未**出现在上述声明中的数据，**不**强制 contract；引擎可直接 `DataManager` 或表服务，例如：

| 用途 | 典型 API | 说明 |
| --- | --- | --- |
| 回测 **universe / 股票池** | `stock.list.load(period_start=…)` | 由 `sampling` + 日历解析，**不是**默认 contract 注入 |
| 单票 **元数据**（name、行业等） | `stock.list.load_meta` / `load_single` | 展示与风控上下文，非策略 `data` 声明 |
| **交易日历**、最新已完成交易日 | `CalendarService`、`resolve_latest_completed_trading_date` | 编排基础设施 |
| K 线 **锚点日**（scanner 等） | `kline.load_latest_date`、按日查表 | 未声明时由引擎解决 |
| DbCache、workbench、输出 retention | 各 output / cache 表 | 与策略输入数据无关 |

若用户 **将来** 在 `extra_required_data_sources` 中声明 `stock.list`（或其它 `DataKey`），则该 key **纳入** contract 范围，仍不得旁路。

**理由（Rationale）**  
Contract 回答的是：「策略逻辑需要哪些数据、如何自动注入 Cursor」。股票池与日历回答的是：「这次回测跑哪些票、在什么时间窗」——职责分离，避免把编排层绑进 mapping。

**影响（Consequences）**  
- Strategy：`StrategyDataInjectionService` / `StrategyJobContractBatch` 仅消费 `required_data_sources`；`_load_stock_info`、`resolve_backtest_universe` 等保持直调。  
- Tag：见 [`ROADMAP.md`](ROADMAP.md) 步骤 4 剩余项。  
- 文档与代码审查：新增 `DataKey` 时先问「是否 settings 声明项」再决定走 inject 还是 orchestrator。
