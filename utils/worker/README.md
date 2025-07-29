# JobWorker - 通用任务执行器

## 概述

`JobWorker` 是一个通用的任务执行器，专门为股票数据获取和策略计算而设计。它支持串行和并行执行模式，提供灵活的任务队列管理和详细的执行监控。

## 主要特性

### 🚀 执行模式
- **串行执行** (`ExecutionMode.SERIAL`): 逐个执行任务，适合需要严格控制执行顺序的场景
- **并行执行** (`ExecutionMode.PARALLEL`): 多线程并行执行，适合I/O密集型任务（如API调用）

### 🔧 可定制性
- **自定义执行逻辑**: 通过 `set_job_executor()` 设置任务执行函数
- **灵活的任务数据**: 支持任意类型的数据结构
- **可配置的并发数**: 在并行模式下控制最大工作线程数

### 📊 监控和统计
- **实时统计**: 任务完成数、失败数、成功率等
- **性能指标**: 执行时间、吞吐量、平均耗时
- **详细日志**: 每个任务的执行状态和结果

### 🎛️ 控制功能
- **暂停/恢复**: 支持运行时暂停和恢复执行
- **停止**: 优雅停止所有任务
- **队列管理**: 清空任务队列和结果队列
- **信号处理**: 自动处理 Ctrl+C 和系统信号
- **优雅关闭**: 确保资源正确释放，避免线程泄漏

## 核心类

### JobWorker
主要的任务执行器类，负责管理任务队列和执行流程。

### JobResult
任务执行结果类，包含执行状态、结果数据、错误信息等。

### JobStatus
任务状态枚举：
- `PENDING`: 等待中
- `RUNNING`: 执行中
- `COMPLETED`: 已完成
- `FAILED`: 失败
- `CANCELLED`: 已取消

### ExecutionMode
执行模式枚举：
- `SERIAL`: 串行执行
- `PARALLEL`: 并行执行

## 使用示例

### 基本用法

```python
from utils.worker import JobWorker, ExecutionMode

# 创建执行器
worker = JobWorker(
    max_workers=5,
    execution_mode=ExecutionMode.PARALLEL
)

# 设置任务执行函数
def my_task(job_data):
    # 你的任务逻辑
    return {"result": "success"}

worker.set_job_executor(my_task)

# 添加任务
jobs = [
    {'id': 'task_1', 'data': {'param': 'value1'}},
    {'id': 'task_2', 'data': {'param': 'value2'}},
]

# 执行任务
stats = worker.run_jobs(jobs)

# 获取结果
results = worker.get_results()
```

### K线数据获取示例

```python
def kline_fetcher(job_data):
    """K线数据获取任务"""
    # 调用Tushare API
    data = api.daily(
        ts_code=job_data['ts_code'],
        start_date=job_data['start_date'],
        end_date=job_data['end_date']
    )
    return data

# 创建执行器
worker = JobWorker(max_workers=3, execution_mode=ExecutionMode.PARALLEL)
worker.set_job_executor(kline_fetcher)

# 准备任务
jobs = []
for stock in stock_list:
    jobs.append({
        'id': f'kline_{stock["code"]}',
        'data': {
            'ts_code': stock['ts_code'],
            'start_date': '20250101',
            'end_date': '20250131'
        }
    })

# 执行
stats = worker.run_jobs(jobs)
worker.print_stats()
```

### 策略计算示例

```python
def strategy_calculator(job_data):
    """策略计算任务"""
    # 执行策略计算
    signal = calculate_strategy(
        job_data['strategy_name'],
        job_data['stock_code']
    )
    return signal

# 创建执行器
worker = JobWorker(max_workers=5, execution_mode=ExecutionMode.PARALLEL)
worker.set_job_executor(strategy_calculator)

# 准备策略任务
jobs = []
strategies = ['MA', 'RSI', 'MACD']
stocks = ['000001', '000002', '600000']

for strategy in strategies:
    for stock in stocks:
        jobs.append({
            'id': f'{strategy}_{stock}',
            'data': {
                'strategy_name': strategy,
                'stock_code': stock
            }
        })

# 执行
stats = worker.run_jobs(jobs)
```

## API 参考

### JobWorker 构造函数

```python
JobWorker(
    max_workers: int = 5,                    # 最大并行工作线程数
    execution_mode: ExecutionMode = ExecutionMode.PARALLEL,  # 执行模式
    job_executor: Optional[Callable] = None, # 任务执行函数
    enable_monitoring: bool = True           # 是否启用监控
)
```

