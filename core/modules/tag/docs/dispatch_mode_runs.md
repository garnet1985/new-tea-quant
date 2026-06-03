# Tag × JobDispatcher 调度模式实测记录

## 约定模式（2026-06-03，后续默认）

| 环节 | DuckDB | MySQL / PostgreSQL |
|------|--------|---------------------|
| **Stage / 读** | 子进程 `execute` 内 stage（默认） | 同左 |
| **算** | 子进程 Worker | 同左 |
| **写** | `on_result` 攒批 → 达 `save_batch_size` 写 tag | 同左（**直接 `save_batch`**） |
| **仅 DuckDB 额外** | 主进程 **suspend**；缓冲过大 **Parquet spill**；池结束后 **digest** 写 tag（文件锁） | 无 suspend / spill / digest |

推荐 CLI（全量 ~5850、`entities_per_job=100`）：

```bash
python -m core.modules.tag activity-ratio20 -v \
  --entities-per-job 100 --max-workers 9 --stage-in-worker
```

- 代码：`TagManager._backend_is_duckdb()` → 仅 DuckDB 走 `duckdb_stage_spill`；其余库 `TagReportSaveBuffer` 边算边写。
- 试验性多波次 digest、7 读 2 算等已废弃，不再扩展。

**实测（activity-ratio20 · 5847 entities · 100/job · 9 workers · stage_in_worker）：**

| 库 | wall | 备注 |
|----|------|------|
| DuckDB + Parquet spill | ~26–38s | 视收尾写库、锁状态 |
| **MySQL 直接 save_batch** | **~26s** | 2026-06-03，59/59 成功，506677 rows |

---

**场景：** `activity-ratio20` · DuckDB · 全量 ~5850 股  
**环境：** 本地 dev（2026-06-02）

---

## 结论（有效性）

**多股一 job + bulk stage（`entities_per_job=50`）在全量上 wall 约快 26%**，与 1000 股子集上 ~15–18% 同向；**stage 读库是主要收益来源**（profile 见下），pickle 单 job 变大但总 payload 相近、非 wall 热点。

| 对比 | dispatch_jobs | entities | tag_values | save_batch | wall |
|------|---------------|----------|------------|------------|------|
| **基线** 1 股/job · QUEUE | 5850 | 5850 | 506677 | 102 | **63.08s** |
| **bulk stage** 50 股/job · QUEUE | 117 | 5850 | 506677 | 102 | **46.56s** |
| **Δ** | −98% jobs | 同 | 同 | 同 | **−26%** (~16.5s) |

1000 股 debug 子集（同 tag 逻辑）：8.69s → 7.34s（**−15%**）。

---

## 全量 bulk stage（用户确认 2026-06-02 16:25）

```text
Tag jobs 分组: entities=5850, entities_per_job=50, dispatch_jobs=117
Tag计算完成: scenario=activity-ratio20, dispatch_jobs=117, entities=5850,
  成功=117, 失败=0, 写入tag_values=506677, save_batch次数=102, 耗时=46.56秒
```

- `execute_mode=queue`，`max_workers=auto` → 9 workers
- `_DEBUG_ENTITY_LIMIT=None`（全池，无截断）

---

## 基线（1 股/job · JobDispatcher 新 API · 2026-06-02）

```text
Tag计算完成: scenario=activity-ratio20, 总jobs=5850, 成功=5850, 失败=0,
写入tag_values=506677, save_batch次数=102, 耗时=63.08秒
```

---

## Profile（1000 entities · NTQ_TAG_PROFILE=1）

| 指标 | 1 股/job (1000 jobs) | 50 股/job (20 jobs) | 变化 |
|------|----------------------|---------------------|------|
| **wall** | 11.19s | 9.15s | −18% |
| **stage 总** | 6.80s | 3.87s | **−43%** |
| pickle avg/job | 63.6 KB | 2809 KB | ×44（job 数 ÷50） |
| pickle 总量≈ | ~62 MB | ~55 MB | 持平 |
| 未计入 IPC | 0% | 0% | 非热点 |

---

## ExecuteMode.BATCH（dispatcher 批间串行 · 非 bulk stage）

5850 股 · 1 股/job：`execute_mode=batch`, `batch_size=50` → **83.81s**（比 queue 基线慢，预期）。

---

## 复现

```bash
# 全量 bulk stage（当前 tag_manager 默认 entities_per_job=50，无 entity 截断）
python -m core.modules.tag activity-ratio20 -v

# 显式指定
python -m core.modules.tag activity-ratio20 -v --entities-per-job 50

# 对比基线 1 股/job
python -m core.modules.tag activity-ratio20 -v --entities-per-job 1

# profile
NTQ_TAG_PROFILE=1 python -m core.modules.tag activity-ratio20 -v
```

配置项：`settings.performance.entities_per_job`；调试常量 `TagManager._DEBUG_ENTITIES_PER_JOB`（默认 50，设 `None` 则读 settings）。

---

## WorkerProbe auto

`workers = cpu_count - reserve_cores`（本机 10−1=9）。内存不在 auto 限流。

---

## 运行记录表

| 日期 | 形态 | dispatch_jobs | entities | tag_values | save_batch | 耗时(s) | 备注 |
|------|------|---------------|----------|------------|------------|---------|------|
| 2026-06-02 | 1股/job · queue | 5850 | 5850 | 506677 | 102 | **63.08** | 基线 |
| 2026-06-02 | 50股/job · queue · bulk | 117 | 5850 | 506677 | 102 | **46.56** | **−26% wall** |
| 2026-06-02 | 50股/job · queue · bulk | 20 | 1000 | 81874 | 17 | 7.34 | debug 子集 |
| 2026-06-02 | 1股/job · queue | 1000 | 1000 | 81874 | 17 | 8.69 | debug 子集 |
| 2026-06-02 | 1股/job · batch | 5850 | 5850 | 506677 | 102 | 83.81 | dispatcher BATCH，非 bulk |
| 2026-06-02 | elastic | — | — | — | — | — | NotImplementedError |
