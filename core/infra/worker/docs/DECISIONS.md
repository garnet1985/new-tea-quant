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

## 相关文档

- [架构总览](./ARCHITECTURE.md)
- [详细设计](./DESIGN.md)
- [API](./API.md)
