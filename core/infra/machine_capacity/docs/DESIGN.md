# Machine Capacity 详细设计

**版本：** `0.2.0`

## 内存预算语义

1. `memory_floor_mb`：机器必须保留的空闲内存，不参与 worker 预算；`auto` 时按总量/可用估算。
2. `memory_budget_mb` / `dispatch_memory_budget_mb`：显式则直接用；`auto` 时为 `(available − floor) * worker_memory_fraction`，夹在 256–16384 MB。
3. 兼容旧字段 `main_process_reserve_mb`：并入 floor 的下限。

## 可用 worker

`max(1, cpu_count − reserve_cores)`。
