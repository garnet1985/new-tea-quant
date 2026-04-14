# Worker 详细设计

**版本：** `0.2.0`

实现向说明；总览见 [ARCHITECTURE.md](./ARCHITECTURE.md)。

**相关文档**：[架构总览](./ARCHITECTURE.md) · [API](./API.md) · [决策记录](./DECISIONS.md)

---

## 1. 导出别名

`__init__.py` 将 `multi_process` 的 `ExecutionMode` 导出为 **`ProcessExecutionMode`**，`JobStatus`/`JobResult` 为 **`ProcessJobStatus`** / **`ProcessJobResult`**；线程侧同理为 **`ThreadExecutionMode`** 等，避免与线程模块枚举同名冲突。

---

## 2. ProcessWorker

- **模式**：`ExecutionMode.BATCH`（batch 间串行、batch 内并行）与 `QUEUE`（进程池持续取任务）。
- **进程数**：`max_workers` 默认 `cpu_count()`；手动值与 `cpu_count()` 取 min；`resolve_max_workers('auto', module_name)` 用 `TaskType` + `reserve_cores` 计算，并调用 `ConfigManager.get_module_config`。
- **任务形态**：队列内为 `{id, payload}`；`add_jobs` 兼容 `data` 字段作 payload。
- **启动方式**：`multiprocessing.get_context(start_method)`，默认 `spawn`。

---

## 3. MultiThreadWorker

- **模式**：`SERIAL` 与 `PARALLEL`（`ThreadPoolExecutor`）。
- **队列**：内部 `Queue` 存放待执行任务；`run_jobs` 可接受外部传入 jobs 列表或消费已 `add_job` 的队列（以代码为准）。

---

## 4. Orchestrator

- 若 `scheduler` 提供 `iter_batches`（如部分内存感知调度器），按迭代批次执行；否则 `has_more`/`get_batch` 循环。
- 无调度器时默认 `get_batch(1000)` 大块拉取。
- 返回 `{'results': [...], 'summary': ..., 'monitor_stats': ..., 'warnings': ...}`（后两者在组件存在时填充）。

---

## 5. 版本元数据

包级 `__version__` 使用 `core.system.get_version()`，与 core 发布版本对齐。
