# Data Contract 设计说明

**版本：** `0.5.0`（0.3.0 **IssueResult / load_batch**；0.5.0 **Facade 黑盒 cache** — **已实现**）

本文档描述 **`DataSpec` 字段**、**core 默认路由表摘要**、**缓存策略**、**userspace 合并**及 **Tag 专用 `DataKey.TAG`**。实现以 `mapping.py`、`data_contract_manager.py`、`cache/policy.py`、`discovery.py` 为准。

**相关文档**：[架构总览](./ARCHITECTURE.md) · [演进路线](./ROADMAP.md)

---

## `DataSpec`（`TypedDict`，字段均可选）

| 字段 | 含义 |
| --- | --- |
| `scope` | `ContractScope.GLOBAL` 或 `PER_ENTITY`。 |
| `type` | `ContractType.TIME_SERIES` 或 `NON_TIME_SERIES`。 |
| `unique_keys` | `validate_raw` 时要求行记录上存在的列（轻量校验）。 |
| `time_axis_field` / `time_axis_format` | 时序模板使用（如 `date` + `YYYYMMDD`，或 `quarter` + `YYYYQ`）。 |
| `loader` | `BaseLoader` 子类（非实例）；可选 override **`load_batch`**，见下文。 |
| `list_data_key` | **`scope=per_entity` 必填**：所属实体 GLOBAL list 的 `DataKey`（如 `stock.list` / `index.list`）。Tag / 策略据此解析实体池。 |
| `display_name` | 展示用名称。 |
| `defaults` | 与 `issue(..., **override_params)` 合并为 `loader_params`，后者覆盖前者。 |

---

## Core `default_map` 摘要

| `DataKey` | scope | type | 说明（loader） |
| --- | --- | --- | --- |
| `STOCK_LIST` | GLOBAL | 非时序 | 股票列表 |
| `STOCK_KLINE_DAILY` | PER_ENTITY | 时序 | 股票日 K（`adjust` 等由 params） |
| `STOCK_KLINE_WEEKLY` | PER_ENTITY | 时序 | 股票周 K |
| `STOCK_KLINE_MONTHLY` | PER_ENTITY | 时序 | 股票月 K |
| `TAG` | PER_ENTITY | 时序 | 标签值（scenario 等由 params / loader） |
| `STOCK_CORPORATE_FINANCE` | PER_ENTITY | 时序 | 财报季频 |
| `STOCK_ADJ_FACTOR_EVENTS` | PER_ENTITY | 时序 | 复权事件 |
| `INDEX_LIST` | GLOBAL | 非时序 | 指数列表 |
| `INDEX_KLINE_DAILY` | PER_ENTITY | 时序 | 指数日线 |
| `INDEX_WEIGHT_DAILY` | PER_ENTITY | 时序 | 指数权重 |
| `MACRO_*` | GLOBAL | 时序 | 宏观序列（GDP/LPR/CPI/PPI/PMI） |

完整默认值与字段以 `mapping.py` 为准。

---

## `issue` 与时间窗

- **非时序**：`start`/`end` 不参与业务语义；DCM 内部用占位窗口参与 cache key（见 `DataContractManager._effective_load_window`）。
- **时序**：须 **同时提供** `start` 与 `end`，或 **同时省略**（省略表示 **全量语义**，内部用 `__full__` 标记参与缓存键）。只传其一 → **`ValueError`**。
- **PER_ENTITY（0.3.0）**：须 **`entity_ids`**（非空序列）；**`entity_id="A"`** 糖化为 **`["A"]`**。返回 **`IssueResult.by_entity`**，见 [`DECISIONS.md`](DECISIONS.md) 决策 8–9。
- **GLOBAL**：不要求 entity 维度；误传 `entity_id` / `entity_ids` 在 DCM 内忽略以免污染缓存键。

---

## PER_ENTITY plural 与 `load_batch`（0.3.0）

### 签发与返回

```text
issue(STOCK_KLINE_DAILY, entity_ids=[A, B, C], start=..., end=..., **params)
  → IssueResult(by_entity={
        A: DataContract(meta=..., data=rows_A),
        B: DataContract(...),
        C: DataContract(...),
    })
```

一股：`entity_ids=[A]`，`by_entity` 仅一个键。

GLOBAL 不变：

```text
issue(STOCK_LIST) → IssueResult(contract=DataContract(...))
```

### Loader 双路径（同一类）

