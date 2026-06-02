# Tag 设计决策

**版本：** `0.2.0`

---

## 决策 3：主进程 batch stage IO（待集成，先跑通再优化）

**背景（Context）**  
Tag 已切到 **JobDispatcher + inject/report**：主进程 `on_stage_job` 每股执行 `hydrate_row_slots`（kline）+ `fetch_prior_tag_values`（prior 点查）。profile 与专用 benchmark 表明 **stage 读库是主要瓶颈**（全量 ~47s / ~60s wall），而非 checkpoint、pickle 或子进程计算。

**决策（Decision）**  
**暂不实现**；pipeline 稳定后再做 **主进程 bulk SQL stage**：

1. kline：`DataManager.stock.kline.load_batch(entity_ids, ...)`（`IN` 一次查多股）  
2. prior：`fetch_prior_tag_values_batch`（每 chunk 一次 window SQL，已实现于 `tag_prior_values.py`，TagJobStager 尚未接入）  
3. 按 chunk（建议 **20–100 股**）预取后，仍 **每股一个 job / 一份 inject payload** 交给 worker（不是把多股合并进单个 worker job）  
4. 配置入口预留：`settings.performance.stage_batch_size` 或与 `DispatchConfig.chunk_size` 对齐  

**理由（Rationale）**  
Benchmark 工具 `python -m core.modules.tag.tools.tag_read_benchmark`（100 股、activity-ratio20 窗口）实测 **仅当 batch 真正减少 SQL 次数** 才有收益；「多股同 task 但每股仍单独查库」无意义。

| 引擎 | point_io | batch_io（chunk） | batch/point |
|------|----------|-------------------|-------------|
| MySQL | ~0.73–0.80s | chunk=100 | **~0.78x（~22%）** |
| DuckDB | ~0.64s | chunk=100 | **~0.55x（~45%）** |

- checkpoint（`get_tag_value_last_update_info`）整场景 **~0.5s（MySQL）/ ~0.005s（DuckDB）**，非 per-job 热点  
- per-entity 读：kline **~80%**，prior **~20%**  
- chunk=5 收益过小；chunk≥20 后收益明显，DuckDB 上 batch 边际大于 MySQL  
- 多进程并行读库 **不采用**（spawn + 多连接；DuckDB WAL 风险；实测不比主进程串行快）  
- spill / 向量计算 **优先级低于 batch stage**（profile 与 benchmark 未支持）  

**明确不做（本优化点内）**  
- 仅合并 job 粒度而不合并 SQL  
- worker 内多股共读（除非 stage 已 bulk 预取并拆分 inject）  
- 为 batch stage 提前上 spill  

**影响（Consequences）**  
集成时需改 `TagJobStager`（或上层 bulk prefetch + 按 entity 组装 `_inject`），并补测试；全量回填 stage 可望缩短 **~20%（MySQL）～ ~45%（DuckDB）**；日常增量（~13s）收益较小。  

**验收（将来）**  
- `tag_read_benchmark` 在目标 chunk 下 batch/point **≤ 0.8x**（MySQL）  
- 全量 Tag profile 中 `stage(on_stage_job)` 相对 baseline 下降  
- DuckDB 跑 benchmark / Tag 后无 WAL 回归（仍单进程 stage）  

---

## 决策 1：实体型（`entity_based`）与通用型（`general`）标签目标

**背景（Context）**  
标签既需要按股票等实体逐只计算，也需要少量不绑定单实体的全局结果；配置层需可扩展且类型安全。

**决策（Decision）**  
引入 **`TagTargetType`**：**`ENTITY_BASED`** 与 **`GENERAL`**，由 **`ScenarioModel`** 与 Job 构建逻辑区分执行路径。

**理由（Rationale）**  
实体型与全局型的数据准备、并行粒度不同，显式分类避免隐式约定导致错误分片或空跑。

**影响（Consequences）**  
新增场景类型时需正确设置 target 类型，并与 **`TagManager`** 的实体列表解析保持一致。

---

## 决策 2：横截面（cross-sectional）类能力暂不纳入框架核心

**背景（Context）**  
全市场同一日截面上的排名、分位等依赖「当日多实体联合」视图，与当前「单实体 + as_of 历史切片」模型不同。

**决策（Decision）**  
不在本模块核心路径提供一等公民的 cross-sectional API；需要时由用户在 **`calculate_tag`** 内自行组合查询或缓存。

**理由（Rationale）**  
避免在 DataCursor 语义上叠加模糊的「全市场快照」契约，降低一致性与性能风险。

**影响（Consequences）**  
复杂横截面标签需更多自定义代码或预计算中间表；未来若引入需单独设计与 **`DECISIONS`** 增补。

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DESIGN.md](DESIGN.md)
- [API.md](API.md)
