#!/usr/bin/env python3
# Memory-Aware Batch Scheduler 设计文档

> 本文档描述一个围绕 `FuturesWorker` / `ProcessWorker` 的“内存感知批量调度”扩展，用于在不引入外部框架的前提下，实现基于内存占用的自适应 batch size 调整。

---

## 1. 背景与动机

在现有的策略枚举 / 模拟框架中：

- 我们需要对「大量独立任务」（如每只股票一次完整枚举）做并行执行；
- 每个任务内部会：
  - 访问 DuckDB（读取 K 线、财务等数据）；
  - 执行一段较重的计算（指标、枚举）；
  - 产出结果并写入汇总结构（如性能统计、元数据、CSV）。

迁移到 DuckDB 后的约束：

- DuckDB **文件型数据库不支持多进程对同一文件同时读写**；
- 多线程访问单一连接在高负载场景下也可能引发原生库的内存问题；
- 但我们仍希望利用多核能力，最大化并行度，同时**显式控制内存峰值**。

目标：

- 在一个进程内，**安全地以多线程方式执行 I/O + 计算任务**（或在未来扩展到多进程）；
- 提供一个通用的「批量调度器」，可以根据**进程实际内存占用**动态调整 batch size；
- 兼容现有的 `FuturesWorker` / `ProcessWorker` 接口，尽量不破坏现有调用方。

---

## 2. 模块化视角：Worker 组件拆分

在整体 worker 体系里，可以按职责拆成若干高度可复用的组件（而不是一个"大一统"的 Worker 类）：

- **Executor（执行器）**
  - 负责"如何并发执行一批 jobs"；
  - 形态：`FuturesWorker`（多线程）、`ProcessWorker`（多进程）、未来的其他实现；
  - 接口倾向于：`run_jobs(jobs: List[Job]) -> List[JobResult]`，对调度/监控无感。

- **Queue / JobSource（队列 / 任务源）**
  - 负责 job 的产生与顺序，例如：
    - 简单列表（一次性加载所有 jobs）；
    - 惰性生成（iterator / generator）；
    - 优先级队列、分级队列等。
  - 与 DB 或外部系统解耦，关注"提供 jobs，而不是如何执行"。

- **Monitor（监控器）**
  - 负责观测：内存、CPU、吞吐量、进度、失败率等；
  - 暴露统一接口：`get_stats()`, `get_memory_warning()`, `export_snapshot()` 等；
  - 不直接做决策，只提供「可观测性」。

- **Controller / Scheduler（控制器 / 调度器）**
  - 负责基于监控数据和配置策略，动态调整：
    - batch size；
    - worker 并发度（如 `max_workers`）；
  - 以 orchestrator 角色存在：
    - 从 Queue 拉取一批 jobs；
    - 调用 Executor 执行；
    - 把结果交给 Aggregator & ErrorHandler；
    - 同时更新 Monitor。

- **Aggregator（聚合器）**
  - 负责将单个 `JobResult` 聚合成「全局视图」：
    - 业务层统计（如 total_opportunity_count）；
    - 性能统计（如 avg_time_per_job_ms, total_db_time 等）；
    - 可选：增量 flush 到磁盘。

- **ErrorHandler（错误处理器）**
  - 统一处理 job 级别的异常：
    - 是否重试（次数 / 退避策略）；
    - 是否跳过某些已知安全异常；
    - 何时 fail-fast。

在这套拆分下，**`MemoryAwareBatchScheduler` 被设计成一个「Controller + Monitor」的组合组件**：

- 在「Controller」层面：负责根据内存使用情况动态调整 batch size；
- 在「Monitor」层面：负责采集与内存/进度相关的核心指标，并提供统一的监控 API；
- Executor / Aggregator / ErrorHandler 保持可插拔，不写死在 Scheduler 内部。

---

## 3. 总体设计概览

我们在 `FuturesWorker` 之上引入一个新的调度层：`MemoryAwareBatchScheduler`。

### 3.1 核心职责

1. **批量调度（Batching）**
   - 将一大批 `jobs: List[Job]` 分成多批（batch），每批通过下层 `Worker` 执行。
   - 每个 `Job` 的接口不变：`{'id': ..., 'data': ...}`。

