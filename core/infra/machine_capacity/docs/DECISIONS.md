# Machine Capacity — 设计与决策

**模块：** `infra.machine_capacity` · **版本：** `0.2.1`

**最低支持核心版本：** `>=0.5.0`

本文记录本模块的设计目标、方案思路与拍板决策。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

- **能力探测**：获取当前用户机器的能力信息（内存、CPU、硬盘类型等），给大性能需求的任务提供规划信息。
- **预算语义明确**：worker 内存预算与可用核数有清晰、可预测的计算规则，且在缺少 psutil 等依赖时有兜底。

## 方案与思路

- **内存预算语义**：
  1. `memory_floor_mb`：机器必须保留的空闲内存，不参与 worker 预算；`auto` 时按总量/可用估算（见 `MachineInfo` 类常量）。
  2. `memory_budget_mb`：显式则直接用（下限 `MIN_BUDGET_MB`）；`auto` 时为 `(available − floor) * worker_memory_fraction`，夹在 `MIN_BUDGET_MB`–`MAX_BUDGET_MB`。
  3. 无 psutil 时：floor / budget 分别回落到 `FALLBACK_MEMORY_FLOOR_MB` / `FALLBACK_BUDGET_MB`。
- **可用 worker**：`max(1, cpu_count − reserve_cores)`。
- **配置字段收敛**：去掉旧字段兼容，只认 `memory_floor_mb` / `memory_budget_mb`（见下文 DEC-01）。
- **模块形态**：体量小，解析逻辑内联在门面 `MachineInfo`，不拆空 `core/` 包（见下文 DEC-02）。

---

## DEC-01：D1：去掉旧字段兼容

不再识别 `main_process_reserve_mb`、`dispatch_memory_budget_mb`；只认 `memory_floor_mb` / `memory_budget_mb`。

---

## DEC-02：D2：门面承载全部实现

模块体量小，解析逻辑内联在 `MachineInfo`；不拆空 `core/` 包。

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