### 主要方法

#### 任务管理
- `add_job(job_id: str, job_data: Any)`: 添加单个任务
- `add_jobs(jobs: List[Dict[str, Any]])`: 批量添加任务
- `run_jobs(jobs: Optional[List[Dict[str, Any]]] = None)`: 执行任务队列
- `run_job(job_id: str, job_data: Any)`: 执行单个任务

#### 控制功能
- `pause()`: 暂停执行
- `resume()`: 恢复执行
- `stop()`: 停止执行
- `shutdown(timeout=5.0)`: 优雅关闭执行器
- `clear_queue()`: 清空任务队列
- `clear_results()`: 清空结果队列

#### 监控和统计
- `get_results() -> List[JobResult]`: 获取所有执行结果
- `get_stats() -> Dict[str, Any]`: 获取执行统计信息
- `print_stats()`: 打印统计信息
- `reset_stats()`: 重置统计信息

## 性能优化建议

### 1. 选择合适的执行模式
- **I/O密集型任务**（如API调用）: 使用并行模式
- **CPU密集型任务**（如复杂计算）: 根据CPU核心数调整并行数
- **顺序依赖任务**: 使用串行模式

### 2. 调整并发数
```python
# 对于API调用，可以设置较高的并发数
worker = JobWorker(max_workers=10, execution_mode=ExecutionMode.PARALLEL)

# 对于计算密集型任务，建议不超过CPU核心数
worker = JobWorker(max_workers=4, execution_mode=ExecutionMode.PARALLEL)
```

### 3. 批量处理
```python
# 将大量任务分批处理，避免内存占用过高
batch_size = 100
for i in range(0, len(all_jobs), batch_size):
    batch = all_jobs[i:i+batch_size]
    worker.run_jobs(batch)
```

## 信号处理和优雅关闭

### 自动信号处理
JobWorker 现在支持自动处理系统信号，确保在程序被中断时能够优雅地关闭：

```python
# 自动处理 Ctrl+C (SIGINT) 和 SIGTERM 信号
worker = JobWorker(enable_monitoring=True)

try:
    stats = worker.run_jobs(jobs)
except KeyboardInterrupt:
    print("Gracefully shutting down...")
    # 信号处理器会自动调用 shutdown()
```

### 手动关闭
```python
# 显式关闭执行器
worker.shutdown(timeout=5.0)  # 等待最多5秒完成关闭
```

### 资源清理
- 自动清理线程池资源
- 清空任务和结果队列
- 确保无资源泄漏

## 错误处理

### 任务执行错误
```python
def robust_task(job_data):
    try:
        # 任务逻辑
        return result
    except Exception as e:
        logger.error(f"Task failed: {e}")
        # 可以选择重试或返回默认值
        return {"error": str(e), "status": "failed"}
```

### 获取失败的任务
```python
results = worker.get_results()
failed_jobs = [r for r in results if r.status == JobStatus.FAILED]

for failed in failed_jobs:
    logger.error(f"Job {failed.job_id} failed: {failed.error}")
```

## 最佳实践

### 1. 任务设计
- 保持任务粒度适中，避免过大的单个任务
- 确保任务之间无依赖关系（并行模式下）
- 合理设计任务数据结构

### 2. 资源管理
- 及时清理不需要的结果
- 监控内存使用情况
- 适当设置超时机制

### 3. 监控和日志
- 定期检查执行统计
- 记录关键任务的执行结果
- 设置适当的日志级别

## 与现有代码集成

### 在 Tushare 数据获取中使用
```python
# 在 main.py 中集成
def execute_stock_kline_renew_jobs_with_worker(self, jobs: dict):
    worker = JobWorker(max_workers=5, execution_mode=ExecutionMode.PARALLEL)
    worker.set_job_executor(self.fetch_kline_data)
    
    # 转换任务格式
    worker_jobs = []
    for stock_key, stock_jobs in jobs.items():
        for job in stock_jobs:
            worker_jobs.append({
                'id': f"{stock_key}_{job['term']}",
                'data': job
            })
    
    stats = worker.run_jobs(worker_jobs)
    return stats
```

这个 `JobWorker` 为你的股票项目提供了一个强大而灵活的任务执行框架，可以显著提高数据获取和策略计算的效率！ 