2. **内存监控（Memory Monitoring）**
   - 在每一批执行前后读取当前进程 RSS 内存（通过 `psutil`），计算“本批任务引起的增量内存”。

3. **自适应 batch size（Adaptive Batching）**
   - 基于内存增量和配置的 `memory_budget`，动态调整下一批的任务数：
     - 批量太大 → 观察到 `delta_mem` 超过预算 → 减小 batch size；
     - 批量太小且仍有大量富余内存 → 适度放大 batch size。

4. **考虑汇总信息的内存增长**
   - 每个 job 执行完，会在主进程累积汇总数据（例如性能指标、metadata），这部分是**不随 batch 释放的常驻内存**；
   - 调度器在估算可用内存时，需要考虑“已完成 job 的累计汇总开销”，防止 batch size 一直维持在过高水平导致最终 OOM。

### 3.2 与现有 Worker 的关系

- `FuturesWorker` / `ProcessWorker` 仍然只关心“如何执行一堆 job”：
  - 输入：`jobs = [{'id': ..., 'data': ...}, ...]`
  - 输出：`List[JobResult]`
- `MemoryAwareBatchScheduler` 只负责：
  - 在外层决定每一批要给下层 worker 几个 job；
  - 在每一批执行完后，根据结果和内存占用情况更新自己的状态。

因此：

```python
def run_with_memory_aware_batches(jobs, worker_factory, memory_budget_mb, **worker_kwargs):
    scheduler = MemoryAwareBatchScheduler(
        jobs=jobs,
        memory_budget_mb=memory_budget_mb,
        warmup_batch_size=20,
        min_batch_size=10,
        max_batch_size=500,
        ...
    )

    all_results = []
    finished_jobs = 0

    for batch in scheduler.iter_batches():
        worker = worker_factory(**worker_kwargs)
        # 将 batch 转成 worker 可识别的 job 格式
        worker_jobs = [{'id': job['id'], 'data': job} for job in batch]

        stats = worker.run_jobs(worker_jobs)
        batch_results = worker.get_results()

        all_results.extend(batch_results)
        finished_jobs += len(batch)

        scheduler.update_after_batch(
            batch_size=len(batch),
            batch_results=batch_results,
            finished_jobs=finished_jobs,
        )

        # 协助 GC，避免长时间持有大对象
        del batch, worker_jobs, batch_results
        import gc; gc.collect()

    return all_results
```

这段逻辑可以在 `FuturesWorker` 的 README 中给出示例，也可以在更高一层（例如 `OpportunityEnumerator`）中直接使用。

---

## 4. MemoryAwareBatchScheduler 设计细节

### 4.1 初始化参数

```python
class MemoryAwareBatchScheduler:
    def __init__(
        self,
        jobs: List[Any],
        memory_budget_mb: float,
        warmup_batch_size: int = 20,
        min_batch_size: int = 10,
        max_batch_size: int = 500,
        smooth_factor: float = 0.3,
        summary_weight: float = 0.2,
        log: Optional[logging.Logger] = None,
    ):
        ...
```

含义：

- `jobs`: 原始任务列表（例如股票 ID 列表或完整 payload）；
- `memory_budget_mb`: 为一轮任务执行预留的**最大额外内存**（不含进程 baseline）；
- `warmup_batch_size`: 首批 job 数量，用于估算 `mem_per_job`；
- `min_batch_size` / `max_batch_size`: batch 上下限，避免极端值；
- `smooth_factor`: 对观测到的 `mem_per_job` 做指数平滑，抑制抖动；
- `summary_weight`: 估算中，用于区分「工作集内存」和「汇总内存」的比例。

### 4.2 内存测量

```python
import os, psutil

def _get_rss_mb() -> float:
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)
```

在每个 batch 执行前后调用：

```python
mem_before = _get_rss_mb()
# 执行 batch ...
mem_after = _get_rss_mb()
delta_batch = max(mem_after - mem_before, 0.0)
```

### 3.3 单 Job 内存模型（含“汇总信息”）

假设：

