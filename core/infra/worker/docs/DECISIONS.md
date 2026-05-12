# Worker 决策记录

**模块版本：** `0.2.0`

---

## 决策 1：同时提供多进程与多线程 Worker

1. **背景（Context）**  
   业务中并存 CPU 密集与 I/O 密集负载，单一并发模型难以兼顾。

2. **决策（Decision）**  
   提供 `ProcessWorker` 与 `MultiThreadWorker` 两套传统 API，并由 `TaskType` 描述任务特征以支持自动推导并发度。

3. **理由（Rationale）**  
   进程绕过 GIL 适合计算；线程适合 I/O；接口保持「提交 jobs → run」心智。

4. **影响（Consequences）**  
   维护两套执行路径；文档需标明适用场景。

5. **备选方案（Alternatives）**  
   仅进程或仅线程（覆盖不全）。

---

## 决策 2：引入 Orchestrator 与可插拔组件

1. **背景（Context）**  
   单类堆叠监控、调度、聚合会导致类体积膨胀、难以测试。

2. **决策（Decision）**  
   拆分 `Executor` / `JobSource` / `Monitor` / `Scheduler` / `Aggregator` / `ErrorHandler`，由 `Orchestrator` 组合并暴露 `run()`。

3. **理由（Rationale）**  
   单一职责、可替换实现、组件可单测。

4. **影响（Consequences）**  
   新功能优先走组件化路径；传统 Worker 仍保留。

5. **备选方案（Alternatives）**  
   单一大类 Facade（难扩展）。

---

## 决策 3：内存感知调度

1. **背景（Context）**  
   固定 batch 在不同机器与数据集规模下易 OOM 或利用率低。

2. **决策（Decision）**  
   使用 `MemoryMonitor` 等指标，`MemoryAwareScheduler` 动态调整 batch；旧版 `MemoryAwareBatchScheduler` 保留兼容。

3. **理由（Rationale）**  
   在安全前提下提高吞吐。

4. **影响（Consequences）**  
   依赖运行时内存观测（如 `psutil` 可用时）。

5. **备选方案（Alternatives）**  
   全局固定 batch。

---

## 决策 4：`TaskType` 与 `resolve_max_workers('auto')`

1. **背景（Context）**  
   业务难以统一选择并发数。

2. **决策（Decision）**  
   `TaskType` 区分 CPU / IO / Mixed；`calculate_workers` 按类型与预留核数估算；`'auto'` 从 `ConfigManager.get_module_config(module_name)` 读配置。

3. **理由（Rationale）**  
   与 `userspace/config/worker.json` 等约定对齐，减少魔数。

4. **影响（Consequences）**  
   依赖 `infra.project_context`。

5. **备选方案（Alternatives）**  
   完全手动指定并发数。

---

## 决策 5：`max_workers=1` 默认主进程执行，并统一输出进度事件

1. **背景（Context）**  
   在金融回测场景中，`max_workers=1` 若仍启动单子进程，容易出现「主进程 + 子进程」并存语义，叠加数据库连接池继承问题，增加单写多读链路的状态混乱风险。与此同时，UI 需要稳定的全局进度信息提升可观测性与交互体验。

2. **决策（Decision）**  
   - `ProcessWorker` 在 `execution_mode=QUEUE` 且 `max_workers=1` 时，默认走主进程串行执行（`is_main_process_used_if_single_worker=True`）。  
   - 仅在显式关闭该开关时，`max_workers=1` 才允许走单子进程路径。  
   - 新增 `on_job_done` 回调，在每个 `job_finished` 时输出进度事件。  
   - 新增 `ProgressReportConfig`（`none / every_job_done / every_sec_interval / every_progress_interval`）统一控制进度日志上报策略。  
   - `DatabaseManager.reset_default()` 仅在子进程路径触发，避免主进程执行路径误重置连接上下文。

3. **理由（Rationale）**  
   主进程串行语义与业务认知一致（`worker=1` 即不并发），可降低连接状态漂移与写读冲突概率；同时保留开关用于少数需要进程隔离的场景。统一事件格式让上层在不引入 pipeline 抽象的前提下也能做全局进度展示，而 dataclass + 枚举模式避免进度参数碎片化。

4. **影响（Consequences）**  
   - 默认行为更偏向稳定与可解释性，而非进程隔离。  
   - 需要进程隔离时必须显式配置 `is_main_process_used_if_single_worker=False`。  
   - 上层可直接消费 `on_job_done` 回调结果构建运行态 UI，无需自行推导进度。  
   - 日志策略由 `ProgressReportConfig` 集中管理；新增模式时无需继续膨胀构造参数。

5. **备选方案（Alternatives）**  
   - 保持 `max_workers=1` 仍创建 `ProcessPoolExecutor`（语义不直观且在部分场景引入额外风险）。  
   - 将进度计算完全留给业务层（重复实现、事件口径难统一）。

---

## 相关文档

- [架构总览](./ARCHITECTURE.md)
- [详细设计](./DESIGN.md)
- [API](./API.md)
