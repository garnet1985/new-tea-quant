# 测试用例 — `infra.machine_capacity`（模块根）

**模块：** `infra.machine_capacity`  
**覆盖版本：** `0.2.1`  
**本文件位置：** `__test__/`

---

## Scope

验证门面 `MachineInfo` 与 `contracts` / `types`（公开业务逻辑）。  
本模块无独立 `core/`；行为单测与 API 同目录，但 TEST_CASES 只索引业务/公开 case。

## 边界

**负责**

- 包根仅导出 `MachineInfo`
- 容量解析、可用 worker、并行上限解析

**不负责**

- BacktestEngine 调度 / 进程池

**允许的测试类型（本目录）：** `api`、`behavior`

---

## Scenario：facade_api

| Case | 文件 | 说明 |
|------|------|------|
| `test_facade_exported_only` | `test_api.py` | `__all__`；无包根 MachineCapacity |
| `test_types_machine_capacity` | `test_api.py` | types ≡ contracts |
| `test_get_capacity_explicit_budget` | `test_api.py` | 显式预算快照 |
| `test_parse_max_parallel_jobs_cap` | `test_api.py` | None / auto / 数值 |
| `test_get_disk_type_returns_known_token` | `test_api.py` | ssd/hdd/unknown |
| `test_linux_block_name` | `test_machine_capacity.py` | sysfs block 名解析 |

## Scenario：capacity_resolve

| Case | 文件 | 说明 |
|------|------|------|
| `test_get_reserve_cores_defaults_and_clamps` | `test_machine_capacity.py` | 默认 / 非法回落 |
| `test_resolve_memory_budget_explicit` | `test_machine_capacity.py` | 显式 budget+floor |
| `test_get_available_workers` | `test_machine_capacity.py` | cpu − reserve |
| `test_worker_pool_budget_mb` | `test_machine_capacity.py` | 至少 1 |
| `test_parse_max_parallel_jobs_cap_edges` | `test_machine_capacity.py` | 边界值 |
