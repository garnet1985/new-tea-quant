# JobDispatcher 设计决策

**版本：** `0.5.0`

---

## 1. 四输入模型

Dispatcher 只认：`jobs`、`execute(JobContext)`、`on_result`。  
业务分组与 load 数据由应用构建 `Job` 或在 `execute` 内完成。

---

## 2. 废弃 module_name auto

`max_workers="auto"` 由 **WorkerProbe** 解析：`mp.cpu_count() - reserve_cores`（为 OS + 主进程留核）。**auto 不看内存**；内存调节留给 ELASTIC（未实现）。不再读 `worker.json` 的 `module_task_config`。

`run_name` 仅用于日志，与并行度配置无关。

---

## 3. 无 infra 级 CHUNK

原 `FillStrategy.CHUNK` 与 `to_executable_job` 已移除。bulk stage / IO 由 `execute` 或 run 前 payload 形状控制。

---

## 4. ExecuteMode

- **QUEUE**：默认，低延迟流水线
- **BATCH**：控峰值内存、批间 checkpoint 友好
- **ELASTIC**：运行时探针调节 prepare/submit 窗口（见 [docs/DECISIONS.md](./docs/DECISIONS.md) §7 草案）

---

## 5. 大 payload 外部化

不在 infra 实现。若业务需要减轻 pickle/IPC，在 `execute` 内或 payload 约定里自行处理（如 Tag 的 DuckDB Parquet 写缓冲在 `core/modules/tag`）。

---

## 6. ProcessWorker

`ProcessWorker.run_jobs` 已移除。新代码使用 `JobDispatcher`；`ProcessWorker.resolve_max_workers` 转发至 `WorkerProbe`（`module_name` 参数忽略）。

---

## 7. ExecuteMode.ELASTIC（草案 · 未实现）

**TODO：** 实现前需与 Tag profile 对齐验收指标；当前 Tag 瓶颈在 stage 读库，ELASTIC 主要解决 **主进程 prepared payload 堆积 / 内存**，不是 pickle 热点。

### 7.1 与 QUEUE / BATCH 的区别

| 模式 | 填池节奏 | 并行度 |
|------|----------|--------|
| QUEUE | 固定 `max_workers + prefetch_ahead` | 启动时定死 |
| BATCH | 按批 prepare + submit | 批间串行 |
| **ELASTIC** | 每完成 N 个或每个 tick **重新探测**，动态决定 prepare/submit 窗口 | **运行时调节 in-flight 上限** |

ELASTIC 外表仍像 QUEUE（完成即补），差别在 **admission limit 随探针变化**，不是固定 cap。

### 7.2 「动态填充」控什么

三层窗口（由外到内）：

```text
pending jobs
    │  prepare 门控 ← 内存/CPU 探针
    ▼
ready queue（已 prepare、未 submit）
    │  submit 门控 ← in_flight 上限
    ▼
executor in-flight
```

- **prepare 门控**：主进程预装填 payload 时最吃内存；Tag 默认在 worker `execute` 内 stage，ready 队列保持轻 payload
- **submit 门控**：限制同时跑在 worker 里的 job 数（≈ QUEUE 的 in-flight）
- **prefetch**：ELASTIC 下应为 **小值或 0**，避免探针说缩窗口时 ready 里仍堆大 payload

### 7.3 探针输入（复用 infra.worker）

| 信号 | 来源 | 用途 |
|------|------|------|
| CPU 上限 | `WorkerProbe` | `max_in_flight` 硬顶 |
| 主进程 RSS / 预算 | `MemoryMonitor`（已有） | 估算「还能 prepare 几个」 |
| 单 job 内存 | 前 `warmup_jobs` 个 job 平滑估算 | `mem_working_per_job` |
| 系统 available | `psutil` | 预算 auto |

**输出（每轮循环）：**

```python
max_in_flight = clamp(elastic_min, elastic_max, cpu_limit, memory_limit)
max_ready = max_in_flight + elastic_prefetch   # elastic_prefetch 建议 ≤ 1
```

`memory_limit` 示例：`floor((budget - rss - in_flight * mem_per_job) / mem_per_job)`。

### 7.4 与 ProcessPoolExecutor 的限制

标准库 **进程池 `max_workers` 创建后不可缩容**；子进程 idle 仍占内存。因此 v1 ELASTIC 应是：

- 池子按 **`elastic_max_workers`（probe 上限）** 一次建好
- 运行时只做 **submit 节流**（under-utilize），不指望动态 kill 空闲 worker
- 真·缩容需自定义 Executor 或换 worker 模型 → **后续**

### 7.5 建议 settings 扩展

```python
elastic_min_workers: int = 1
elastic_max_workers: Union[str, int] = "auto"   # WorkerProbe
memory_budget_mb: Union[float, str] = "auto"    # 复用 worker 公式
warmup_jobs: int = 4                            # 估算 mem/job
probe_every_n_completions: int = 1              # 再评估频率
elastic_prefetch: int = 0                       # 默认不预取大 payload
```

### 7.6 实现位置

- 新模块 `elastic_controller.py`（或 `admission.py`）：`ElasticAdmission` 封装探针 + limit 计算
- `JobDispatcher._run_elastic()`：与 `_run_queue` 同骨架，limit 来自 controller
- **不** 再引入 Orchestrator 第二条 pipeline；可 **import** `MemoryMonitor`，不复制逻辑

### 7.7 何时值得做

- **值得：** payload 大、ready 队列常顶满、OOM 或 swap 风险（大场景 Tag、Strategy 大因子）
- **可后置：** 当前 Tag profile 主瓶颈是 stage **读库**；优先 **batch stage IO**，ELASTIC 作内存保险

**验收（将来）：** 同等 job 数下 RSS 峰值下降；wall 不明显劣于 QUEUE；内存紧时 in-flight 自动降到 `elastic_min`。
