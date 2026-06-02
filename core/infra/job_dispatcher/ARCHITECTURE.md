# JobDispatcher 架构

**状态：** v0.5.0 API 定案，不兼容旧 `ProcessWorker.run_jobs` / `JobShell` 命名  
**日期：** 2026-06-02

---

## 1. 范围

| 本模块 | 后续集成（本阶段不改） |
|--------|------------------------|
| `core/infra/job_dispatcher/*` | Tag / DataSource / Strategy |

**不保证向后兼容。** 业务方在集成阶段改为 `JobDispatcher` + 新 hooks。

---

## 2. 心智模型

```text
jobs[] → [to_executable_job?] → executor.execute(payload) → on_result
```

| 输入 | 必填 | 说明 |
|------|------|------|
| `jobs` | 是 | `List[Job]`，`job_id` + `payload` |
| `execute` | 是 | Worker 侧纯计算 |
| `on_result` | 是 | 主进程收报告 + 进度 |
| `to_executable_job` | 否 | `None` 时 payload 直送 execute |

**应用层职责：** 一 job 一股还是多股、bulk IO、写库攒批 — 均在 jobs 构建与 hooks 内完成，不在 infra 做 CHUNK / module_name。

---

## 3. 组件

| 组件 | 职责 |
|------|------|
| **JobDispatcher** | prepare 编排、有界 ready 队列、按 ExecuteMode 调度 |
| **JobExecutor** | process/thread 池 `submit` + `shutdown` |
| **WorkerProbe** | `max_workers="auto"` 解析（CPU + reserve + cap） |
| **JobDispatchSettings** | worker、execute_mode、并行度、prefetch、batch_size |

---

## 4. ExecuteMode

| 模式 | 行为 | 状态 |
|------|------|------|
| **QUEUE** | 有空位 prepare/submit；完成 1 补 1 | 已实现 |
| **BATCH** | 每批 `batch_size` 个；批内并行、批间串行 | 已实现 |
| **ELASTIC** | 探针动态调池 | 预留 |

---

## 5. 日志

`run(jobs, run_name=...)` 的 `run_name` 作为本次 run 的日志前缀（与 `module_name` 无关）。

---

## 6. 相关文档

- [docs/API.md](./docs/API.md)
- [docs/DECISIONS.md](./docs/DECISIONS.md)
- [../worker/docs/ARCHITECTURE.md](../worker/docs/ARCHITECTURE.md)
