# Worker - 通用任务执行器

## 概述

本模块提供了两种任务执行器，分别针对不同类型的任务优化：
- **ProcessWorker**: 基于多进程的CPU密集型任务执行器
- **MultiThreadWorker**: 基于多线程的IO密集型任务执行器（原 FuturesWorker）

同时提供了模块化架构，支持可插拔的组件设计。

## 📁 目录结构

```
core/infra/worker/
├── multi_process/          # 多进程执行器
│   ├── process_worker.py   # ProcessWorker核心实现
│   ├── example.py          # 使用示例
│   ├── task_type.py        # 任务类型定义
│   └── README.md           # 多进程模块说明
├── multi_thread/           # 多线程执行器
│   ├── futures_worker.py   # MultiThreadWorker核心实现
│   ├── example.py          # 使用示例
│   └── README.md           # 多线程模块说明
├── executors/              # 执行器模块（模块化架构）
│   ├── base.py
│   ├── process_executor.py
│   └── futures_executor.py
├── queues/                 # 任务源模块
│   ├── base.py
│   └── list_source.py
├── monitors/               # 监控器模块
│   ├── base.py
│   └── memory_monitor.py
├── schedulers/             # 调度器模块
│   ├── base.py
│   └── memory_aware_scheduler.py
├── aggregators/            # 聚合器模块
│   ├── base.py
│   └── simple_aggregator.py
├── error_handlers/         # 错误处理器模块
│   ├── base.py
│   └── simple_error_handler.py
├── orchestrator.py         # 编排器（组合所有组件）
├── memory_aware_scheduler.py  # 内存感知调度器（旧版本，向后兼容）
├── __init__.py             # 模块导入配置
├── README.md               # 本文件
└── DESIGN.md               # 设计文档
```

## 🚀 快速选择指南

### 使用ProcessWorker的场景
- **CPU密集型计算**: 数据分析、算法计算、策略分析
- **需要充分利用多核CPU**: 自动使用CPU核心数
- **任务执行时间较长**: >100ms的计算任务
- **内存使用可控**: 特别是BATCH模式

### 使用MultiThreadWorker的场景
- **IO密集型操作**: API调用、文件读写、数据库查询
- **任务执行时间较短**: <100ms的任务
- **需要频繁的线程切换**: 大量小任务
- **对内存使用要求不高**: 线程开销相对较小

## 🚀 快速开始

### ProcessWorker (多进程)

```python
from core.infra.worker import ProcessWorker, ProcessExecutionMode

# 创建多进程执行器
worker = ProcessWorker(
    max_workers=None,  # 自动使用CPU核心数
    execution_mode=ProcessExecutionMode.QUEUE,  # 队列模式
    job_executor=my_cpu_task,
    is_verbose=True
)

# 执行任务
stats = worker.run_jobs(jobs)
worker.print_stats()
```

### MultiThreadWorker (多线程)

```python
from core.infra.worker import MultiThreadWorker, ThreadExecutionMode

# 创建多线程执行器
worker = MultiThreadWorker(
    max_workers=10,
    execution_mode=ThreadExecutionMode.PARALLEL,
    job_executor=my_io_task,
    is_verbose=True
)

# 执行任务
stats = worker.run_jobs(jobs)
worker.print_stats()
```

## 📊 执行模式对比

### ProcessWorker 执行模式

| 模式 | 特点 | 适用场景 |
|------|------|----------|
| QUEUE | 持续填充进程池，完成一个立即启动下一个 | 最大化CPU利用率 |
| BATCH | batch间串行，batch内并行 | 控制内存使用，大数据量处理 |

### MultiThreadWorker 执行模式

| 模式 | 特点 | 适用场景 |
|------|------|----------|
| PARALLEL | 多线程并行执行 | IO密集型任务 |
| SERIAL | 串行执行 | 需要严格控制执行顺序 |

## ⚡ 性能对比

### CPU密集型任务
- **ProcessWorker**: 可达到接近线性的性能提升
- **MultiThreadWorker**: 受GIL限制，性能提升有限

### IO密集型任务
- **ProcessWorker**: 进程创建开销大，不适合
- **MultiThreadWorker**: 线程切换开销小，性能优秀

## 💡 实际应用示例

### 股票策略分析 (CPU密集型)

