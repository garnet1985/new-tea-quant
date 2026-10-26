# Machine Capacity 详细设计

**版本：** `0.2.1`

实现向细节；公开入口见根目录 [API.md](../API.md)。

## 内存预算语义

1. `memory_floor_mb`：机器必须保留的空闲内存，不参与 worker 预算；`auto` 时按总量/可用估算（见 `MachineInfo` 类常量）。
2. `memory_budget_mb`：显式则直接用（下限 `MIN_BUDGET_MB`）；`auto` 时为 `(available − floor) * worker_memory_fraction`，夹在 `MIN_BUDGET_MB`–`MAX_BUDGET_MB`。
3. 无 psutil 时：floor / budget 分别回落到 `FALLBACK_MEMORY_FLOOR_MB` / `FALLBACK_BUDGET_MB`。

## 可用 worker

`max(1, cpu_count − reserve_cores)`。

## 设计决策

> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）