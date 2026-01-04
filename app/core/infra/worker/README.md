# Worker - 通用任务执行器

## 概述

本模块提供了两种任务执行器，分别针对不同类型的任务优化：
- **ProcessWorker**: 基于多进程的CPU密集型任务执行器
- **FuturesWorker**: 基于多线程的IO密集型任务执行器

## 目录结构

```
utils/worker/
├── multi_process/          # 多进程执行器
│   ├── process_worker.py   # ProcessWorker核心实现
│   ├── process_worker_example.py  # 使用示例
│   ├── test_process_worker.py     # 功能测试
│   ├── PROCESS_WORKER_GUIDE.md    # 详细使用指南
│   ├── example.py          # 简化示例
│   └── README.md           # 多进程模块说明
├── multi_thread/           # 多线程执行器
│   ├── futures_worker.py   # FuturesWorker核心实现
│   ├── example.py          # 使用示例
│   └── README.md           # 多线程模块说明
├── __init__.py             # 模块导入配置
└── README.md               # 本文件
```

## 快速选择指南

### 使用ProcessWorker的场景
- **CPU密集型计算**: 数据分析、算法计算、策略分析
- **需要充分利用多核CPU**: 自动使用CPU核心数
- **任务执行时间较长**: >100ms的计算任务
- **内存使用可控**: 特别是BATCH模式

### 使用FuturesWorker的场景
- **IO密集型操作**: API调用、文件读写、数据库查询
- **任务执行时间较短**: <100ms的任务
- **需要频繁的线程切换**: 大量小任务
- **对内存使用要求不高**: 线程开销相对较小

## 快速开始

### ProcessWorker (多进程)

```python
from utils.worker import ProcessWorker, ProcessExecutionMode

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

### FuturesWorker (多线程)

```python
from utils.worker import FuturesWorker, ThreadExecutionMode

# 创建多线程执行器
worker = FuturesWorker(
    max_workers=10,
    execution_mode=ThreadExecutionMode.PARALLEL,
    job_executor=my_io_task,
    is_verbose=True
)

# 执行任务
stats = worker.run_jobs(jobs)
worker.print_stats()
```

## 执行模式对比

### ProcessWorker 执行模式

| 模式 | 特点 | 适用场景 |
|------|------|----------|
| QUEUE | 持续填充进程池，完成一个立即启动下一个 | 最大化CPU利用率 |
| BATCH | batch间串行，batch内并行 | 控制内存使用，大数据量处理 |

### FuturesWorker 执行模式

| 模式 | 特点 | 适用场景 |
|------|------|----------|
| PARALLEL | 多线程并行执行 | IO密集型任务 |
| SERIAL | 串行执行 | 需要严格控制执行顺序 |

## 性能对比

### CPU密集型任务
- **ProcessWorker**: 可达到接近线性的性能提升
- **FuturesWorker**: 受GIL限制，性能提升有限

### IO密集型任务
- **ProcessWorker**: 进程创建开销大，不适合
- **FuturesWorker**: 线程切换开销小，性能优秀

## 实际应用示例

### 股票策略分析 (CPU密集型)
```python
from utils.worker import ProcessWorker, ProcessExecutionMode

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
from utils.worker import FuturesWorker, ThreadExecutionMode

def fetch_api_data(data):
    """获取API数据"""
    url = data['url']
    response = requests.get(url)  # IO密集型
    return response.json()

# 使用多线程执行器
worker = FuturesWorker(
    max_workers=20,
    execution_mode=ExecutionMode.PARALLEL,
    job_executor=fetch_api_data
)
```

## 配置建议

### 进程数/线程数设置

#### ProcessWorker
- **CPU密集型**: 使用CPU核心数或略少于核心数
- **内存受限**: 减少进程数避免内存不足
- **I/O混合**: 可以适当增加进程数

#### FuturesWorker
- **纯IO密集型**: 设置为CPU核心数的2-4倍
- **IO+计算混合**: 设置为CPU核心数的1-2倍
- **网络延迟高**: 可以设置更多线程

### 执行模式选择

#### ProcessWorker
- **大量任务**: 使用QUEUE模式最大化吞吐量
- **内存敏感**: 使用BATCH模式控制内存使用
- **任务依赖**: 使用BATCH模式确保执行顺序

#### FuturesWorker
- **IO密集型**: 使用PARALLEL模式
- **需要顺序控制**: 使用SERIAL模式
- **任务依赖**: 使用SERIAL模式

## 最佳实践

### 任务设计
1. **任务粒度**: 确保每个任务有足够的工作量
2. **数据序列化**: 确保任务数据可以被pickle序列化
3. **资源管理**: 在任务函数中正确管理资源
4. **错误处理**: 实现完善的异常处理

### 性能优化
1. **选择合适的执行器**: 根据任务特性选择ProcessWorker或FuturesWorker
2. **合理设置并发数**: 平衡性能和资源使用
3. **监控执行状态**: 使用详细日志和统计信息
4. **测试验证**: 在实际环境中测试和优化

### 资源管理
1. **数据库连接**: 使用连接池管理数据库连接
2. **网络连接**: 合理管理HTTP连接和超时
3. **内存使用**: 监控内存使用，避免内存泄漏
4. **进程/线程清理**: 确保资源正确释放

## 示例和测试

### 运行示例
```bash
# 多进程示例
cd utils/worker/multi_process
python example.py

# 多线程示例
cd utils/worker/multi_thread
python example.py
```

### 运行测试
```bash
# 多进程测试
cd utils/worker/multi_process
python test_process_worker.py
```

## 注意事项

### ProcessWorker
1. **函数序列化**: 任务函数必须在模块级别定义
2. **数据传递**: 任务数据必须可序列化
3. **资源管理**: 每个进程需要独立的资源
4. **内存使用**: 多进程会增加内存开销

### FuturesWorker
1. **GIL限制**: Python的全局解释器锁限制了真正的并行计算
2. **线程安全**: 确保共享资源的线程安全访问
3. **资源管理**: 正确管理数据库连接、网络连接等资源
4. **内存使用**: 大量线程会增加内存开销

## 版本信息

- **版本**: 2.0.0
- **作者**: Stocks-Py Team
- **描述**: 通用任务执行器模块 - 支持多进程和多线程执行

## 更新日志

### v2.0.0
- 重新组织模块结构，分离多进程和多线程执行器
- 新增ProcessWorker多进程执行器
- 优化FuturesWorker多线程执行器
- 完善文档和示例

### v1.0.0
- 初始版本，包含FuturesWorker多线程执行器