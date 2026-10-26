# Backtest Engine — 设计与决策

**版本：** `0.2.0`

本文记录回测调度引擎的设计目标、方案思路与拍板决策。API 与行为以根目录 [API.md](../API.md) 为准。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

对上层应用（tag / strategy）提供的任务进行规划、重组和按时间推进。回测调度是业务语义（entity / slice / 日历），不是通用计算原语：infra 提供机器容量、DuckDB scope 等原语，engine 组合为回测专用流水线。

要解决的核心问题包括「全窗 10GB、内存 8GB」类场景：全截面数据可能大于可用内存，需按片装载与释放，峰值由在飞片决定；同时用探针先做小批量测试再规划，充分利用资源的同时防止内存占用过高。

## 方案与思路

### 两种执行模式

公开 API 仅 `entity_based` 与 `slice_based`：

| 模式 | 并行模型 | 何时选用 |
|------|----------|----------|
| entity_based | ProcessPoolExecutor，每 batch 调 `execute_fn` | entity 间无 slice 内 cross-entity 编排 |
| slice_based | 按日历片从 DB 分次装载 + reader/compute 预读管道 | 全截面数据可能大于可用内存 |

slice_based 的权威算法独立成 [SLICE_BASED_ALGORITHM.md](./SLICE_BASED_ALGORITHM.md)（硬约束，见下文 DEC-03）。要点（细节以该文为准）：

- 按片装载与释放，峰值由在飞片决定
- 探针先测 `mb/open_day` 与读/算单价，再规划片宽与预读深度
- N 个正式片 ⇒ **至少 N 次**按片 DB 读；禁止 task 开头一次拉满全窗
- 预读队列用 `t_read/t_compute` 对齐吞吐；进度按片汇报

实现或 Strategy 集成若与该文冲突，**改代码对齐文档**。

### 其余选型主线

- **Facade + contracts 边界**：根目录 `BacktestEngine` 为唯一调度入口；跨模块类型从 `contracts.py` 导入；不 export planner/executor（见 DEC-01、DEC-02）。
- **业务提供 execute_fn，engine 提供 probe**：同一 `execute_fn` 用于 probe 试跑与正式执行；无独立 ProbeRegistry（见 DEC-04）。
- **Job 契约：id + payload**：所有 job 为 `{"id": str, "payload": dict}`；`BacktestJob.validate_many(..., mode=...)` 在 run 前 fail-fast（见 DEC-05）。
- **performance 配置边界**：engine 提供 base defaults，应用模块维护 `settings/dispatch.yaml`；engine 不读 global `worker.json` dispatch 段；用户 settings 禁止 `performance` 字段（见 DEC-06）。
- **RunCallbacks 聚合钩子**：`run(..., callbacks=RunCallbacks(...))`；不在 `run` 签名上平铺 `on_*`（见 DEC-07）。
- **进度始终计算，display 可关**：`enable_progress_display` 只控制 CMD 日志；四阶段权重始终生效（见 DEC-08）。
- **MachineInfo 归属 infra**：内存/CPU 解析使用 `core.infra.machine_capacity`（见 DEC-09）。
- **与 data_source 调度分离**：不合并 data_source 的依赖拓扑调度与 backtest engine（见 DEC-10）。

---

## DEC-01：放在 modules 层做业务调度 Facade

**是什么：** 引擎放在 `modules.backtest_engine`，不是 `infra` 通用执行器；infra 只提供机器容量、DuckDB scope 等原语。

**为什么选它：**

- 回测调度是业务语义（entity / slice / 日历），不是通用计算原语
- infra 保持纯净，不感知"回测"概念
- tag 与 strategy 共用同一业务入口

**放弃了什么：**

- **放 infra 做通用执行器：** 各业务自己拼 — 通用化程度高但业务语义稀释，调用方需重复编排

---

## DEC-02：公开 API 仅 entity_based 与 slice_based

**是什么：** 对外只暴露两种执行模式，不暴露 planner / executor 等内部组件。

**为什么选它：**

- 两种模式覆盖当前所有回测场景：entity 独立计算用 entity_based，全截面大窗用 slice_based
- 内部组件不导出，保持公开面窄