- `delta_batch` = 当前批次执行完成后，相对上一批结束时的 RSS 增量；
- 一个 batch 有 `B` 个 job；
- 每个 job 完成后，会：
  - 占用一部分**工作集内存**（执行中用，batch 结束后可被 GC 回收）；
  - 产出一部分**汇总信息**（写入 aggregator / metadata，长期存在）。

我们可以用一个简单的经验模型：

```text
delta_batch ≈ B * mem_working_per_job + B * mem_summary_per_job
```

其中：

- `mem_working_per_job`：Job 在执行期间的平均额外内存占用（可回收）；
- `mem_summary_per_job`：Job 结果对长期内存的平均贡献（不可忽略）。

调度器不需要完全精确，只需一个**保守估计**即可：

```python
mem_per_job_obs = delta_batch / max(B, 1)

# 使用简单的比例拆分：大头归为 working_set，小头归为 summary
mem_summary_per_job = mem_per_job_obs * summary_weight      # e.g. 0.1 ~ 0.3
mem_working_per_job = max(mem_per_job_obs - mem_summary_per_job, 0.0)

# 对历史观测做指数平滑，避免波动过大
self.mem_working_per_job = (
    self.mem_working_per_job * (1 - smooth_factor)
    + mem_working_per_job * smooth_factor
)
self.mem_summary_per_job = (
    self.mem_summary_per_job * (1 - smooth_factor)
    + mem_summary_per_job * smooth_factor
)
```

> 注意：因为汇总信息是「只增不减」，`self.mem_summary_per_job` 的估算会直接影响后续可用内存预算。

### 4.4 动态计算下一批 batch size

设：

- `memory_budget_mb`：为整个执行过程预留的额外内存预算（例如 5000 MB，对应 5GB）；
- `finished_jobs`：已经完成的 job 数量；
- `mem_working_per_job` / `mem_summary_per_job`：上一步的估算结果。

则当前时刻的**汇总内存占用估算**：

```python
summary_used_mb = finished_jobs * self.mem_summary_per_job
```

预留给**当前批次工作集**的内存：

```python
available_for_working_mb = max(
    memory_budget_mb - summary_used_mb,
    self.min_working_floor_mb,  # 避免出现负值或过小值
)
```

据此计算建议的 batch 大小：

```python
if self.mem_working_per_job > 0:
    target_batch = int(available_for_working_mb / self.mem_working_per_job)
else:
    target_batch = self.max_batch_size  # 没法估计时退回最大值

target_batch = max(self.min_batch_size, min(target_batch, self.max_batch_size))
```

为避免 batch 抖动过大，对调整幅度做限幅和平滑：

```python
delta = target_batch - self.current_batch_size
max_step = max(int(self.current_batch_size * 0.5), 5)
delta_clamped = max(-max_step, min(max_step, delta))

self.current_batch_size = max(
    self.min_batch_size,
    min(self.max_batch_size, self.current_batch_size + delta_clamped)
)
```

### 3.5 Job 汇总信息导致的“缓慢膨胀”

正如你提到的，每个 job 执行完成后，都会向某个 aggregator / summary 里追加数据，例如：

- 每只股票的性能指标（time / memory / opportunities 统计）；
- metadata（版本号、起止日期、策略设置快照）；
- 甚至未来可能还有：
  - 部分示例机会列表；
  - 调试日志片段等。

这意味着：

- 即使单个 batch 的工作集内存完全可回收，**随着 job 数增加，进程 RSS 仍会单调上升**；
- 如果调度器仅根据 `delta_batch / B` 来估计 `mem_per_job`，而不区分 working_set / summary，会低估后续的真实内存压力。

我们通过 `summary_weight` + `finished_jobs * mem_summary_per_job` 的方式，将这部分逐步「吃掉」内存预算：

```python
summary_used_mb = finished_jobs * self.mem_summary_per_job
available_for_working_mb = memory_budget_mb - summary_used_mb
```

这样：

- 随着 job 越做越多，可用于新 batch 的工作集内存配额会逐渐下降；
- 调度器会自动把 `current_batch_size` 往下调，避免在后期内存已经很满的时候还开过大的 batch。

如果希望更精细，还可以：

