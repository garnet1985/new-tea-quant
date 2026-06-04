# Data Contract 演进路线（PER_ENTITY batch）

**版本：** `0.3.0`（contract + Strategy 枚举：**已实现**；Tag 对称改造：**待做**）

本文档记录 **PER_ENTITY 批量签发 / 加载** 的落地顺序，与 [`DECISIONS.md`](DECISIONS.md) 决策 8–11 配套。

---

## 目标

- **加强**现有 contract 设计：用户在 settings 中**声明**的数据 → `issue` → loader → 注入；**未声明**的编排数据（股票池、日历、元数据）由回测器直调 `DataManager`（见决策 11）。
- **PER_ENTITY** 统一 plural 语义（`entity_ids` → `by_entity` map）；**GLOBAL** 保持 singleton。
- Strategy / Tag 对**已声明** `DataKey` 只经 DCM 取数；删除 bulk stage 等旁路。

---

## 阶段

### 1. 记录 contract 改动（文档）

| 状态 | 内容 |
| --- | --- |
| ✅ | [`DECISIONS.md`](DECISIONS.md) 决策 8–11 |
| ✅ | [`DESIGN.md`](DESIGN.md) / [`API.md`](API.md) / [`CONCEPTS.md`](CONCEPTS.md) / [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| ✅ | 本文档 |

**产出：** 团队对 `IssueResult`、`entity_ids`、`load_batch` fallback 口径一致。

---

### 2. 实验：batch load 是否更有效率

| 状态 | 内容 |
| --- | --- |
| ✅ | [`experiments/kline_batch_io/`](../../experiments/kline_batch_io/) + [`REPORT.md`](../../experiments/kline_batch_io/REPORT.md) |

**结论：** N≥10 时 raw batch 明显省时；全链路需 **batch adj + merge** 才有 ~12–15% 收益；生产 enum 在 load 占主导时收益更大（实测 1000 股 wall ~6.8s→~4.2s）。

---

### 3. 改造 contract

| 状态 | 内容 |
| --- | --- |
| ✅ | `IssueResult` + `DataContractManager.issue(entity_ids=…)` |
| ✅ | `BaseLoader.load_batch` + 默认 fallback |
| ✅ | `StockKlineLoader.load_batch` → optimized `kline_service.load_batch` |
| ✅ | 单测 + smoke |

**可延后：**

- 其它 PER_ENTITY loader 的 `load_batch`（未声明则与 Strategy 无关）
- PER_ENTITY 缓存策略变更

---

### 4. 改造 Strategy / Tag：声明驱动、经 contract 注入

**原则（决策 11）：** 仅 **`settings.data` 声明项** 走 contract；股票池 / 元数据 / 日历等 **不在声明内** 时回测器可直调。

| 状态 | Strategy | Tag |
| --- | --- | --- |
| 声明 → `issue` → inject | ✅ `StrategyDataInjectionService`、`StrategyJobContractBatch`、`run_enumeration_payload` | ⏳ `tag_batch_stage` 等待对称 |
| 多股 job batch issue | ✅ | ⏳ |
| 删除 K 线旁路 | ✅ `_preloaded_klines` / `preload_klines` 已移除 | ⏳ |
| 编排层直调（universe、meta） | ✅ 保持 `stock.list` 等，**不**默认 contract | — |

**Strategy 已落地：**

- `hydrate_row_slots` / job 级 `StrategyJobContractBatch.hydrate` 只消费 `required_data_sources`
- `_load_stock_info`、`resolve_backtest_universe` 等 **刻意** 不在 contract 范围（除非用户把 `stock.list` 写进 extras）

**Tag 剩余：**

- `tag_batch_stage` → DCM `issue(..., entity_ids=...)`
- `TagDataManager` 与 Strategy 对称

**产出：** userspace 新增**可声明** `DataKey` + loader 后，Strategy **inject 层**无需再改 load 代码。

---

## 依赖关系

```mermaid
flowchart LR
  S1[1 文档] --> S2[2 实验]
  S2 --> S3[3 contract 实现]
  S3 --> S4[4 Strategy / Tag]
  S4 --> S4b[4b Tag 对称]
```

---

## 相关文档

- [DECISIONS.md](DECISIONS.md)
- [DESIGN.md](DESIGN.md)
- [API.md](API.md)
