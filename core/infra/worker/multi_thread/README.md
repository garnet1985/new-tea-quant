# Multi-Thread Worker

## 概述

多线程工作器模块，专门为IO密集型任务设计，提供高效的多线程并行执行能力。

## 文件说明

### 核心文件
- **`futures_worker.py`** - MultiThreadWorker多线程执行器核心实现

## MultiThreadWorker 特性

### 🚀 执行模式
- **串行执行** (`ExecutionMode.SERIAL`): 逐个执行任务，适合需要严格控制执行顺序的场景
- **并行执行** (`ExecutionMode.PARALLEL`): 多线程并行执行，适合I/O密集型任务

### 🔧 核心功能
- **多线程执行**: 基于concurrent.futures的ThreadPoolExecutor
- **任务队列管理**: 灵活的任务添加和执行
- **详细统计监控**: 执行时间、成功率、性能指标
- **优雅资源管理**: 信号处理、线程清理、资源释放
- **错误处理**: 完善的异常处理和重试机制
- **实时监控**: 支持暂停/恢复、进度监控

### 📊 适用场景
- **IO密集型操作**: API调用、数据库查询、文件读写
- **任务执行时间较短**: <100ms的任务
- **需要频繁的线程切换**: 大量小任务
- **对内存使用要求不高**: 线程开销相对较小

## 快速开始

### 基本用法

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

### 执行模式选择

#### 并行执行（推荐用于IO密集型）
```python
worker = MultiThreadWorker(
    execution_mode=ThreadExecutionMode.PARALLEL,  # 多线程并行
    job_executor=io_intensive_task
)
```

#### 串行执行（推荐用于需要顺序控制的场景）
```python
worker = MultiThreadWorker(
    execution_mode=ThreadExecutionMode.SERIAL,  # 串行执行
    job_executor=sequential_task
)
```

## 性能优势

### 与多进程对比
- **多线程**: 适合IO密集型任务，线程切换开销小
- **多进程**: 适合CPU密集型任务，绕过GIL限制

### 适用场景
- **API调用**: 网络请求、REST API调用
- **数据库操作**: 查询、更新、批量操作
- **文件处理**: 读写文件、数据解析
- **Web爬虫**: 网页抓取、数据提取

## 使用建议

1. **任务特性**: 确保任务是IO密集型的
2. **线程数设置**: 通常设置为CPU核心数的2-4倍
3. **资源管理**: 注意数据库连接池、网络连接等资源
4. **错误处理**: 实现完善的异常处理和重试机制
5. **监控日志**: 使用详细日志监控执行过程

## 示例用法

### API数据获取
```python
def fetch_api_data(data):
    """获取API数据"""
    url = data['url']
    response = requests.get(url)
    return response.json()

worker = MultiThreadWorker(
    max_workers=20,
    execution_mode=ThreadExecutionMode.PARALLEL,
    job_executor=fetch_api_data
)
```

### 数据库批量操作
```python
def update_database(data):
    """更新数据库记录"""
    record_id = data['id']
    new_data = data['data']
    # 执行数据库更新
    return update_record(record_id, new_data)

worker = MultiThreadWorker(
    max_workers=5,
    execution_mode=ThreadExecutionMode.PARALLEL,
    job_executor=update_database
)
```

## 配置参数

### 基本参数
- **`max_workers`**: 最大工作线程数
- **`execution_mode`**: 执行模式（SERIAL/PARALLEL）
- **`job_executor`**: 任务执行函数
- **`timeout`**: 任务超时时间
- **`enable_monitoring`**: 是否启用监控
- **`is_verbose`**: 是否启用详细日志

### 高级功能
- **暂停/恢复**: 支持运行时暂停和恢复执行
- **任务取消**: 支持取消正在执行的任务
- **信号处理**: 自动处理Ctrl+C和系统信号
- **优雅关闭**: 确保线程正确释放

## 注意事项

1. **GIL限制**: Python的全局解释器锁限制了真正的并行计算
2. **线程安全**: 确保共享资源的线程安全访问
3. **资源管理**: 正确管理数据库连接、网络连接等资源
4. **内存使用**: 大量线程会增加内存开销

## 最佳实践

1. **选择合适的线程数**: 根据IO等待时间调整线程数
2. **资源池管理**: 使用连接池管理数据库和网络连接
3. **错误处理**: 实现完善的异常处理和重试机制
4. **性能监控**: 监控线程使用情况和执行效率
5. **测试验证**: 在实际环境中测试和优化性能

## 与ProcessWorker的选择

### 使用MultiThreadWorker的场景
- IO密集型操作（API调用、数据库查询）
- 任务执行时间较短（<100ms）
- 需要频繁的线程切换
- 对内存使用要求不高

### 使用ProcessWorker的场景
- CPU密集型计算（数据分析、算法计算）
- 任务执行时间较长（>100ms）
- 需要充分利用多核CPU
- 内存使用可控
