# Strategy — 设计说明

**模块：** `modules.strategy` · **版本：** `0.7.0`

硬约束摘要如下；更长边界笔记见 [notes/BOUNDARY_NOTES.md](./notes/BOUNDARY_NOTES.md)。

---

## 与 BacktestEngine（硬约束）

Strategy 主业：把用户策略钩子经 BE `RunCallbacks` 挂进回测器。**不**另起平行调度或 session 框架。

- **禁止** TimelineBuilder / 第二套 JobSession / Executor 空 proxy
- 时钟 → 切数据 → 业务：`Timeline.drive` → `on_tick` → `AsOfSlice` → 业务

---

## simulation_output 读路径

| 类型 | 职责 |
|------|------|
| `EnumOutput` | version 目录布局 |
| `EnumSource` | 下游只读句柄 |
| `investment_csv` | 投资/goal CSV 行模型 |

---

## Facade + contracts

- 包根仅 `Strategy`
- hooks / 枚举 / 共享数据类从 `contracts.py` 导入
- 公开 API 状态最高 `beta`（core 仍为 `0.x`）

## 自由函数现状

- 模块内约 29 个无下划线顶层 `def`，**绝大多数仅模块内使用**（helpers / package / timeline 等）。
- **跨模块入口**此前主要是 `package_cli.run_export` / `run_strategy_bundle_import`（CLI）；已收为 **`PackageCli`** 类方法。
- BFF / tag / adapter 的 deep-import 多为**类**（`DiscoveryService`、`ReportManager` 等），不在「自由函数类化」范围内；全量改走 Facade 另开专项。

---

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [API.md](../API.md)
- [BOUNDARY_NOTES.md](./notes/BOUNDARY_NOTES.md)
