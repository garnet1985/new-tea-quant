# Backtest Engine — 设计决策

**模块：** `modules.backtest_engine` · **版本：** 0.3.0

本文档记录**当前有效**的设计决策。API 与行为以 `api.yaml` 为准。

---

## 1. 模块定位：业务调度 Facade

**决策：** 放在 `modules` 层，作为 tag/strategy 共用的回测调度 Facade，不是 infra 通用执行器。

**理由：**
- 理解回测 job 形状、probe/plan、entity vs slice 编排差异
- infra 提供机器容量、DuckDB scope 等基础能力；engine 组合它们为回测专用流水线

---

## 2. 两种执行模式

**决策：** 公开 API 仅 `entity_based` 与 `slice_based`。

| 模式 | 并行模型 | 何时选用 |
|------|----------|----------|
| entity_based | 外层 `ProcessPoolExecutor`，每 batch 调 `execute_fn` | entity 间无 slice 内 cross-entity 编排 |
| slice_based | 主进程 `execute_fn` + 内部 reader/compute orchestrator | slice 内多 entity 管道交互 |

**理由：** 模式差异本质是「是否在 slice 边界内做编排」；slice 模式不能包一层 daemon ProcessPool（子进程无法再 fork orchestrator）。

内部包 `timeline_based` 对应 `entity_based`，命名保留仅为目录稳定，对外只用新术语。

---

## 3. Facade + contracts 边界

**决策：**
- 根目录 `BacktestEngine` 为唯一调度入口
- 跨模块类型从 `contracts.py` 导入
- 不 export planner/executor；业务不 import `core/` 内部路径

**理由：** 收紧 API，避免多入口与实现细节泄漏。

---

## 4. 业务提供 execute_fn，engine 提供 probe

**决策：** 同一 `execute_fn` 用于 probe 试跑与正式执行；无独立 ProbeRegistry。

**理由：** 探针测的是真实 worker 路径；调用方最清楚如何执行 job。

---

## 5. Job 契约：id + payload

**决策：** 所有 job 为 `{"id": str, "payload": dict}`；`BacktestJob.validate_many(..., mode=...)` 在 run 前 fail-fast。

**理由：**  envelope 统一，payload 按 mode 区分最小字段集（entity 键 vs open_dates + bulk entities）。

---

## 6. performance 配置边界

**决策：**
- engine 提供 `EntityBasedPerformance.base()` / `SliceBasedPerformance.base()`，入口 `validate` + `resolve`
- 应用模块维护 `settings/dispatch.yaml`（性能基准，用户不可改）
- engine **不读** global `worker.json` dispatch 段
- 用户 settings **禁止** `performance` 字段；业务项用 `update_mode`、`run_options` 等

**理由：** 消除多层 merge 与用户误配；调优权在模块维护者，不由 end user 覆盖。

---

## 7. RunCallbacks 聚合钩子

**决策：** `run(..., callbacks=RunCallbacks(on_result=..., on_release=...))`；不在 `run` 签名上平铺 `on_*`。

**理由：** 扩展回调不破坏 Facade 签名；`on_release` 仅 entity_based batch 释放时使用。

---

## 8. entity_based：QUEUE 填池 + ProcessPool

**决策：** 默认 QUEUE（完成 1 补 1）；`max_workers` / `entities_per_job` 由 plan 决定，Monitor 可调 in-flight 上限。

**理由：** 吞吐与内存平衡；BATCH/ELASTIC 未作为当前公开路径。

---

## 9. Probe 与 Monitor 分工（entity_based）

**决策：**
- **Probe**：小样本试跑，得到 epj / 内存相关初值
- **Monitor**：运行期采样，主要调整 admission / in-flight；**entities_per_job 全 run 固定**

**理由：** 规划与运行时反馈分离，避免 run 中频繁改 batch 形状。

---

## 10. slice 进度 hook

**决策：** slice 细粒度进度由 engine 注入 `_engine_on_execute_unit_done`；tag/strategy orchestrator 每 slice 回调，engine 统一算 percent 与 CMD 输出。

**理由：** slice 循环在 `execute_fn` 内部，engine 外层只有 bulk job 粒度；hook 保持 engine 拥有进度算法。

---

## 11. 进度：始终计算，display 可关

**决策：** `enable_progress_display` 只控制 CMD 日志；四阶段权重 5/10/80/5 始终生效。

**理由：** 后续可接 UI/回调 sink，不与「是否打印」绑定。

---

## 12. MachineInfo 归属 infra

**决策：** 内存/CPU 解析使用 `core.infra.machine_capacity`；engine 内不保留 re-export 空壳。

**理由：** 机器容量是 infra 能力；engine 只消费 `get_capacity` / `worker_pool_budget_mb`。

---

## 13. 与 data_source 调度分离

**决策：** 不合并 data_source 的依赖拓扑调度与 backtest engine。

**理由：** 执行顺序、并行策略、资源模型均不同；各自独立模块更清晰。

---

## 14. 测试：test_cases.yaml

**决策：** `__test__/test_cases.yaml` 为 UT 索引；一个 case 大类对应一个 test 文件，scenario 对齐 pytest 函数名。

**理由：** 用例可追溯；engine 层不测 infra 职责（如 MachineInfo 单测在 infra）。

---

## 相关文档

- [OVERVIEW.md](../OVERVIEW.md)
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [api.yaml](../api.yaml)
- [glossary.yaml](../glossary.yaml)
