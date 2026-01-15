# Multi-Process Worker

## 概述

多进程工作器模块，专门为CPU密集型任务设计，提供高效的多进程并行执行能力。

## 文件说明

### 核心文件
- **`process_worker.py`** - ProcessWorker多进程执行器核心实现
- **`process_worker_example.py`** - 使用示例和演示代码
- **`test_process_worker.py`** - 功能测试文件
- **`PROCESS_WORKER_GUIDE.md`** - 详细使用指南

## ProcessWorker 特性

### 🚀 执行模式
- **BATCH模式**: batch间串行，batch内并行
- **QUEUE模式**: 持续填充进程池，完成一个立即启动下一个

### 🔧 核心功能
- **自动进程数管理**: 默认使用CPU核心数
- **任务队列管理**: 灵活的任务添加和执行
- **详细统计监控**: 执行时间、成功率、性能指标
- **优雅资源管理**: 信号处理、进程清理、资源释放
- **错误处理**: 完善的异常处理和重试机制

### 📊 适用场景
- **CPU密集型计算**: 数据分析、算法计算、策略分析
- **需要充分利用多核CPU**: 自动使用CPU核心数
- **任务执行时间较长**: >100ms的计算任务
- **内存使用可控**: 特别是BATCH模式

## 快速开始

### 基本用法

```python
from app.core.infra.worker import ProcessWorker, ProcessExecutionMode

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

### 执行模式选择

#### QUEUE模式（推荐用于CPU密集型）
```python
worker = ProcessWorker(
    execution_mode=ProcessExecutionMode.QUEUE,  # 持续填充进程池
    job_executor=cpu_intensive_task
)
```

#### BATCH模式（推荐用于内存敏感场景）
```python
worker = ProcessWorker(
    execution_mode=ProcessExecutionMode.BATCH,
    batch_size=16,  # 每个batch 16个任务
    job_executor=cpu_intensive_task
)
```

## 性能优势

### 与多线程对比
- **多进程**: 绕过Python GIL限制，真正并行执行
- **多线程**: 受GIL限制，适合IO密集型任务

### 性能提升
- **CPU密集型任务**: 可达到接近线性的性能提升
- **多核利用**: 充分利用所有CPU核心
- **内存隔离**: 进程间内存隔离，提高稳定性

## 使用建议

1. **任务粒度**: 确保每个任务有足够的工作量（>100ms）
2. **进程数设置**: 使用CPU核心数或略少于核心数
3. **内存管理**: 大数据量处理时使用BATCH模式
4. **错误处理**: 在任务函数中正确处理异常
5. **资源管理**: 正确管理数据库连接、文件句柄等

## 示例和测试

- 运行示例: `python process_worker_example.py`
- 运行测试: `python test_process_worker.py`
- 详细指南: 查看 `PROCESS_WORKER_GUIDE.md`

## 注意事项

1. **函数序列化**: 任务函数必须在模块级别定义，支持pickle序列化
2. **数据传递**: 任务数据必须可序列化
3. **资源管理**: 每个进程需要独立的资源（如数据库连接）
4. **内存使用**: 多进程会增加内存开销，需要合理控制进程数

## 最佳实践

1. **选择合适的执行模式**: 根据任务特性和资源限制选择BATCH或QUEUE模式
2. **合理设置进程数**: 平衡性能和资源使用
3. **监控执行状态**: 使用详细日志和统计信息监控执行过程
4. **错误处理**: 实现完善的错误处理和重试机制
5. **性能测试**: 在实际环境中测试和优化性能
