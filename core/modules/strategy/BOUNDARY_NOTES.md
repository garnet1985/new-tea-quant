# Strategy Module — Boundary Notes

供后续 split/merge 与 agent 改动参考。下方「与 BE 的关系」为硬约束；「Shared vs private」为包布局约定。

## 与 BacktestEngine 的关系（硬约束 — 勿再复杂化）

**Strategy 模块的主业**：把用户策略钩子（及引擎业务）通过 BE `RunCallbacks` 挂进回测器，再做 jobs / 报告 / 指纹等周边。  
**不**在 strategy 侧另起一套调度、日历推进、或平行于 BE 的 session 框架。

| 谁 | 干什么 |
|----|--------|
| **BE** | jobs 调度、worker、`Timeline`（默认按 `run(start,end)` + CalendarService 建开市日轴并 `drive`）、`JobContext`（含 **`init`**） |
| **Strategy 引擎** | `JobBuilder` 喂 jobs；`JobExecutor` 实现 callbacks；可变状态只挂在 **`job_context.init`** |

### 枚举器（entity / slice）两件套 — 仅此

```text
JobBuilder  → 组装 BE jobs（payload 含数据加载窗；slice 另写 timeline_point_count 供规划）
JobExecutor → RunCallbacks（on_before_task_start / on_tick / …）
Pipeline    → 周边编排（采样、BE.run、ReportManager）
```

**禁止再引入：**

- **TimelineBuilder / 枚举器侧复写推进轴** — 枚举走交易日历即可，交给 BE；不要为 enum 再 build 一份 start/end 或 points「覆盖默认轴」
- **JobSession / 第二套 session** — BE 的 session 就是 `JobContext.init`（`on_before_task_start` 返回值）。`EntityTaskState` / `SliceTaskState` 只是 init 里的可变袋，不是平行 API
- **Executor 空 proxy** — 日业务入口在 `JobExecutor` 钩子；不要再拆一层「只有转发」的 Session 类文件叙事
- **自建日历 resolver 重复 BE** — slice 若只需 `timeline_point_count`，用 `Timeline.from_calendar_window` 取点数即可（见 slice `JobBuilder`）

### 价格回测 / 投资组合 vs Timeline

| 引擎 | Timeline 复写？ |
|------|----------------|
| **enumerator** | 不需要 |
| **price_factor** | 现状：`run(start,end)` + 默认日历；真业务在 after_task 事件回放，`on_tick` noop。**不要**为「少空转」先加 TimelineBuilder；等回放迁到 `on_tick` 再议 event 轴 |
| **portfolio** | **不用 BE**；enum → `PortfolioEvent` 排序 → 进程内模拟。不要为组合套 `Timeline.drive` |

### 进程内传对象

完整 dataclass（如 `StrategySettings`）在同进程路径直接传；**仅**在 pickle / job payload / 落盘边界 `to_dict`。勿把完整对象再投影成 bag/标量「中间层」。

## Shared vs private（约定）

四大引擎：`scanner` / `enumerator` / `price_factor` / `portfolio`。

### 何时进 `engines/shared`

| 条件 | 动作 |
|------|------|
| **≥3 个引擎**依赖同一概念 | 必须进 `engines/shared` |
| **恰好 2 个**，且是上游产物 → 下游消费的稳定契约 | 也进 shared（或 `shared/services/...`），不藏在 producer 私有包 |
| 仅 1 个引擎用 | 留在该引擎私有包 |
| Facade / hooks / `core/services` | 不算第五大件；若依赖 shared，**消费者标注须写出** |

### shared 只允许两类

| 可放 | 不放 |
|------|------|
| `data_class`（跨引擎 DTO / 生命周期对象） | Pipeline / JobBuilder / Executor |
| `services`（无引擎偏见的加载、解析、校验） | 某引擎 ReportManager / 写盘格式 |
| （可选）纯类型并入 `data_class` 或旁挂 `types` | helpers（先私有；真 ≥3 再提成 **service**，不提成 helpers） |

`enumerator/common` 是**枚举引擎内部**（entity vs slice）共用；与四引擎 `engines/shared` 层级不同，故意不用 shared 以免混淆。

### 按功能块移动

promote / demote 时**整块**搬迁（例如整个 `strategy_settings` 包），不要把「根」留在 shared、「叶子」拆进引擎。消费者标注打在**块入口**上即可。

### 入口必须标消费者

每个 shared 对外入口（包 `__init__.py` 或主模块）文件顶：

```text
消费者: scanner, enumerator, price_factor
（可选）Facade / hooks / fingerprints
```

搬迁或删除前先对消费者；review 可核对是否仍满足 ≥2。

### 整理顺序（todo）

