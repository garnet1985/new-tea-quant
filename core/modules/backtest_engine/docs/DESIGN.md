# Backtest Engine — 设计说明

**模块：** `modules.backtest_engine` · **版本：** `0.4.0`

API 与行为以根目录 [API.md](../API.md) 为准。

---

## 1. 模块定位：业务调度 Facade

放在 `modules` 层，作为 tag/strategy 共用的回测调度 Facade，不是 infra 通用执行器。infra 提供机器容量、DuckDB scope 等；engine 组合为回测专用流水线。

---

## 2. 两种执行模式

公开 API 仅 `entity_based` 与 `slice_based`。

| 模式 | 并行模型 | 何时选用 |
|------|----------|----------|
| entity_based | ProcessPoolExecutor，每 batch 调 `execute_fn` | entity 间无 slice 内 cross-entity 编排 |
| slice_based | 主进程 `execute_fn` + reader/compute orchestrator | slice 内多 entity 管道交互 |

内部包名与公开模式名一致；`BacktestMode` 定义于 `core/shared/modes.py`。

---

## 3. Facade + contracts 边界

- 根目录 `BacktestEngine` 为唯一调度入口
- 跨模块类型从 `contracts.py` 导入
- 不 export planner/executor

---

## 4. 业务提供 execute_fn，engine 提供 probe

同一 `execute_fn` 用于 probe 试跑与正式执行；无独立 ProbeRegistry。

---

## 5. Job 契约：id + payload

所有 job 为 `{"id": str, "payload": dict}`；`BacktestJob.validate_many(..., mode=...)` 在 run 前 fail-fast。

---

## 6. performance 配置边界

- engine 提供 base defaults，应用模块维护 `settings/dispatch.yaml`
- engine **不读** global `worker.json` dispatch 段
- 用户 settings **禁止** `performance` 字段

---

## 7. RunCallbacks 聚合钩子

`run(..., callbacks=RunCallbacks(...))`；不在 `run` 签名上平铺 `on_*`。

---

## 8. 进度：始终计算，display 可关

`enable_progress_display` 只控制 CMD 日志；四阶段权重始终生效。

---

## 9. MachineInfo 归属 infra

内存/CPU 解析使用 `core.infra.machine_capacity`。

---

## 10. 与 data_source 调度分离

不合并 data_source 的依赖拓扑调度与 backtest engine。

---

## 相关文档

- [README.md](../README.md)
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [API.md](../API.md)
