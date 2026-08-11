# Strategy Module — Boundary Notes

供后续 split/merge 与 agent 改动参考。  
「与 BE 的关系」「时钟 → 切数据 → 业务」「simulation_output 读路径」为硬约束；「Shared vs private」为包布局约定。

> README 架构树等 report manager 整理后再改；以本文为准。

## 与 BacktestEngine 的关系（硬约束 — 勿再复杂化）

**Strategy 模块的主业**：把用户策略钩子（及引擎业务）通过 BE `RunCallbacks` 挂进回测器，再做 jobs / 报告 / 指纹等周边。  
**不**在 strategy 侧另起一套调度、日历推进、或平行于 BE 的 session 框架。

| 谁 | 干什么 |
|----|--------|
| **BE** | jobs 调度、worker、`Timeline`（默认按 `run(start,end)` + CalendarService 建开市日轴）、**slice：`SliceOrchestrator` 按正式片装载/释放**、`JobContext`（含 **`init`**） |
| **Strategy 引擎** | 各模式 `*JobBuilder` 喂 jobs；`*JobExecutor` 实现 callbacks；可变**业务**状态只挂在 **`job_context.init`**；**不**驱动调度 |

### 枚举器（entity / slice）两件套 — 仅此

```text
*JobBuilder  → 组装 BE jobs（payload 含**按片**数据装载契约；slice 另写 timeline_point_count 供规划）
*JobExecutor → RunCallbacks（on_task_start / on_tick / on_task_complete / …）；**禁止** task 开头全窗一次 JobBundleLoader
Pipeline    → 周边编排（采样、BE.run、ReportManager）
```

**slice_based 装载算法（BE SOT，Strategy 必须遵守）：**  
`core/modules/backtest_engine/docs/SLICE_BASED_ALGORITHM.md`  
N 正式片 ⇒ 至少 N 次按片 DB 读；峰值由 `peak_slices = compute + queue + readers` 决定，不是全窗一次进内存。  
调度状态（窗宽 / reader / queue / 进度）**仅**在 BE；Strategy 只绑定 `init["entity_contracts"]` 做日业务。

**禁止再引入：**

- **TimelineBuilder / 枚举器侧复写推进轴** — 枚举走交易日历即可，交给 BE
- **JobSession / 第二套 session** — BE 的 session 就是 `JobContext.init`。`EntityTaskState` / `SliceTaskState` 只是 init 里的可变袋
- **Strategy 侧片窗装载 / prefetch / queue refine / 进度** — 一律 `SliceOrchestrator`
- **Executor 空 proxy** — 日业务入口在 `JobExecutor` 钩子
- **自建日历 resolver 重复 BE** — slice 规划点数用 `Timeline.from_calendar_window` 即可

### 时钟 → 切数据 → 业务（硬约定）

每个 BE 日历 tick 必须按此顺序，**不得**在业务里另造 `as_of`：

```text
1. BE SliceOrchestrator 按正式片装载 → on_tick(point)   # 唯一时钟
2. AsOfSlice（shared/services/as_of_slice）按 point 切 contracts / base_bar
3. 业务消费 (point, sliced) — scan / Investment / hooks
```

- `AsOfSlice`：时钟点数据切片服务（原 `PitBars` 已删）
- Scanner tick 路径只认 BE `point`；payload 里的 `scan_date` 仅作 job 元数据（建单日轴），**不可**在 `on_tick` 里覆盖时钟

### 价格回测 / 投资组合 vs Timeline

| 引擎 | Timeline 复写？ |
|------|----------------|
| **enumerator** | 不需要 |
| **price_factor** | 现状：`run(start,end)` + 默认日历；真业务在 on_task_complete 事件回放，`on_tick` noop。**不要**为「少空转」先加 TimelineBuilder；等回放迁到 `on_tick` 再议 event 轴 |
| **portfolio** | **不用 BE**；enum → `PortfolioEvent` 排序 → 进程内模拟。不要为组合套 `Timeline.drive` |

### 进程内传对象

完整 dataclass（如 `StrategySettings`）在同进程路径直接传；**仅**在 pickle / job payload / 落盘边界 `to_dict`。

---

## simulation_output 读路径（硬约定）

包：`engines/shared/services/simulation_output/`

| 类型 | 文件 | 职责 |
|------|------|------|
| **EnumOutput** | `enumerator_output.py` | version 目录**布局**：resolve 路径、读 raw `runtime_env` / `entity_ids`、CSV 路径助手 |
| **EnumSource** | `enum_source.py` | 下游**只读句柄**：包一层 `EnumOutput`，投影 period / entity_ids / runtime；**委托** `load_investments` / `load_goals` |
| **investment_csv** | `investment_csv.py` | 投资/goal CSV **行模型 + 读写**（E 写、P/O 读，同一份） |
| 布局 IO | `file_names` / `paths` / `io` | 文件名、路径、json/txt 读写 |