```text
load_batch(entity_ids, params, context)
  ├─ override 且可 bulk IO → 一次取数，返回 {entity_id: raw}
  └─ 默认实现 → for id in entity_ids: load(..., context 含 id)
```

DCM **优先** loader 的 **`load_batch`**（相对 `BaseLoader` 默认实现）；无优化实现时自动 fallback，语义与循环 **`load`** 一致。

### PIT 游标（`until`）

时序契约在 **`BaseTimeSeriesContract`** 内维护每 entity 的 **`CursorState`**；**`contract.until(as_of)`** 累进推进前缀。多 entity 数据按 scope 组织；Strategy / Tag 在 as_of 日调用 `until` 取可见前缀。

---

## 缓存范围（`resolve_cache_scope`）

| mapping 条件 | `ContractCacheScope` |
| --- | --- |
| GLOBAL + 非时序 | `GLOBAL`（进程级共享 store） |
| GLOBAL + 时序 | `PER_STRATEGY`（单次策略 run 内共享，随 `enter/exit_strategy_run` 清理） |
| 其他（含全部 PER_ENTITY） | `NONE`（不写缓存；`issue` 仅装配句柄，数据依赖 `load`） |

`DataContractManager.issue`：若 scope 为 NONE，直接 **`issuer.issue`**；若为 GLOBAL/PER_STRATEGY，则按 sha256 键尝试 **get → 命中则克隆 data 到 contract**；未命中则 **`contract.load(start=eff_start, end=eff_end)`** 后 **put** 再返回。

---

## Userspace 合并

- 文件：`userspace/data_contract/mapping.py`（路径由 `PathManager.data_contract_mapping()` 解析）。
- 导出变量名（优先级）：`custom_map` → `default_map` → `DATA_CONTRACT_MAP`。
- 键：**`DataKey` 实例或与已有枚举值相同的 `str`**（通过 `DataKey(key)` 构造）；须与 **core 已定义的 `DataKey` 成员**一致，**不得与 core 已有键重复**（重复 → `ValueError`）。
- 新增「全新」业务 id 需要先在 **`contract_const.DataKey`** 中增加枚举成员（core 变更），再在 userspace 提供对应 `DataSpec`。

---

## `DataKey.TAG`（标签）

映射为 **PER_ENTITY + TIME_SERIES**，时间轴字段 **`as_of_date`**；具体场景（scenario）由 **`TagLoader`** 与 `loader_params`（如 `tag_scenario` / `scenario_id`）解析，与标签元数据一致。

---

## 相关文档

- [api.yaml](../api.yaml)
- [DECISIONS.md](DECISIONS.md)
- [ROADMAP.md](ROADMAP.md)

---

## 设计决策（原 DECISIONS.md）

# Data Contract：设计决策（issue / 缓存 / 参数）

**版本：** `0.5.0`（决策 1–7、8–10、12–13：**已实现**；决策 11 Strategy/Tag **已实现**；决策 14：**未来**）

本文档记录 **对外 API 与缓存语义** 的已定决议，实现以 **`DataContracts`** Facade 与 `DataContractManager` 为准；与泛化概念叙述冲突时，**以本文、[`api.yaml`](../api.yaml) 与代码为准**。

> **0.3.0 说明：** 决策 8–11 扩展 **PER_ENTITY plural issue / load_batch**，不改变 GLOBAL singleton 语义。落地顺序见 [`ROADMAP.md`](ROADMAP.md)。

---

## 决策 1：单一对外入口 `issue`

**背景（Context）**  
Strategy、Tag 等需要统一方式获取「数据句柄」并可选命中缓存。

**决策（Decision）**  
应用层以 **`DataContracts.issue(...)`** 为主入口（内部 `DataContractManager`），得到 **`IssueResult`** / **`DataContract`**。是否命中进程内 **GLOBAL** 缓存由 Facade **黑盒**决定，调用方不注入 `ContractCacheManager`、不区分缓存分支。

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

| 典型 mapping | `issue(should_load_initially=True)` 返回 |
| --- | --- |
| 可缓存的 **GLOBAL** | 命中 cache 或本次 loader 后 **`data` 已填充** |
| **PER_ENTITY** | 默认 **已 load**（经 `load_batch`）；`should_load_initially=False` 时 **`data` 为空**，须 **`DataContracts.load(issued)`** |

**PER_ENTITY 不参与进程内 cache**（见决策 12）。

**理由（Rationale）**  
内存与语义：只有「全局可共享」类数据在 `issue` 时即物化。

