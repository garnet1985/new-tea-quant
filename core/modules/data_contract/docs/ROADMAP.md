# Data Contract 演进路线

**版本：** `0.5.0`（Facade 黑盒 cache + 下游迁移：**已实现**）

本文档记录 **PER_ENTITY batch** 与 **缓存演进** 的落地顺序，与 [`DECISIONS.md`](DECISIONS.md) 配套。

---

## 目标

- 用户在 settings 中**声明**的数据 → `DataContracts.issue` → loader → 注入；**未声明**的编排数据（股票池、日历、元数据）由回测器直调 `DataManager`（见决策 11）。
- **PER_ENTITY** 统一 plural 语义（`entity_ids` → `by_entity` map）；**GLOBAL** 保持 singleton。
- **GLOBAL** 进程内 cache 对调用方黑盒；**PER_ENTITY** 当前不 cache（见决策 12–13）。

---

## 阶段

### 1. 记录 contract 改动（文档）

| 状态 | 内容 |
| --- | --- |
| ✅ | [`DECISIONS.md`](DECISIONS.md) 决策 8–11 |
| ✅ | [`DESIGN.md`](DESIGN.md) / [`CONCEPTS.md`](CONCEPTS.md) / [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| ✅ | 公开 API 契约 [`api.yaml`](../api.yaml)（已删除 `docs/API.md`） |
| ✅ | 本文档 |

---

### 2. 实验：batch load 是否更有效率

| 状态 | 内容 |
| --- | --- |
| ✅ | [`experiments/kline_batch_io/`](../../experiments/kline_batch_io/) + [`REPORT.md`](../../experiments/kline_batch_io/REPORT.md) |

**结论：** N≥10 时 raw batch 明显省时；全链路需 **batch adj + merge** 才有 ~12–15% 收益。

---

### 3. 改造 contract（0.3.x–0.4.x）

| 状态 | 内容 |
| --- | --- |
| ✅ | `IssueResult` + `issue(entity_ids=…)` |
| ✅ | `BaseLoader.load_batch` + 默认 fallback |
| ✅ | `StockKlineLoader.load_batch` |
| ✅ | `core/` 五层 + `DataContracts` Facade |

---

### 4. 改造 Strategy / Tag：声明驱动、经 contract 注入

| 状态 | Strategy | Tag |
| --- | --- | --- |
| 声明 → `issue` → inject | ✅ | ✅ |
| 多股 job batch issue | ✅ | ✅ |
| 去掉 `ContractCacheManager` 注入 | ✅ | ✅ |
| run 边界 `shared_cache()` | ✅ | ✅ |

---

### 5. Facade 黑盒 cache（0.5.0）

| 状态 | 内容 |
| --- | --- |
| ✅ | `DataContracts(cache_enabled=True)` 默认 GLOBAL cache |
| ✅ | PER_ENTITY 静默不 cache；显式 cache override → `ValueError` |
| ✅ | `issue` / `load` 拆分、`should_load_initially`、`until` 上 Facade |
| ✅ | `contracts.py` 仅导出类/枚举 |

---

### 6. PER_ENTITY DataFrame + Parquet 缓存（未来）

| 状态 | 内容 |
| --- | --- |
| ⏳ | Loader / 句柄 payload 支持 **`pandas.DataFrame`**（与时序 list 语义对齐） |
| ⏳ | 按 `(data_key, entity_id, window, params)` 写 **Parquet** 片段，job / run 内复用 |
| ⏳ | Facade `load` / `until` / `row_count` 对 DataFrame 与 list 等价行为 |
| ⏳ | 与 GLOBAL memory cache、跨进程 `global_data` preload **正交** |

**动机：** 大规模 PER_ENTITY 枚举时，内存 list-of-dict 与重复 IO 成本高；Parquet 便于同机多 run 调试与二次加载。用户仍不可配置 PER_ENTITY cache 开关（黑盒策略）。

**产出：** 见 [`TODO.md`](../TODO.md)「PER_ENTITY DataFrame + Parquet 缓存」验收项。

---

## 依赖关系

```mermaid
flowchart LR
  S1[1 文档] --> S2[2 实验]
  S2 --> S3[3 contract 实现]
  S3 --> S4[4 Strategy / Tag]
  S4 --> S5[5 黑盒 cache 0.5.0]
  S5 --> S6[6 DataFrame Parquet]
```

---

## 相关文档

- [DECISIONS.md](DECISIONS.md)
- [DESIGN.md](DESIGN.md)
- [api.yaml](../api.yaml)
- [TODO.md](../TODO.md)