1. 本约定入库（本节） — done
2. 消费矩阵审计（keep / promote / demote） — 见下节
3. 现有 shared 入口打标注 — done
4. 提升仿真输入契约（enum 产物被 price/portfolio 读） — done → `shared/services/simulation_output`
5. 切断 Scanner→Enumerator 借包 — done（hooks→StrategyHookRuntime；PitBars→shared）
6. investments / pit_bars 包结构 — **跳过**（后期：Investment 拆分、pit_bars 清理）
7. hooks→portfolio 泄漏 — done（默认 on_pick 不再 import EntrySelector）
8. 空壳/双路径清理 — done（删除 `core/services/settings/`；唯一入口 `engines/shared/services/strategy_settings`）
9. pytest + 违规跨引擎私有 import 扫尾 — done
10. CalendarAsOf* → shared.data_class — done
11. 专门整理 `simulation_output` — **done**（收薄为布局服务：`file_names` / `paths` / `io` / `layout`；内容模型归 enumerator `artifacts` + price/portfolio `enum_input`）
12. **后期** `PENDING_TO_ENTER` 入场风控：`max_wait_open_days` / `max_entry_drift` / `abort_enter_when` 接到 `try_enter`（与 `_is_able_to_enter` 分离：不能成交≠放弃机会）
13. enumerator tick 调用链 — **done**：BE `Timeline.drive` → `JobExecutor.on_tick` → `EntityTaskState`/`SliceTaskState.on_calendar_day` → `InvestmentTracker.process_tick`（分桶 `try_exit` / `try_enter` / `check_targets`）→ Investment（**无** JobSession 层）
14. 枚举器去 TimelineBuilder / 平行 session — **done**（见上文「与 BE 的关系」）

## 消费矩阵（审计，2026-07-24）

引擎缩写：S=scanner E=enumerator P=price_factor O=portfolio。  
动作：`keep` 维持 shared；`promote` 从私有抬进 shared；`demote` 从 shared 降回私有；`fix-leak` 切断非法跨包。

### A. 已在 `engines/shared` 的物品

| 物品 | 引擎消费者 | 其它 | 动作 | 说明 |
|------|------------|------|------|------|
| `data_class/opportunity` | S E O | contracts, hooks | **keep** | ≥3 |
| `data_class/investment`（含 BarPrices 等） | S E P | contracts | **keep** | ≥3；O 不直接用 |
| `data_class/simulate_session` | E P O | Facade | **keep** | ≥3 |
| `entity_loader` 整包 | S E（+ Facade/fingerprints） | — | **keep（整块）** | 含 job_bundle / resolver / global / sampling / indicators；不拆子模块 |
| `entity_loader` → period | — | — | **done** | `StrategySettings.resolve_period`（挂在 settings） |
| `strategy_settings` 整包 | S E P O | hooks, core.services | **keep（整块）** | 含 simulation/portfolio/scanner 等；**不拆根/叶** |
| `data_class/investment/*` 子目录 | investment / enums / investment_state | — | ok | Investment 与小类型同目录 |

### B. 跨引擎 / 跨层私有 import（应 promote 或 fix）

| 边 | 目标 | 动作 | 说明 |
|----|------|------|------|
| ~~P/O → E stock_investments / runtime / enum_data~~ | — | **done** | 先经 shared；再收薄：布局留 shared，内容各引擎私有 |
| fingerprints / entity_loader → period | — | **done** | `StrategySettings.resolve_period` |
| P/O 读 enum version | — | **done** | `simulation_output.EnumSource`；P/O `enum_input` 仅私有 CSV 行解析；写各自 report |
| E runtime/CSV 内容 | — | **done** | `enumerator/common/artifacts` |
| ~~S → E load_hooks / PitBars~~ | — | **done** | hooks 直连 StrategyHookRuntime；PitBars → `shared/services/pit_bars` |
| hooks → O `EntrySelector` | — | **fix-leak** | #7；contracts / lazy |
| ~~contracts / hooks → E slice_based.types~~ | CalendarAsOf* | **done** | → `shared/data_class/calendar_as_of.py`；公开仍经 contracts |
| Facade → S | ScannerPipeline | OK | Facade 编排，不算泄漏 |

### C. 与后续 todo 的对应

| 矩阵结论 | todo |
|----------|------|
| A 表 keep 项打消费者标注 | #3 |
| B：stock_investments / runtime_snapshot / enum_data | #4 done |
| B：S→E base_executor / PitBars | #5 |
| A：settings / entity_loader 整块 keep；死目录核对 | #6 |
| B：hooks→O | #7 done |
| 空壳 `core/services/settings` | #8 done |

## Naming

| 路径 | 问题 | 说明 |
|------|------|------|
| 各引擎 `job_builder.py` / `executor.py` | 同名类 `JobBuilder` / `JobExecutor` 重复 | scanner / enumerator(entity+slice) / price_factor 各自独立，import 必须带包路径，易混淆 |
| `engines/scanner/helpers/cache_manager.py` vs `services/simulation_cache/cache_manager.py` | 都叫 CacheManager | 前者磁盘 scan CSV，后者 DB workbench；语义完全不同 |
| `shared/data_class/investment.py` vs `portfolio/data_class/investment.py` | Investment 一词两用 | 前者 enum 生命周期对象，后者 `PortfolioInvestment` 资金汇总；命名未对齐 |
| `core/enums.py` vs `core/const.py` | 枚举与常量分离 | 全局 Enum 只放 enums；字面常量/默认值只放 const；contracts 不再承载枚举 |
| userspace `strategy.py` vs 模块 `strategy.py` | 同名文件不同职责 | 用户 hooks 入口 vs 模块 Facade；discovery 动态 module id 已用 `_ntq_strategy_*` 区分 |
| `SimulationOutputRecorder` vs 各引擎 `ReportManager` | Recorder / Manager 分工不直观 | Recorder 只管 version 目录分配；实际产物写盘在三套 ReportManager |
| ~~`core/services/settings/`~~ | — | **done**；仅 `engines/shared/services/strategy_settings` |