**放弃了什么：**

- **暴露 pipeline 阶段：** 调用方可自定义 stage — 灵活但破坏封装，内部演进受限

---

## DEC-03：slice_based 算法 SOT 独立成 SLICE_BASED_ALGORITHM.md

**是什么：** slice_based 的权威算法细节独立成文，实现或 Strategy 集成若与该文冲突，改代码对齐文档。

**为什么选它：**

- 算法本身复杂（探针、预读、片宽规划），独立文档便于专注维护
- 硬约束声明防止实现漂移

**放弃了什么：**

- **算法内嵌在代码注释：** 文档即代码 — 长算法在代码里难读，且无法独立评审

---

## DEC-04：业务提供 execute_fn，engine 提供 probe

**是什么：** 同一 `execute_fn` 用于 probe 试跑与正式执行；无独立 ProbeRegistry。

**为什么选它：**

- 探针与正式执行共用同一份业务逻辑，避免"探针行为与正式行为不一致"
- 减少概念数量——调用方只写一个函数

**放弃了什么：**

- **独立 ProbeRegistry：** 探针可注册独立轻量实现 — 探针与正式行为可能分叉，结果不可信

---

## DEC-05：Job 契约 = id + payload

**是什么：** 所有 job 统一为 `{"id": str, "payload: dict}`；`BacktestJob.validate_many(..., mode=...)` 在 run 前 fail-fast。

**为什么选它：**

- 极简契约降低接入成本
- fail-fast 在调度前拦截非法 job，避免跑到一半才发现

**放弃了什么：**

- **强类型 Job 类：** 每类 job 一个 dataclass — 类型安全但增加样板代码，plugin 接入成本高

---

## DEC-06：engine 不读 global worker.json dispatch 段

**是什么：** engine 提供 base defaults，应用模块维护 `settings/dispatch.yaml`；用户 settings 禁止 `performance` 字段。

**为什么选它：**

- 调度参数与机器容量解耦——机器容量由 infra.machine_capacity 探测，调度策略由应用模块定义
- 用户不应直接调 performance，避免破坏引擎自调度

**放弃了什么：**

- **用户可覆盖 performance：** 高级用户可调 worker 数 — 误配风险高，且与引擎自探测冲突

---

## DEC-07：RunCallbacks 聚合钩子

**是什么：** `run(..., callbacks=RunCallbacks(...))`；不在 `run` 签名上平铺 `on_*`。

**为什么选它：**

- 签名稳定——新增钩子不破坏 API
- 钩子集中管理，调用方一眼看清有哪些钩子

**放弃了什么：**

- **平铺 on_start / on_progress / on_end：** 调用直观 — 签名膨胀，新增钩子破坏兼容性

---

## DEC-08：进度始终计算，display 可关

**是什么：** `enable_progress_display` 只控制 CMD 日志；四阶段权重（load 5% + dispatch 3% + execute 90% + report 2%）始终生效。

**为什么选它：**

- 进度计算与展示解耦——前端 / BFF 需要进度数据，CMD 日志只是其中一种消费方式
- 四阶段权重固定，避免各业务自定义导致进度语义漂移

**放弃了什么：**

- **display 关闭即不计算：** 省 CPU — 前端无法拿到进度，进度文件机制失效

---

## DEC-09：MachineInfo 归属 infra.machine_capacity

**是什么：** 内存 / CPU 解析使用 `core.infra.machine_capacity`，engine 不自带硬件探测。

**为什么选它：**

- 硬件探测是通用原语，不应绑定在回测引擎里
- 单一真源，避免多处探测结果不一致

**放弃了什么：**

- **engine 自带探测：** 减少跨模块调用 — 硬件探测逻辑重复，且无法被其他模块复用

---

## DEC-10：与 data_source 调度分离

**是什么：** 不合并 data_source 的依赖拓扑调度与 backtest engine。

**为什么选它：**

- data_source 是 DAG 依赖拓扑（先拉股票列表再拉 K 线），backtest 是时间窗推进——语义完全不同
- 合并会导致引擎职责膨胀

**放弃了什么：**

- **统一调度框架：** 一套引擎支撑所有调度 — 语义稀释，两边都做不好

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