- 把汇总结构 **分级持久化**（例如每 N 只股票就 flush 一批 summary 到磁盘，释放内存）；
- 并在 flush 后把 `finished_jobs` 或 `summary_used_mb` 进行适当“折扣”，反映一部分内存已经释放。

---

## 4. 扩展：Worker Monitor 职责

除了批量调度，`MemoryAwareBatchScheduler` 还可以承担**Worker 执行过程的监控职责**，提供统一的监控接口。

### 4.1 监控维度

1. **内存监控（Memory Monitoring）**
   - 实时 RSS 内存占用；
   - 每批次的增量内存；
   - 汇总信息的累计内存；
   - 内存使用趋势（是否接近预算上限）。

2. **执行进度监控（Progress Monitoring）**
   - 已完成 job 数量 / 总 job 数量；
   - 当前批次进度；
   - 预计剩余时间（基于历史平均耗时）。

3. **性能监控（Performance Monitoring）**
   - 每批次的平均执行时间；
   - DB 查询时间 vs 计算时间；
   - 吞吐量（jobs/second）。

4. **健康检查（Health Check）**
   - 内存是否接近预算上限（触发告警）；
   - 是否有异常 job（失败率统计）；
   - Worker 线程/进程状态（如果可访问）。

### 5.2 Monitor API 设计

```python
class MemoryAwareBatchScheduler:
    # ... 现有方法 ...

    def get_monitor_stats(self) -> Dict[str, Any]:
        """
        获取当前监控统计信息
        
        Returns:
            {
                'memory': {
                    'current_rss_mb': float,
                    'memory_budget_mb': float,
                    'used_mb': float,
                    'available_mb': float,
                    'usage_percent': float,
                    'summary_used_mb': float,
                    'working_set_available_mb': float,
                },
                'progress': {
                    'total_jobs': int,
                    'finished_jobs': int,
                    'current_batch': int,
                    'total_batches': int,
                    'progress_percent': float,
                },
                'performance': {
                    'avg_time_per_job_ms': float,
                    'throughput_jobs_per_sec': float,
                    'current_batch_size': int,
                },
                'health': {
                    'memory_warning': bool,  # 是否接近预算上限
                    'failure_rate': float,   # 失败率
                    'status': str,           # 'healthy' / 'warning' / 'critical'
                }
            }
        """
        ...

    def should_adjust_batch_size(self) -> Tuple[bool, str]:
        """
        判断是否应该调整 batch size（用于健康检查）
        
        Returns:
            (should_adjust: bool, reason: str)
        """
        ...

    def get_memory_warning(self) -> Optional[str]:
        """
        获取内存告警信息（如果有）
        
        Returns:
            None 或告警消息字符串
        """
        ...
```

### 5.3 监控数据的生命周期

- **实时数据**：每次 `update_after_batch()` 时更新；
- **历史趋势**：可以保留最近 N 批次的快照（用于绘制内存曲线、性能曲线）；
- **持久化**：监控数据可以定期写入文件（例如每 10 批次写一次），用于事后分析。

### 5.4 与 Worker 的集成

监控器可以**被动观察**（不侵入 Worker 内部）：

```python
scheduler = MemoryAwareBatchScheduler(...)

for batch in scheduler.iter_batches():
    # 执行前记录
    mem_before = scheduler._get_rss_mb()
    
    # Worker 执行（不关心内部细节）
    worker.run_jobs(batch)
    results = worker.get_results()
    
    # 执行后更新监控
    scheduler.update_after_batch(
        batch_size=len(batch),
        batch_results=results,
        finished_jobs=finished_jobs,
    )
    
    # 可选：打印监控信息
    if scheduler.should_log_progress():
        stats = scheduler.get_monitor_stats()
        logger.info(f"📊 监控: {stats['progress']['progress_percent']:.1f}%, "
                   f"内存: {stats['memory']['usage_percent']:.1f}%, "
                   f"batch_size: {stats['performance']['current_batch_size']}")
```

也可以**主动告警**：

```python
warning = scheduler.get_memory_warning()
if warning:
    logger.warning(f"⚠️  内存告警: {warning}")
    # 可以触发降级策略：减小 batch size、暂停新批次等
```

---

## 6. 实现建议