## Location / package layout

| 路径 | 问题 | 说明 |
|------|------|------|
| `engines/shared/services/entity_loader/` | 跨引擎却放在 `engines/shared` 下 | scanner / enumerator / price_factor 均依赖；更像 `core/services/data_loader` |
| `core/helpers/` vs `engines/scanner/helpers/` | helpers 分层不一致 | 顶层 helpers 无 IO；scanner helpers 含 DataManager、ProjectContext、adapter |
| ~~`price_factor/enum_data` / enum CSV 契约~~ | — | **done** → `shared/services/simulation_output` |

| ~~`contracts.py` 深 import slice_based~~ | — | **done**；CalendarAsOf* 在 shared.data_class |
| `core/services/data/simulation_output_recorder.py` | 与引擎 report_manager 分离 | 合理，但 enum/price/portfolio 三套 ReportManager 无 shared 基类，重复 begin/finalize 模式 |
| `FingerprintCalculator` 在 `simulation_cache/` | 指纹非缓存 | 算指纹 + seed GlobalEntityCache；更接近 `core/services/fingerprints` 或 orchestration 层 |

## Boundary leaks

| 泄漏 | 路径 | 说明 |
|------|------|------|
| ~~Scanner → Enumerator~~ | — | **done**（#5） |
| ~~StrategyHooks → Portfolio~~ | — | **done**（#7）；未 override 由 EnterSelection 用 EntrySelector |
| 指纹服务 → GlobalEntityCache | `fingerprints.py` 构造并 seed cache | 编排前置步骤合理，但 `simulation_cache` 包名暗示仅 DB 缓存 |
| Portfolio → 多引擎 | `portfolio/pipeline.py` | ~~曾依赖 P.enum_data / E~~ → 布局 `simulation_output` + 私有 `enum_input` |
| Discovery validation → WorkerLoader | `discovered_strategy.py` 校验阶段加载 hooks | 发现阶段副作用（exec 用户 strategy.py）；失败策略仍可能被 list 看到 draft 错误 |

## Duplication

| 区域 | 重复内容 | 路径 |
|------|----------|------|
| 日历解析 | open_dates 过滤 | `helpers/calendar.py`、`scanner/helpers/date_resolver.py`（~~slice resolver/calendar~~ 已删；slice 规划点数用 BE `Timeline.from_calendar_window`） |
| 报告编排 | version 目录 + runtime + overall + entities | `enumerator/common/report_manager/`、`price_factor/report_manager/`、`portfolio/report_writer.py` |
| CSV 机会格式 | opportunities 写盘 | `helpers/opportunity_csv.py`、`scanner/helpers/cache_manager.py`（内联 write_dicts_to_csv） |
| Job payload 构建 | entity_shared / shm / strategy_info | `enumerator/common/base_job_builder.py`、scanner/price 各自 JobBuilder |
| 贴板/tradability | limit up 判定 | `scanner/helpers/tradability.py` vs price `deferred_exit` + simulation tradability settings |

## Suggested merges / splits

1. **`simulation_output` 布局服务** — done（names/paths/io/layout；**不含** RuntimeEnv / CSV / overall 内容模型）。

2. **Report 基类**（仅当确有共用业务骨架时）  
   `SimulationOutputRecorder` + 可选写目录骨架 → 内容 dataclass 仍各引擎私有；勿为文件名造共享 Overall/Performance。

3. **重命名 mode 内 Executor/JobBuilder**  
   例如 `ScannerJobExecutor`、`EnumEntityJobExecutor`、`PriceFactorJobExecutor`，或统一收到 `core/engines/{mode}/` 下用模块名消歧（保持类名简短时至少文档与 __all__ 用别名）。

4. **上移 entity_loader**  
   `core/services/entity_loader/`（或 `core/data/`），scanner 不再从 `engines/enumerator` 借 BaseJobExecutor；scanner 自有 `ScannerHookLoader` 薄封装。

5. **拆分 simulation_cache 包**  
   - `fingerprints.py` → `core/services/fingerprints/`  
   - `cache_manager.py` 保留 DB 槽位语义  
   - 可选：scan CSV 缓存接口与 DB 缓存共用 `BaseCacheManager` 抽象（磁盘 vs 表）

6. **contracts 瘦身** — done（CalendarAsOf* → `shared/data_class/calendar_as_of.py`）。

7. **Portfolio Investment 命名**  
   `PortfolioInvestment` 文件名与类名一致（已用类名）；shared `Investment` 文档中强调「信号生命周期」vs「资金汇总」。

8. **settings 包归一** — done。