**写边界：**

- 枚举 **RuntimeEnv** 等写模型 → `enumerator/common/artifacts`（CSV 行模型已上移，artifacts 仅 re-export）
- P/O **写自有产物** → 各自 report（**本期先不动**）
- 已删除 P/O `enum_input/`（不再私有拷贝 CSV 解析）

---

## Shared vs private（约定）

四大引擎：`scanner` / `enumerator` / `price_factor` / `portfolio`。

### 何时进 `engines/shared`

| 条件 | 动作 |
|------|------|
| **≥3 个引擎**依赖同一概念 | 必须进 `engines/shared` |
| **恰好 2 个**，且是上游产物 → 下游消费的稳定契约 | 也进 shared（或 `shared/services/...`） |
| 仅 1 个引擎用 | 留在该引擎私有包 |
| Facade / hooks / `core/services` | 不算第五大件；依赖 shared 时**消费者标注须写出** |

### shared 只允许两类

| 可放 | 不放 |
|------|------|
| `data_class`（跨引擎 DTO / 生命周期对象） | Pipeline / JobBuilder / Executor |
| `services`（无引擎偏见的加载、解析、校验、切片） | 某引擎 ReportManager / 写盘格式 |
| （可选）纯类型并入 `data_class` | helpers（先私有；真 ≥3 再提成 **service**） |

`enumerator/common` 是**枚举引擎内部**（entity vs slice）共用；与四引擎 `engines/shared` 层级不同。

### 入口必须标消费者

每个 shared 对外入口文件顶：

```text
消费者: scanner, enumerator, …
```

---

## 已完成（摘要）

| 项 | 状态 |
|----|------|
| Shared vs private 约定 + 消费者标注 | done |
| 仿真输入契约 → `simulation_output`（布局 + `EnumSource`） | done |
| Scanner→Enumerator 借包切断；`AsOfSlice` → shared | done |
| hooks→portfolio `EntrySelector` 泄漏切断 | done |
| 删除空壳 `core/services/settings/`；唯一 `strategy_settings` | done |
| `CalendarAsOfContext` 删除；仅留 `CalendarAsOfResult`；`on_entity_init` 删除 | done |
| hooks 上下文 → `hooks/hook_params/StrategyContext` | done |
| period → `StrategySettings.resolve_period` | done |
| 枚举器仅 JobBuilder + JobExecutor；无 TimelineBuilder / JobSession | done |
| tick：推进 → `AsOfSlice` → 业务 | done（命名 + Executor 接线） |
| 旧 skip 测删除；`EnumVersionData` → `EnumSource` | done |
| enum 投资 CSV 三份拷贝 → `simulation_output.investment_csv` | done |
| `entity_loader` 整块上移 → `core/services/entity_loader` | done |
| perf metric `pit_*` → `as_of_slice_*` / `enum_as_of_slice` | done |
| JobBuilder/Executor 类名加引擎前缀（文件名不变） | done |
| `PENDING_TO_ENTER` 挂单风控（touch / wait / drift / abort） | done |
| ReportManager 统一生命周期（`BaseReportManager` + 四引擎） | done |

UI 工作台 **submit / 读进度** 在 ``core.bff.APIs.strategy.routes.runner``。
**加权进度 / 落盘**：``PipelineProgress``（workbench）、``ScanProgress`` + ``ScanJob``（扫描）；BFF 只读 / 薄壳。
**Snapshot 读模型**（多 version settings、冷启动、hydrate）在 BFF ``helpers/workbench_snapshots`` + ``report_hydrate``——前端概念；后端 run 只走指纹 ``SimulationCacheManager``。
``launcher`` 包已删除。

---

## 消费矩阵（审计，2026-07-25）

引擎缩写：S=scanner E=enumerator P=price_factor O=portfolio。

### A. `engines/shared` 的物品

| 物品 | 引擎消费者 | 其它 | 动作 | 说明 |
|------|------------|------|------|------|
| `data_class/opportunity` | S E O | contracts, hooks | **keep** | ≥3 |
| `data_class/investment` | E（+ contracts） | — | **keep** | 信号生命周期；P/O 用私有 `InvestmentRow`，勿与 `PortfolioInvestment` 混淆 |
| `data_class/simulate_session` | E P O | Facade | **keep** | ≥3 |
| `data_class/calendar_as_of` | E | contracts, hooks | **keep** | 仅 `CalendarAsOfResult` |
| `strategy_settings` 整包 | S E P O | hooks, core.services | **keep（整块）** | period 挂在 settings |
| `simulation_output` | E（写路径经 Artifact*）P O（读） | fingerprints | **keep** | 见上文读路径表 |
| `as_of_slice` | S E | — | **keep** | 时钟点切数据 |
| `safe_values` | （按需） | — | keep | 小工具 |

### A2. `core/services`（跨引擎 + Facade，非整引擎私有）

