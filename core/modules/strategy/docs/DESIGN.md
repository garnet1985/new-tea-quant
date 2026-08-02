# Strategy — 设计说明

**模块：** `modules.strategy` · **版本：** `0.7.0`

摘自原 `BOUNDARY_NOTES.md` 中仍有效的硬约束。

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

---

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [API.md](../API.md)
