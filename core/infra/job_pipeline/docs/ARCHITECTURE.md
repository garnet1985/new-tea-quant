# JobPipeline 架构

**状态：** v0.1.0 — `job_pipeline`  
**日期：** 2026-06-03

---

## 1. 目录结构

```text
core/infra/job_pipeline/
  __init__.py          # 对外公共 API（JobPipeline、types、WorkerProbe …）
  types.py             # Job / JobContext / JobReport 等共享类型
  pipeline/            # 编排层
    settings.py        # JobPipelineSettings
    hooks.py           # execute / on_result / on_release 协议
    runner.py          # JobPipeline（QUEUE / BATCH 调度）
  runtime/             # 执行后端
    executor.py        # JobExecutor 协议 + create_job_executor
    pool.py            # ProcessJobExecutor / ThreadJobExecutor
    invoke.py          # 子进程/线程内 execute 包装
  profile/             # worker.json 配置
    constants.py       # 默认值、策略 settings 应忽略的键
    probe.py           # WorkerProbe（CPU / reserve / cap）
    resolver.py        # profile 合并、dispatch 配置解析
  docs/
  __test__/
```

**心智模型：** `pipeline` 负责「怎么跑」；`runtime` 负责「在哪跑」；`profile` 负责「跑几个 worker、dispatch 默认参数」。

---

## 2. 范围

| 本模块 | 业务职责 |
|--------|----------|
| `core/infra/job_pipeline/*` | 并行执行、进度、失败阶段 |
| Tag / Strategy 等 | load 数据、算、写库 — 均在 `execute` / `on_result` 或 run 前建 `Job` |

---

## 3. 执行流

```text
jobs[] → JobContext(job_id, payload, run_name) → execute(context) → on_result
```

| 输入 | 必填 | 说明 |
|------|------|------|
| `jobs` | 是 | `List[Job]` |
| `execute` | 是 | 子进程/线程；load 与计算由使用方在 context 内完成 |
| `on_result` | 是 | 主进程收报告 |
| `on_release` | 否 | 单 job 结束后的可选清理 |

---

## 4. ExecuteMode

| 模式 | 行为 | 状态 |
|------|------|------|
| **QUEUE** | 完成 1 补 1 | 已实现 |
| **BATCH** | 批内并行、批间串行 | 已实现 |
| **ELASTIC** | 动态 admission | 未实现 |

---

## 5. 行为说明

- **execute 抛错**：记入 `DispatchResult.failures`，**不**调用 `on_result`。
- **execute 返回 `success=False`**：走 `on_result`，计入 `failed`。
- **`on_release`**：每个 job 的 future 结束后调用（含失败）。

---

## 6. 相关文档

- [docs/API.md](./API.md)
- [docs/DECISIONS.md](./DECISIONS.md)
