# Decision 004: Calendar Slice Runtime Planner（auto 宽度 + preload 动态调节）

## Status

**Accepted**（2026-06；与 ADR-003 Reader/Compute v2 配套）

## Context

calendar_slice v2 已分离 Reader / Compute，并通过 `reader_workers` 并行 load 取得明显 wall time 收益。下一阶段需要：

1. **用户少配 knob**：`slice_open_days`、`reader_workers`、preload 深度支持 `auto`
2. **内存 budget 系统自算**：复用 `dispatch_planner.resolve_memory_budget_mb`，用户不可改
3. **job 内 inline 探针**：首片 + prewarm 第二片，得到 `T_io` / `T_compute` / `mb_per_slice`
4. **运行时采样调节 preload**：每片 `SliceDone` 后根据 RSS 与 budget 升降 preload，**不超过 job 初始 ideal ceiling**

## Decision

### 1. 语义：`min_required_records` 双语义

| `execution_mode` | `data.min_required_records` 含义 |
| --- | --- |
| `entity_timeline` | 实体 K 线条数不足则跳过 scan |
| `calendar_slice` | **slice 宽度下限**（开市日）；per-stock 片内仍按 lookback 跳过 scan，**不丢整片** |

auto 宽度硬区间（安全默认，将来可动态化）：

```text
floor = max(min_required_records, MIN_PLANNER_SLICE_OPEN_DAYS)   # MIN_PLANNER = 50
ceiling = MAX_SLICE_OPEN_DAYS                                     # 252
```

- `min_required_records > ceiling` → **拒绝执行**
- `min_required_records < 50` → auto clamp 到 50

### 2. Worker 与 preload 分离

```text
total_process_cap = resolve_pipeline_workers(...)     # 如 9（留 1 核给系统）
reader_workers      = min(IO 并行需求, process_cap - 1)   # DuckDB 固定 1
compute             = 1 进程（固定）
```

**内存压力主 knob 是 preload slice 数**，不是 reader 进程数：

| 代码字段 | 含义 |
| --- | --- |
| `enumerator.calendar_slice.queue_depth` | `payload_q` 容量 = **最多几份 SlicePayload 等待 compute** |
| orchestrator `ahead_limit` | 最多提前 dispatch 几个 load；**绑定 `current_preload_depth`，不再绑定 `reader_workers`** |

carry / lookback 状态 **不计入** preload budget：

```text
peak_mb ≈ carry_mb + compute_current_mb + preload_count × mb_per_slice
```

### 3. Job 内 `CalendarSliceRuntimePlan`（内存变量）

job 开始时创建，结束时销毁；**不持久化**。

| 字段 | 说明 |
| --- | --- |
| `slice_open_days` | 解析后的片宽 |
| `memory_budget_mb` | auto 预算 |
| `ideal_preload_ceiling` | 探针推断的 preload 上限（本 job 内回升不超过此值） |
| `current_preload_depth` | 当前允许 preload 片数（= runtime `ahead_limit` / 有效 queue 调度深度） |
| `reader_workers` | 并行 reader 进程数 |
| `mb_per_slice` | 滚动平均 RSS / 片 |

### 4. Inline 探针（job 启动）

1. 解析 `slice_open_days`（auto 时用 floor 宽度做 parent IO 粗探，或首片 metrics  refine）
2. spawn Reader + Compute
3. 首片 / 次片执行时记录 `SlicePayload.load_elapsed_ms`、`SliceDone.compute_elapsed_ms`
4. 由 `T_io / T_compute` 得 **ideal_preload_ceiling**，再被 memory budget clamp
5. 首片结果 **计入 enum 产出**（非 throwaway）

### 5. 运行时采样（每 `SliceDone` 固定一次）

1. 采样 job 树 RSS（orchestrator + reader + compute 子进程）
2. 对比 `memory_budget_mb`
3. 紧张 → `current_preload_depth -= 1`（必要时暂不再 dispatch 新 load，等 queue 消化）
4. 富裕且 `current < ideal_preload_ceiling` → `current += 1`
5. **v1 不动态改 `slice_open_days`**（replan 复杂度高）

### 6. DuckDB

稳定优先：`reader_workers = 1`；仅调 preload 深度与 slice 宽度。

### 7. Settings（用户面）

```python
"simulation": {
    "execution_mode": "calendar_slice",
    "slice_open_days": "auto",   # 或整数
},
"enumerator": {
    "calendar_slice": {
        "reader_workers": "auto",    # 或整数
        "queue_depth": "auto",       # 或整数；auto = 由 plan 决定
        "prefetch_enabled": True,
    },
},
```

`memory_budget_mb` **不出现在用户 settings**。

## Consequences

- orchestrator 需在 dispatch 侧门控 preload，而非仅依赖固定 `Queue(maxsize)`
- `SliceDone` 携带 `compute_elapsed_ms` 供探针与 metrics
- 现有手动 `reader_workers=4` 仍可用；`auto` 为推荐默认

## References

- [ADR-003](./003-calendar-slice-enumerator.md)
- [`dispatch_planner.py`](../../../../infra/worker/dispatch_planner.py)
- [`experiments/calendar_slice_planner/`](../../../../../experiments/calendar_slice_planner/)
