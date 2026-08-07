# Machine Capacity API 文档

**版本：** `0.2.0`  
**最低支持核心版本：** `>=0.4.0`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。  
> 所列门面入口须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `MachineInfo`；`MachineCapacity` 从 [`contracts.py`](./contracts.py) 导入，或经 `MachineInfo.types`。

---

## MachineInfo

**描述：** 机器容量门面类（Facade）— 从 `performance` 字典解析 CPU / 内存预算与可用 worker

### types

**描述：** 与 `contracts` 同源的类型挂载点（`MachineCapacity`）

#### get_capacity

`MachineInfo.get_capacity(performance: dict) -> MachineCapacity`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 综合 CPU、预留核、内存预算，返回容量快照
- **举例：**

```python
from core.infra.machine_capacity import MachineInfo

capacity = MachineInfo.get_capacity(performance)
workers = MachineInfo.get_available_workers(capacity)
```

#### get_cpu_count

`MachineInfo.get_cpu_count() -> int`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 逻辑 CPU 数（至少 1）

#### get_reserve_cores

`MachineInfo.get_reserve_cores(performance: dict) -> int`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 从 `performance.reserve_cores` 解析预留核（默认 1，非法值回落默认）

#### resolve_memory_budget

`MachineInfo.resolve_memory_budget(performance: dict) -> tuple[float, float]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 返回 `(budget_mb, floor_mb)`；显式 `memory_budget_mb` 或 `auto`（见 DESIGN）

#### resolve_memory_floor

`MachineInfo.resolve_memory_floor(performance: dict) -> float`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 机器保留空闲内存底线；显式或 `auto`

#### get_available_workers

`MachineInfo.get_available_workers(capacity: MachineCapacity) -> int`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** `cpu_count − reserve_cores`（至少 1）

#### worker_pool_budget_mb

`MachineInfo.worker_pool_budget_mb(capacity: MachineCapacity) -> float`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 进程池可用预算；对 `capacity.memory_budget_mb` 夹紧到至少 1 MB

#### parse_max_parallel_jobs_cap

`MachineInfo.parse_max_parallel_jobs_cap(raw) -> int | None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 解析并行 job 上限；`None` / `""` / `"null"` / `"auto"` / 非法 → `None`

#### virtual_memory_mb

`MachineInfo.virtual_memory_mb() -> tuple[float | None, float | None]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 本机 `(total_mb, available_mb)`；无 psutil 或失败时 `(None, None)`

---

## contracts（`core.infra.machine_capacity.contracts`）

| 符号 | 说明 | 状态 |
|------|------|------|
| `MachineCapacity` | 冻结 dataclass：cpu_count / memory_budget_mb / memory_floor_mb / reserve_cores | `beta` |
