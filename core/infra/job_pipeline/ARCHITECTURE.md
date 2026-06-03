# JobPipeline 架构

**状态：** v0.7.0 — `job_pipeline`  
**日期：** 2026-06-03

---

## 1. 范围

| 本模块 | 业务职责 |
|--------|----------|
| `core/infra/job_pipeline/*` | 并行执行、进度、失败阶段 |
| Tag / Strategy 等 | load 数据、算、写库 — 均在 `execute` / `on_result` 或 run 前建 `Job` |

---

## 2. 心智模型

```text
jobs[] → JobContext(job_id, payload, run_name) → execute(context) → on_result
```

| 输入 | 必填 | 说明 |
|------|------|------|
| `jobs` | 是 | `List[Job]` |
| `execute` | 是 | 子进程/线程；load 与计算由使用方在 context 内完成 |
| `on_result` | 是 | 主进程收报告 |
| `on_release` | 否 | 单 job 结束后的可选清理 |

主进程若需装填：在 `dispatcher.run()` **之前** 改好 `Job.payload`，或（常见）在 `execute` 里读库。

---

## 3. JobContext

Dispatcher 为每个 submit 构造：

- `job_id`
- `payload`（浅拷贝；注入 `_job_id`）
- `run_name`（本次 `run(..., run_name=)`）

---

## 4. ExecuteMode

| 模式 | 行为 | 状态 |
|------|------|------|
| **QUEUE** | 完成 1 补 1 | 已实现 |
| **BATCH** | 批内并行、批间串行 | 已实现 |
| **ELASTIC** | 动态 admission | 未实现 |

---

## 5. 行为说明

- **execute 抛错**：记入 `DispatchResult.failures`，**不**调用 `on_result`（业务可从 `failures` 或 `failed` 汇总）。
- **execute 返回 `success=False`**：走 `on_result`，计入 `failed`。
- **`on_release`**：每个 job 的 future 结束后调用（含失败），与 `execute` 配对做清理。

---

## 6. 相关文档

- [docs/API.md](./docs/API.md)
- [docs/DECISIONS.md](./docs/DECISIONS.md)
