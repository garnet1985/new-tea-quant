# Machine Capacity 详细设计

**版本：** `0.2.0`

实现向细节；公开入口见根目录 [API.md](../API.md)。

## 内存预算语义

1. `memory_floor_mb`：机器必须保留的空闲内存，不参与 worker 预算；`auto` 时按总量/可用估算（见 `MachineInfo` 类常量）。
2. `memory_budget_mb`：显式则直接用（下限 `MIN_BUDGET_MB`）；`auto` 时为 `(available − floor) * worker_memory_fraction`，夹在 `MIN_BUDGET_MB`–`MAX_BUDGET_MB`。
3. 无 psutil 时：floor / budget 分别回落到 `FALLBACK_MEMORY_FLOOR_MB` / `FALLBACK_BUDGET_MB`。

## 可用 worker

`max(1, cpu_count − reserve_cores)`。

## 设计决策

### D1：去掉旧字段兼容

不再识别 `main_process_reserve_mb`、`dispatch_memory_budget_mb`；只认 `memory_floor_mb` / `memory_budget_mb`。

### D2：门面承载全部实现

模块体量小，解析逻辑内联在 `MachineInfo`；不拆空 `core/` 包。
