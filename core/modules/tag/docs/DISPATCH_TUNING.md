# Tag 调度规划（entities / workers）

**实现：** `dispatch_planner.py` + `tag_dispatch_probe.py`  
**入口：** `TagManager._run_execute_pipeline`

---

## 流程（默认 `entities_per_job: auto`）

```text
1. 探针：子进程跑 1 个 job（默认 20 股，与生产相同 stage+算）
2. 采样 worker RSS 峰值 + pickle 体积 → mb_per_entity（× safety_factor）
3. 规划：可用内存预算 + CPU → entities_per_job、max_workers（封顶/保底）
4. 按规划 _build_jobs → 全量 JobDispatcher.run
```

中途动态取样（ELASTIC）**未做**；探针一次通常足够，且避免与跑批中抢锁。

手写 `entities_per_job` 或 `mb_per_entity_staged` 时 **跳过探针**；`dispatch_probe: false` 可关闭。

---

## 目标

| 目标 | 手段 |
|------|------|
| **效率** | 每 job 多股 bulk stage（`entities_per_job` 足够大，dispatch 次数少） |
| **稳定** | 限制 **in-flight 子进程 × 单 job 内存**，避免 OOM |
| **简单** | 默认 `"auto"`，显式配置可覆盖 |

---

## 两层划分

```text
全量 entities
    │  entities_per_job（bulk 分组）
    ▼
dispatch_jobs ≈ ceil(entities / entities_per_job)
    │  max_workers（进程池并行度）
    ▼
同时 in-flight ≤ max_workers（QUEUE + prefetch≈1）
```

### 1. `entities_per_job`（bulk 批大小）

| 来源 | 行为 |
|------|------|
| 整数 | 直接用，夹在 `[entities_per_job_min, entities_per_job_max]`（默认 10–200） |
| `"auto"` / 未配置 | 探针实测 `mb_per_entity` 后按内存预算反推 |
| 调试 | `TagManager._DEBUG_ENTITIES_PER_JOB` 强制覆盖 |

**auto 公式（粗算）：**

```text
memory_budget_mb ≈ available_ram × worker_memory_fraction − main_process_reserve_mb
per_job_mb = memory_budget_mb / cpu_workers
entities_per_job = clamp(floor(per_job_mb / mb_per_entity_staged), min, max)
```

- 默认走 **探针**（`tag_dispatch_probe`）；探针失败时用代码默认 `0.25` MB/股
- 手写 **`mb_per_entity_staged`** 则跳过探针，直接用该值

### 2. `max_workers`（进程数）

```text
cpu_workers = WorkerProbe.resolve("auto")   # cpu − reserve_cores
memory_workers = floor(memory_budget_mb / (entities_per_job × mb_per_entity))
max_workers = min(cpu_workers, memory_workers)
```

- CPU 侧：为 OS + 主进程 `on_result` 留 `reserve_cores`（默认 1）
- 内存侧：保证「并行 job 数 × 单 job staged 体积」不超过预算

### 3. `prefetch_ahead`

- Tag 默认 **1**（`stage_in_worker` 下 ready 队列 payload 轻，不必堆大 prefetch）
- 可在 `performance.prefetch_ahead` 覆盖

---

## `settings.performance` 字段

| 字段 | 默认 | 说明 |
|------|------|------|
| `entities_per_job` | `"auto"` | 整数或 `"auto"` |
| `max_workers` | `"auto"` | 整数 / `"auto"`；最终可能被内存 cap |
| `reserve_cores` | `1` | auto worker 时为主进程留核 |
| `max_workers_cap` | — | auto 上限 |
| `prefetch_ahead` | `1` | QUEUE ready 窗口 |
| `dispatch_memory_budget_mb` | `"auto"` | 固定 MB 或按可用内存算 |
| `worker_memory_fraction` | `0.65` | 可用内存中给 worker 池的比例 |
| `main_process_reserve_mb` | `512` | 主进程写库 / 缓冲预留 |
| `dispatch_probe` | `true`（implicit） | `false` 关闭探针 |
| `dispatch_probe_entities` | `20` | 探针 job 股数 |
| `dispatch_probe_safety_factor` | `1.25` | 探针 MB/股 安全系数 |
| `mb_per_entity_staged` | — | 手写则跳过探针 |
| `entities_per_job_min` / `_max` | `10` / `100` | auto 夹紧范围 |
| `stage_in_worker` | `true` | 子进程 bulk stage |
| `save_batch_size` | `5000` | 主进程写 tag_values 攒批 |

---

## 日志

每次 run 开头一行 **「Tag 调度规划」**，含 `dispatch_jobs≈`、`workers`、内存预算、单 job 估算 MB。  
若 `entities_per_job` 过小或 workers 被内存收紧，会打 **WARNING**。

---

## 调参建议

| 现象 | 调整 |
|------|------|
| wall ~60s、`dispatch_jobs` 五千+ | 增大 `entities_per_job` 或减小 `mb_per_entity_staged`（auto 过小） |
| OOM / 子进程被杀 | 增大 `mb_per_entity_staged`、减小 `entities_per_job_max`、或设 `max_workers` 为较小整数 |
| CPU 空闲、内存够 | `entities_per_job: 100~150`，`max_workers: "auto"` |
| 重 tag（多数据源、长窗口） | `mb_per_entity_staged: 0.15~0.3`，`entities_per_job: 50` |

---

## 与 JobDispatcher 边界

- **infra** 只负责 `JobContext` + 进程池 + `max_workers` / `prefetch`（来自 `JobDispatchSettings`）
- **Tag** 负责 `entities_per_job` 分组与内存规划（本模块）
- 不在 Dispatcher 做 ELASTIC / 主进程 prepare
