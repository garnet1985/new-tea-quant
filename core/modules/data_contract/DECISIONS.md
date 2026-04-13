# Data Contract：Issue / 缓存 / 参数（设计决议）

本文档记录 **对外 API 与缓存语义** 的已定决议，实现以 `DataContractManager` 与 `ContractIssuer` 为准；与 `CONCEPTS.md` 中历史叙事冲突时，**以本文为准**。

---

## 1. 单一对外入口：`issue`

- 应用层（Strategy、Tag 等）以 **`DataContractManager.issue(...)`** 为主入口，得到 **`DataContract`**。
- **是否命中进程内缓存**由 DCM 内部决定，**调用方无感**。
- 不再对外提供可塞任意键值的 **`context`**；必要维度用 **显式命名参数**（见下节）。

---

## 2. `issue` 参数形态（Python）

```text
issue(
    data_id: DataKey,
    *,
    entity_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    **params,
) -> DataContract
```

- **`*`（keyword-only）**：`data_id` 之后参数须带参数名调用，避免顺序传错。
- **`**params`**：仅允许 **各 `DataKey` 在 mapping/文档中声明的 loader 参数**（如 `filtered`、`adjust`）；实现可对未知键 **报错**（推荐），避免缓存键空间被污染。

| 参数 | 含义 |
|------|------|
| `data_id` | 必选，选哪条 mapping。 |
| `entity_id` | 当 mapping 为 **`ContractScope.PER_ENTITY`** 时 **必填**（非空）；表示实体（如股票代码），**不是**用户自定义业务上下文。 |
| `start` / `end` | 仅对 **时序** 有意义；**非时序**不要求。 |
| `params` | 该 key 允许的 loader 覆盖参数。 |

---

## 3. 时间与校验

- **非时序**：不要求 `start`/`end`；内部用固定占位参与 cache key（调用方不传）。
- **时序**：
  - **可以不传** `start`/`end`：语义为 **全量/全历史**（具体边界以 loader 为准）；cache key 用内部 **全量窗口标记**（如 `__full__`），与「区间请求」区分。
  - **区间请求**：传 `start`/`end`；**建议约定**：要么都传要么都不传；只传一个 → `ValueError`（避免半开区间歧义）。

---

## 4. `DataContract` 返回时是否已带 `data`

| mapping 典型情况 | `issue` 返回的 contract |
|------------------|-------------------------|
| **可缓存的 GLOBAL**（非时序 → 全局层；时序 GLOBAL → per-run 层，见 policy） | **已物化**：`data` 已填（来自缓存或本次 loader）。 |
| **`PER_ENTITY`（及 policy 为 NONE 的项）** | **未物化**：不走路径缓存，`data` 为空，需再 **`load(start=..., end=...)`**（与现 loader 一致）。 |

原则：**只有 mapping 里「全局可共享」的那类数据在 `issue` 时即物化**；按票/按实体的大表不在 issue 时预填。

---

## 5. 缓存与清理职责

- DCM 持有 **`ContractCacheManager`**：两层（**global** / **per-run**）仅表示 **存储分桶**；**何时清空 per-run**、**何时清 global** 由 **应用编排**（Strategy、Tag 等）在合适边界调用 **公开清理方法**（如 `clear_run` / `clear_global` / `clear_all`），**contract 包不绑定「策略 run」等业务词**。
- Tag 与 Strategy **用法统一**：同一套 `issue` + 同一套清理 API；差异只在谁、何时调清理。

---

## 6. 禁止「用户自定义 context」

- **不**提供开放式 `Mapping` 供用户塞业务字段，以免 cache key 混乱、误命中或信息扩散。
- 必要信息 **显式、可枚举**（如 `entity_id` + 各 key 的 `params` allowlist）。

---

## 7. 与旧 API 的关系

- **`load_contract_data`**：已移除；统一为 **`issue`**（可缓存 GLOBAL 直接得到 `contract.data`；`PER_ENTITY` 再 `load`）。

---

## 8. 修订记录

- 初稿：统一 `issue`、显式 `entity_id`、时序时间窗与全量语义、缓存与清理边界、禁止自由 context。