```python
from core.infra.worker import ProcessWorker, ProcessExecutionMode

def analyze_stock_strategy(data):
    """分析单只股票的策略"""
    stock_code = data['stock_code']
    
    # 获取股票数据
    stock_data = get_stock_data(stock_code)
    
    # 执行策略计算 (CPU密集型)
    signals = calculate_signals(stock_data)
    
    return {
        'stock_code': stock_code,
        'signals': signals
    }

# 使用多进程执行器
worker = ProcessWorker(
    max_workers=None,  # 自动使用CPU核心数
    execution_mode=ProcessExecutionMode.QUEUE,
    job_executor=analyze_stock_strategy
)
```

### API数据获取 (IO密集型)

```python
from core.infra.worker import MultiThreadWorker, ThreadExecutionMode

def fetch_api_data(data):
    """获取API数据"""
    url = data['url']
    response = requests.get(url)  # IO密集型
    return response.json()

# 使用多线程执行器
worker = MultiThreadWorker(
    max_workers=20,
    execution_mode=ThreadExecutionMode.PARALLEL,
    job_executor=fetch_api_data
)
```

## 🔧 配置建议

### 进程数/线程数设置

#### ProcessWorker
- **CPU密集型**: 使用CPU核心数或略少于核心数
- **内存受限**: 减少进程数避免内存不足
- **I/O混合**: 可以适当增加进程数

#### MultiThreadWorker
- **纯IO密集型**: 设置为CPU核心数的2-4倍
- **IO+计算混合**: 设置为CPU核心数的1-2倍
- **网络延迟高**: 可以设置更多线程

### 执行模式选择

#### ProcessWorker
- **大量任务**: 使用QUEUE模式最大化吞吐量
- **内存敏感**: 使用BATCH模式控制内存使用
- **任务依赖**: 使用BATCH模式确保执行顺序

#### MultiThreadWorker
- **IO密集型**: 使用PARALLEL模式
- **需要顺序控制**: 使用SERIAL模式
- **任务依赖**: 使用SERIAL模式

## 📝 最佳实践

### 任务设计
1. **任务粒度**: 确保每个任务有足够的工作量
2. **数据序列化**: 确保任务数据可以被pickle序列化
3. **资源管理**: 在任务函数中正确管理资源
4. **错误处理**: 实现完善的异常处理

### 性能优化
1. **选择合适的执行器**: 根据任务特性选择ProcessWorker或MultiThreadWorker
2. **合理设置并发数**: 平衡性能和资源使用
3. **监控执行状态**: 使用详细日志和统计信息
4. **测试验证**: 在实际环境中测试和优化

### 资源管理
1. **数据库连接**: 使用连接池管理数据库连接
2. **网络连接**: 合理管理HTTP连接和超时
3. **内存使用**: 监控内存使用，避免内存泄漏
4. **进程/线程清理**: 确保资源正确释放

## 🔄 模块化架构（高级）

Worker 模块还提供了模块化架构，支持可插拔的组件：

```python
from core.infra.worker import (
    Orchestrator,
    ProcessExecutor,
    ListJobSource,
    MemoryMonitor,
    MemoryAwareScheduler,
    SimpleAggregator,
    SimpleErrorHandler
)

# 创建编排器
orchestrator = Orchestrator(
    executor=ProcessExecutor(max_workers=4),
    job_source=ListJobSource(jobs),
    monitor=MemoryMonitor(),
    scheduler=MemoryAwareScheduler(),
    aggregator=SimpleAggregator(),
    error_handler=SimpleErrorHandler()
)

# 执行任务
result = orchestrator.run()
```

详细设计请参考 `DESIGN.md`。

## ⚠️ 注意事项

### ProcessWorker
1. **函数序列化**: 任务函数必须在模块级别定义
2. **数据传递**: 任务数据必须可序列化
3. **资源管理**: 每个进程需要独立的资源
4. **内存使用**: 多进程会增加内存开销

### MultiThreadWorker
1. **GIL限制**: Python的全局解释器锁限制了真正的并行计算
2. **线程安全**: 确保共享资源的线程安全访问
3. **资源管理**: 正确管理数据库连接、网络连接等资源
4. **内存使用**: 大量线程会增加内存开销

## 📚 更多信息

- **设计文档**：查看 `DESIGN.md` 了解设计思路和架构背景
- **多进程模块**：查看 `multi_process/README.md` 了解 ProcessWorker 详细用法
- **多线程模块**：查看 `multi_thread/README.md` 了解 MultiThreadWorker 详细用法
