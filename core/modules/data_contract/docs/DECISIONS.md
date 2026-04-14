# Data Contract：设计决策（issue / 缓存 / 参数）

**版本：** `0.2.0`

本文档记录 **对外 API 与缓存语义** 的已定决议，实现以 `DataContractManager` 与 `ContractIssuer` 为准；与泛化概念叙述冲突时，**以本文与代码为准**。

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