| 物品 | 引擎消费者 | 其它 | 动作 | 说明 |
|------|------------|------|------|------|
| `entity_loader` 整包 | S E | Facade, fingerprints | **keep（整块）** | 已从 `engines/shared` 上移；含 job_bundle / resolver / global / sampling / indicators；**P 不依赖** |
| `simulation_cache` | — | Facade / fingerprints | keep | DB 槽位 + 指纹（指纹服务于 cache，**不拆出**） |
| `discovery` | — | Facade | keep | 策略发现 |
| `data/simulation_output_recorder` | E P O | — | keep | version 目录分配 |

### B. 跨引擎边（现状）

| 边 | 状态 | 说明 |
|----|------|------|
| P/O 读 enum version | **done** | `EnumSource` + `investment_csv`；无 P/O 私有拷贝 |
| E 写 runtime/CSV 内容 | **done** | `enumerator/common/artifacts` |
| S/E 切当日数据 | **done** | `AsOfSlice` |
| hooks → O EntrySelector | **done** | 无 import；默认选股在 `EnterSelection` |
| Facade → S | OK | 编排不算泄漏 |

---

## 遗留问题

> **Report manager（done）**：`shared/services/report_manager.BaseReportManager` + 四引擎私有 `ReportManager`（begin → collect* → finalize=summarize+save → present*）。无兼容别名；各引擎 `report_manager/` 包布局统一（`report_manager.py` + 私有 summary 数据类）。Scanner 落盘仍用 `scan_results/{date}/`。

### 应尽快（正确性风险）

| 问题 | 路径 | 说明 |
|------|------|------|
| **`PENDING_TO_ENTER` 入场风控** | — | **done**：`risk_control.pending_enter` + `enter_price=touch`；abort ≠ unable-to-enter |

### 后期整理

| 问题 | 路径 | 说明 |
|------|------|------|
| settings → GlobalEntityCache | `strategy_settings/.../execution.py` | `resolve_period` 耦合 cache；可再收薄 |
| helpers 分层不一致 | `core/helpers/*` vs `scanner/helpers/*` vs `price_factor/helpers/*` | 顶层宜无 IO；引擎 helpers 含 DataManager / adapter |
| 日历/日期双表面 | `helpers/calendar.py` vs `scanner/helpers/date_resolver.py` | 职责不同但「日期」入口分散 |
| Job payload 组装重叠 | `enumerator/common/base_job_builder.py` vs S/P `JobBuilder` | entity_shared / shm / strategy_info 模式重复 |
| 贴板/tradability 重叠 | `scanner/helpers/tradability.py` vs price `deferred_exit` + simulation risk settings | 语义近，实现散 |
| Discovery 校验副作用 | `discovery` → `StrategyHooksLoader` | 发现阶段 exec 用户 `strategy.py`；失败策略仍可能进 list |
| 空壳 / 薄目录 | `core/services/data/` 仅 recorder；`discovery/__test__/` 空 | 可随手清 |
| shared `Investment` 体量 | `data_class/investment/` | #6 曾跳过拆分；与入场风控一起再拆更合适 |
| price_factor `on_tick` noop | `price_factor/executor.py` | 回放仍在 on_task_complete；迁 `on_tick` 后再议 event 轴（勿先加 TimelineBuilder） |

### 命名 / 易混（低优先级）

| 问题 | 说明 |
|------|------|
| 多引擎同名 `JobBuilder` / `JobExecutor` | — | **done**：类名加前缀（文件名不变）`Scanner*` / `EnumEntity*` / `EnumSlice*` / `PriceFactor*`；基类仍 `BaseJob*` |

| 两个 `CacheManager` | `scanner/helpers/cache_manager.py`（磁盘 scan CSV）vs `simulation_cache/cache_manager.py`（DB workbench） |
| `Investment` vs `PortfolioInvestment` | 文件名 `portfolio/data_class/investment.py` 仍易混；类名已区分 |
| userspace `strategy.py` vs 模块 `strategy.py` | discovery 已用 `_ntq_strategy_*` 区分 |
| Scanner runtime `scan_date` 键名 | 与 tick `as_of`/`point` 并存；可逐步改成只作 meta，避免再当时钟 |

### 明确不做 / 已否决

| 项 | 说明 |
|----|------|
| 在 BE 内核调 `contract.until` | 切片属 Strategy 适配层（`AsOfSlice`），不把 data_contract 绑进 BE |
| 为 enum 再引入 TimelineBuilder / JobSession | 禁止 |
| 删模块内 `bff_support` / `launcher` | **done**：UI snapshot/hydrate → BFF helpers；scan/job progress → core services；BFF runner 薄壳 |
| 拆 `fingerprints` 出 `simulation_cache` | **不做**：指纹本就是给 cache 用的；以后若边界变了再挪 |

---

## Suggested next

1. 后期整理表中的剩余项（settings/cache、helpers 分层、Job payload 重叠等）按优先级择一。
