# JobDispatcher 架构（定案）

**状态：** 框架实现中，**不兼容**旧 `ProcessWorker.run_jobs` 队列 pipeline  
**日期：** 2026-05-28

---

## 1. 范围

| 改 | 不改（本阶段） |
|----|----------------|
| `core/infra/job_dispatcher/*` | Tag / Strategy / 其它业务方 |
| `core/infra/worker/*`（运行时收薄、旧 API 废弃） | db engines 大迁移 |

**不保证向后兼容。** 业务方在集成阶段改为 `JobDispatcher` + hooks。

---

## 2. 职责

```text
JobShell[]  ──on_stage_job──►  StagedJob  ──JobExecutor.submit──►  execute(payload)
                                                                      │
                                                              JobReport / data
                                                                      │
                                                              on_report（主进程）
```

| 组件 | 职责 |
|------|------|
| **JobDispatcher** | pending / ready 有界队列、自动填池（原 ProcessWorker QUEUE）、stage / report 钩子编排 |
| **JobExecutor** | 多进程 / 多线程 `submit` + `shutdown`；`max_workers` / `execute` 仅在此层 |
| **infra.worker** | 逐步收为运行时辅助（`invoke_execute`、TaskType、`resolve_max_workers` 逻辑迁至 dispatcher） |

---

## 3. Hooks

- `on_stage_job(shell) -> StagedJob` — 主进程装填（IO）
- `on_report(report)` — 主进程回收（IO）
- `on_release_staged(staged)` — 可选 cleanup
- `execute` — 绑定在 `create_job_executor(...)`，不在 `JobDispatcher` 重复配置

---

## 4. 配置

- `DispatchConfig`：`prefetch_ahead`、`ready_queue_limit`、`fill_strategy`（规划）、`batch_size` / `chunk_size`（规划）
- `create_job_executor(backend, max_workers='auto'|int, execute, module_name=...)`
- **当前实现：** 仅 `fill_strategy=queue`（有界 ready + 池满填池 + 完成即补）

---

## 5. Inject 与 payload（Tag 定案 · 基线）

| 项 | 定案 |
|----|------|
| 主进程 | `on_stage_job` 读库 → `_inject.slot_data` **inline** 进 payload |
| 子进程 | 无 DB；`on_report` 写库 |
| spill | **暂不启用**；`spill.py` 保留作 profiling 后的可选路径 |
| pickle | **先不优化**；inline 暴力传参，用 benchmark 衡量后再对症下药 |

---

## 6. 填池策略（规划 · 与 profiling 一并落地）

三种模式控制的是 **何时 `on_stage_job`（IO）** 与 **何时 `submit`（pickle/IPC）**，与 `max_workers` 正交。

```text
                    stage IO          submit / in-flight
QUEUE (当前)        有空位就装填       池未满即 submit；完成 1 补 1
BATCH               每批前装填 N 个    批内并行；批间串行，整批结束再下一批
CHUNK (中间态)      累计完成 N 再装填   in-flight ≤ max_workers；完成 N 再 bulk stage/submit N
```

| 模式 | 适用 | 对 IO / pickle 的预期 |
|------|------|------------------------|
| **QUEUE** | 低延迟、payload 小 | stage/submit 最碎；pickle 次数 ≈ job 数 |
| **BATCH** | 控峰值内存、checkpoint 对齐 | 每批一次 bulk stage；批间可 CHECKPOINT（DuckDB） |
| **CHUNK** | payload 大、stage 贵 | 减少 `on_stage_job` 调用频率；pickle 可成批发生 |

**CHUNK 与 QUEUE 区别（直觉）：**

- QUEUE：完成 **1** 个 → 往往就 stage **1** 个、submit **1** 个（在 cap 内）。
- CHUNK：in-flight 仍 ≤ `max_workers`；但 **累计完成 `chunk_size`** 后才 stage 下一组 `chunk_size` 个，避免 IO/pickle 过于细碎。

**后续一并优化（不在本阶段实现）：**

1. profiling：inline payload 大小、`pickle.dumps` 耗时、stage IO、总 job 时间（见 `TagRunProfile`、`NTQ_TAG_PROFILE=1`）  
2. **Tag batch stage IO**：`kline.load_batch` + `fetch_prior_tag_values_batch`，chunk 20–100；benchmark 见 `core/modules/tag/tools/tag_read_benchmark.py`；**定案与数据见 [../../modules/tag/docs/DECISIONS.md](../../modules/tag/docs/DECISIONS.md) 决策 3**  
3. 实现 `FillStrategy.BATCH` / `CHUNK`（与 batch stage 编排对齐，非替代 bulk SQL）  
4. 视 profiling 再选：spill / parquet / shared memory（见 `spill.py`）  
5. Tag `performance` 与 `DispatchConfig` 对齐（如 `stage_batch_size`、`chunk_size`）  
6. report 侧 **`save_batch` 攒批**（已实现 `TagReportSaveBuffer`，`performance.save_batch_size` 默认 5000）  

---

## 7. 相关文档

- [../worker/docs/ARCHITECTURE.md](../worker/docs/ARCHITECTURE.md)
- [../db/engines/ARCHITECTURE.md](../db/engines/ARCHITECTURE.md) — DuckDB inject/report 定案（集成阶段）
