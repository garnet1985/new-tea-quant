# Timeline 模式执行规范

**版本**：`0.1.0`  
**模块**：`core.modules.backtest_engine.core.timeline_based`  
**状态**：实施中

---

## 1. 定位

Timeline 回测引擎负责 **端到端调度**（不含 Tag/Strategy 业务逻辑）：

```text
jobs 输入 → Probe → Plan → Split batches → Monitor 配置 → Execute pipeline → Report
```

调用方（Tag / Strategy 枚举器）只需按约定准备好 **entity 级 jobs** 并交给引擎；**不再**在业务层自行做 dispatch probe、resolve_dispatch_plan、JobPipeline 调度。

`infra.worker` / `infra.job_pipeline` 仅作只读参考，新代码 **不得 import**。

---

## 2. 组件职责

| 组件 | 文件 | 职责 |
|------|------|------|
| `TimelinePlanner` | `planner.py` | Step 1–5：capacity → probe → settle → split → monitor 配置 |
| `Probe` | `probe.py` | 子进程试跑，估算 `mb_per_entity`（及粗粒度时间） |
| `TimelineRunMonitor` | `pipeline/monitor.py` | 运行期采样汇总，**仅调整 in-flight workers** |
| `TimelineExecutePipeline` | `pipeline/execute_pipeline.py` | 编排 plan + monitor + executor（进程池 QUEUE） |
| `TimelineExecutor` | `executor.py` | 进程池执行（逐步迁入 pipeline） |
| `TimelineExecutorDuckDB` | `executor_duckdb.py` | DuckDB scope 分离包装 |

---

## 3. Probe：初值计划（简单可靠）

### 3.1 输出

| 字段 | 用途 |
|------|------|
| `mb_per_entity` | Plan 内存约束、Monitor 内存估算 |
| `sec_per_entity` | 粗日志 / 可选 tie-break（v1 不参与选 workers） |
| `wall_sec`, `entities_sampled` | 诊断 |

### 3.2 Plan 算法（`_settle_plan`，已实现）

**原则**：实验推荐值优先，内存不够再 `memory_capped`；**不在 probe 做复杂 F/m 双点拟合**。

1. **entities_per_job（epj）**  
   - 显式配置 → `settings`  
   - `auto` → 实验推荐（stock_based v1, 2026-06-22）：  
     - `<200` → 5  
     - `200–1000` → 10  
     - `≥1000` → 5  
   - 若 `epj × mb_per_entity > memory_budget` → 降至 budget 可容纳的最大 epj  

2. **max_workers（初值 / 上限）**  
   - 显式配置 → `settings`  
   - `auto` → 实验推荐：`<200`→1，`200–1000`→2，`≥1000`→min(4, cpu−reserve)  
   - 若 `job_budget × workers > available_memory` → `memory_capped` 降低 workers  

3. **prefetch_ahead**  
   - 从 `performance` 读取，默认 `1`  

4. **mb_per_entity（auto）**  
   - 探针结果 > `mb_per_entity_staged` > 显式 epj 时默认 1.0  
   - `auto` 且无探针且无 staged → **报错**  

**epj 在全 run 内固定**，Monitor **不得**修改。

---

## 4. Monitor：运行期动态调整

### 4.1 动机

- 各 batch 数据量差异大（缺数股占用小），**per-job 采样易高估承载力**  
- 应在 **更大 context** 汇总后再决策  

### 4.2 可调 / 不可调

| 可调 | 不可调 |
|------|--------|
| `current_in_flight`（有效 worker 槽位） | `entities_per_job` |
| admission 门控（QUEUE submit） | 已提交 batch 内容 |

### 4.3 Workers 上限（两层）

```text
max_workers_plan      # settle_plan 产出（目标上限）
max_workers_hard_cap  # min(plan, cpu_cap, settings.max_workers)
current_in_flight     # Monitor 运行时旋钮，∈ [1, hard_cap]
```

### 4.4 评估触发（汇总，非 per-job 调参）

每个完成的 job **只记账**（`record`）；满足窗口条件后 **才** `evaluate`：

| 参数 | 默认 | 说明 |
|------|------|------|
| `evaluation_job_interval` | 10 | 每 N 个完成 job |
| `evaluation_entity_interval` | 50 | 每 M 个完成 entity |
| `evaluation_requires_both` | false | true 时 N **且** M 同时满足 |
| `warmup_jobs` | 3 | 前 K 个 job 只采样不调参 |

**汇总指标（entity 加权）**：

```text
mb_per_entity_hat = Σ peak_rss_mb / Σ entities_count   # 若有 RSS；否则用 probe mb
wall_per_entity_hat = Σ wall_sec / Σ entities_count
```

可选 **F + m**（Monitor 内，非 Probe）：

```text
m_hat = wall_per_entity_hat
F_hat = probe 常数或上一窗口指数平滑
T_job_hat = F_hat + epj × m_hat
```

v1：**以内存为主调 in_flight**；F/m 可先打日志，v2 再参与升并发。

### 4.5 调参策略（保守）

- **降**：`mb_hat × epj × in_flight > available × 0.85` → `in_flight -= 1`  
- **升**（可选）：内存 `< available × 0.60` 且连续 2 个 window 成立 → `in_flight += 1`  
- **永不**超过 `max_workers_hard_cap`  
- admission：`in_flight_limit + prefetch_ahead` 计入在飞 payload 上限（与旧 QUEUE 语义一致）

---

## 5. Execute Pipeline

`TimelineExecutePipeline.run()` 编排：

```text
1. TimelinePlanner.plan_jobs()     → plan, batches, monitor_config
2. ExecutionContext.create()
3. TimelineRunMonitor(plan, config)
4. TimelineExecutor.execute(..., monitor=monitor)   # 实施中：QUEUE + monitor hook
5. TimelinePipelineResult            → plan + execution + monitor stats
```

DuckDB：由 `TimelineExecutorDuckDB` 或 pipeline 内 scope 分支包装，**与标准执行路径分离**。

---

## 6. Job 报告最小字段（引擎契约）

Monitor / 进度依赖 batch 完成时上报：

| 字段 | 必需 |
|------|------|
| `entities_count` | 是 |
| `wall_sec` 或 `execute_sec` | 是 |
| `peak_rss_mb` | 否（有则 Monitor 更准） |
| `success` | 是 |

---

## 7. 实施顺序（小步，逐步 review）

| 阶段 | 内容 | 状态 |
|------|------|------|
| A | 文档 + `_settle_plan` 算法 | ✅ plan 已对齐实验+内存 |
| B | `pipeline/` 骨架 + monitor 配置 | 当前 |
| C | Executor QUEUE 填池（静态 `max_workers`） | 待做 |
| D | Monitor `record` / `evaluate` + 动态 `in_flight` | 待做 |
| E | DuckDB scope 接入 pipeline | 待做 |
| F | `BacktestEngine` Facade | 待做 |
| G | Tag / Strategy 集成 | 待做 |

---

## 8. 相关实验数据

- `devtools/performance/strategy/enumerator/reports/v1/stock_based_v1_zh.md`  
- epj=5 为 workers=1 时 wall time 最优；workers 多进程矩阵 Phase 2 仍为启发式上限  

---

## 9. 相关文档

- [DECISIONS.md](./DECISIONS.md) — 决策 10–14  
- [SCHEDULER_SPEC.md](./SCHEDULER_SPEC.md) — 模块总规范  