**影响（Consequences）**  
调用方对 `PER_ENTITY` 必须再 `load`（或依赖 DCM 在可缓存路径写回 `data` 的规则）。

---

## 决策 5：缓存与清理职责

**背景（Context）**  
多进程与多策略 run 需要可预测的缓存边界。

**决策（Decision）**  
进程内 store 由 **`DataContracts.shared_cache()`**（lazy 单例 `ContractCacheManager`）持有 **global** / **per-strategy** 分桶。**何时** `enter_strategy_run` / `exit_strategy_run` / `clear_all` 由 **应用编排**（Strategy、Tag 等）在 run 边界调用；**不可**在构造 Facade 时注入 manager。

**理由（Rationale）**  
统一 API：`DataContracts()` 即可；Tag 与 Strategy 差异仅在 run 边界清理时机。

**影响（Consequences）**  
遗漏 `exit_strategy_run` 可能导致 per-strategy 层陈旧数据；spawn 子进程 **不继承** store（跨进程仍靠 `global_data` preload）。

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

**状态：** Strategy / Tag **已实现**（0.5.0）

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
2. **只** 通过 **`ContractIssuer.issue`**（多 entity job 传 `entity_ids`）获取契约句柄；
3. **只** 从签发句柄取数 / `until`，再注入 worker。

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
- Tag：`tag_batch_stage` / `TagDataManager` 与 Strategy 对称。  
- 文档与代码审查：新增 `DataKey` 时先问「是否 settings 声明项」再决定走 inject 还是 orchestrator。

---

## 决策 12：GLOBAL 黑盒 cache，PER_ENTITY 永不 cache

**状态：** 已实现（0.5.0）

**决策（Decision）**  

- **`DataContracts(cache_enabled=True)`**（默认）：**GLOBAL** 按 mapping policy 使用进程内 cache；**PER_ENTITY** 内部 **不 cache**（静默，每次 loader IO）。
- **不可注入** `ContractCacheManager`；高级场景仅通过 **`DataContracts.shared_cache()`** 做 run 边界清理。
- 用户在 `override_params` 中显式传 `cache` / `use_cache` 等且 data_key 为 **PER_ENTITY** → **`ValueError`**。
- **`info(data_key).has_cache`**：仅 GLOBAL 且 `cache_enabled=True` 时为 true。

**理由（Rationale）**  
PER_ENTITY 大表不适合默认进程内共享；GLOBAL 列表/宏观适合复用。调用方不应管理两套 cache API。

**影响（Consequences）**  
Strategy / Tag 删除 per-call `ContractCacheManager()`；测试可用 `cache_enabled=False` 关闭 GLOBAL cache。

---

## 决策 13：`issue` / `load` 拆分与 Facade `until`

**状态：** 已实现（0.5.0）

**决策（Decision）**  

- **`issue(..., should_load_initially=True)`**（默认）：签发后立即 **`load`**。
- **`should_load_initially=False`**：仅签发句柄；调用方 **`DataContracts.load(issued)`** 再物化。
- PIT 前缀裁剪：时序句柄 **`BaseTimeSeriesContract.until(as_of)`**（`CursorState` 内置）。
- 时间语义 helper（`get_time_window`、`normalize_as_of` 等）在时序基类。

**理由（Rationale）**  
batch job 可先批量 `issue` 再 `fill_in_data`；游标状态与契约句柄同生命周期，无需独立 cursor 模块。

---

## 决策 14：PER_ENTITY DataFrame + Parquet 缓存（未来）

**状态：** 未做

**背景（Context）**  
大规模 PER_ENTITY 时序以 `List[Dict]` 持有内存压力大；同机多 run 重复 IO 仍常见。决策 12 明确 **当前** PER_ENTITY 不进进程内 cache。

**决策（Decision）**  

- **将来** loader / 句柄可承载 **`pandas.DataFrame`** 作为时序 payload（与 list 语义对齐）。
- **将来** 模块内部按 **`(data_key, entity_id, load_window, params)`** 将 PER_ENTITY 片段 **Parquet 化**，供 job / run 内复用；**用户不可配置**是否启用（黑盒策略，与 GLOBAL memory cache 正交）。
- Facade **`load` / `until` / `row_count`** 须对 DataFrame 与 list **等价**。

**理由（Rationale）**  
Parquet 适合列式时序 bulk 与调试复放；不与 GLOBAL 小对象 memory cache 混用。

**影响（Consequences）**  
落地顺序见 [`ROADMAP.md`](ROADMAP.md) 阶段 6、[`TODO.md`](../TODO.md)。