### 6.1 模块位置

建议放在 `app/core/infra/worker/` 根目录下：

- `memory_aware_scheduler.py`：核心实现
- `MEMORY_AWARE_BATCH_SCHEDULER.md`：本文档

这样：

- 既可以被 `multi_thread/` 下的 `FuturesWorker` 使用；
- 也可以被 `multi_process/` 下的 `ProcessWorker` 使用（未来如果需要）；
- 保持与 Worker 实现解耦，便于独立测试和演进。

### 6.2 最小实现路径

1. **Phase 1：基础调度 + 内存监控**
   - 实现 `MemoryAwareBatchScheduler` 的核心逻辑（批量切割、内存观测、动态调整）；
   - 在 `OpportunityEnumerator` 中接入，验证不会 OOM。

2. **Phase 2：监控 API**
   - 添加 `get_monitor_stats()` / `get_memory_warning()` 等接口；
   - 在枚举过程中定期输出监控信息。

3. **Phase 3：健康检查与自动降级**
   - 实现 `should_adjust_batch_size()`；
   - 当内存接近上限时，自动减小 batch size 或暂停。

### 6.3 配置化

监控参数可以通过策略 settings 暴露：

```python
# example/settings.py
"enumerator": {
    "use_sampling": True,
    "max_workers": 1,              # 计算层 worker 数量
    "memory_budget_mb": 5000.0,     # 内存预算（MB）
    "warmup_batch_size": 20,       # 初始批次大小
    "min_batch_size": 10,
    "max_batch_size": 500,
    "summary_weight": 0.2,         # 汇总信息占比
    "monitor_interval": 5,         # 每 N 批次输出一次监控信息
}
```

---

## 7. 使用示例

### 7.1 在 OpportunityEnumerator 中使用

```python
from app.core.infra.worker.memory_aware_scheduler import MemoryAwareBatchScheduler

# 构建所有 job
jobs = [...]
enum_settings = ...

# 创建调度器（同时承担监控职责）
scheduler = MemoryAwareBatchScheduler(
    jobs=jobs,
    memory_budget_mb=enum_settings.get('memory_budget_mb', 5000.0),
    warmup_batch_size=enum_settings.get('warmup_batch_size', 20),
    ...
)

all_results = []
finished_jobs = 0

for batch in scheduler.iter_batches():
    # 创建 Worker（可以是 FuturesWorker 或 ProcessWorker）
    worker = FuturesWorker(
        max_workers=enum_settings.get('max_workers', 1),
        job_executor=OpportunityEnumerator._execute_single_job,
    )
    
    worker_jobs = [{'id': j['stock_id'], 'data': j} for j in batch]
    worker.run_jobs(worker_jobs)
    batch_results = worker.get_results()
    
    all_results.extend(batch_results)
    finished_jobs += len(batch)
    
    # 更新调度器状态（触发内存观测和 batch size 调整）
    scheduler.update_after_batch(
        batch_size=len(batch),
        batch_results=batch_results,
        finished_jobs=finished_jobs,
    )
    
    # 定期输出监控信息
    if finished_jobs % (scheduler.monitor_interval * scheduler.current_batch_size) == 0:
        stats = scheduler.get_monitor_stats()
        logger.info(f"📊 进度: {stats['progress']['progress_percent']:.1f}%, "
                   f"内存: {stats['memory']['usage_percent']:.1f}%, "
                   f"batch_size: {stats['performance']['current_batch_size']}")
    
    # 检查告警
    warning = scheduler.get_memory_warning()
    if warning:
        logger.warning(f"⚠️  {warning}")

# 最终监控报告
final_stats = scheduler.get_monitor_stats()
logger.info(f"✅ 执行完成，最终监控: {final_stats}")
```

---

## 8. 未来扩展方向

- **多进程场景的监控**：如果未来需要支持多进程 Worker，可以在每个子进程内也运行一个轻量级监控器，主进程汇总。
- **持久化监控数据**：将监控快照写入 JSON / CSV，用于性能分析和优化。
- **自适应参数**：不仅调整 batch size，还可以根据内存情况动态调整 `max_workers`（例如内存紧张时减少并发数）。

