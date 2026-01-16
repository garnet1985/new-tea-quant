# Worker 模块单元测试

## 📁 测试组织方式

采用 `__test__` 文件夹方式，测试代码与源代码放在同一目录下：

```
core/infra/worker/
├── multi_process/
│   └── process_worker.py
├── multi_thread/
│   └── futures_worker.py
├── executors/
├── queues/
├── monitors/
├── schedulers/
├── aggregators/
├── error_handlers/
├── orchestrator.py
└── __test__/
    ├── __init__.py
    ├── test_process_worker.py
    ├── test_multi_thread_worker.py
    ├── test_list_source.py
    ├── test_simple_aggregator.py
    ├── test_simple_error_handler.py
    ├── test_memory_monitor.py
    └── README.md
```

## 🎯 设计理念

- **就近原则**：测试代码与源代码放在一起，便于维护
- **模块化**：每个模块的测试独立，互不干扰
- **清晰命名**：`__test__` 明确表示测试目录

## 🚀 运行测试

### 运行所有测试

```bash
# 在项目根目录
pytest core/infra/worker/__test__/ -v
```

### 运行特定测试文件

```bash
pytest core/infra/worker/__test__/test_process_worker.py -v
```

### 运行特定测试类

```bash
pytest core/infra/worker/__test__/test_process_worker.py::TestProcessWorker -v
```

### 运行特定测试方法

```bash
pytest core/infra/worker/__test__/test_process_worker.py::TestProcessWorker::test_init_default -v
```

## 📋 测试覆盖

### ProcessWorker 测试
- ✅ `__init__()` - 初始化（默认/配置）
- ✅ `resolve_max_workers()` - Worker 数量解析（自动/手动）
- ✅ `run_jobs()` - 执行任务（QUEUE/BATCH 模式）
- ✅ `run_jobs()` - 处理失败任务
- ✅ `get_stats()` - 获取统计信息
- ✅ `calculate_workers()` - 计算 worker 数量（不同任务类型）

### MultiThreadWorker 测试
- ✅ `__init__()` - 初始化（默认/配置）
- ✅ `run_jobs()` - 执行任务（PARALLEL/SERIAL 模式）
- ✅ `run_jobs()` - 处理失败任务
- ✅ `get_stats()` - 获取统计信息
- ✅ `pause()` / `resume()` - 暂停和恢复
- ✅ `shutdown()` - 关闭 worker

### ListJobSource 测试
- ✅ `__init__()` - 初始化
- ✅ `get_batch()` - 获取批次
- ✅ `has_more()` - 是否还有更多任务
- ✅ 边界情况（空列表、批次大小大于总数）

### SimpleAggregator 测试
- ✅ `__init__()` - 初始化
- ✅ `add_result()` - 添加结果（成功/失败）
- ✅ `get_summary()` - 获取聚合摘要
- ✅ `reset()` - 重置聚合器

### SimpleErrorHandler 测试
- ✅ `__init__()` - 初始化（默认/带重试次数）
- ✅ `handle_error()` - 错误处理（重试/跳过）
- ✅ `should_retry()` - 判断是否应该重试
- ✅ `get_retry_delay()` - 获取重试延迟时间

### MemoryMonitor 测试
- ✅ `__init__()` - 初始化（默认/指定基线）
- ✅ `update()` - 更新监控状态
- ✅ `get_stats()` - 获取统计信息
- ✅ `get_warnings()` - 获取警告

## 🔧 测试框架

使用 **pytest** 作为测试框架：

- **优点**：
  - 简洁的语法
  - 丰富的断言
  - 详细的错误信息
  - 支持 fixtures
  - 自动发现测试

## 📝 编写测试的注意事项

1. **测试类命名**：`Test{ClassName}`
2. **测试方法命名**：`test_{method_name}`
3. **使用断言**：`assert` 语句
4. **测试隔离**：每个测试应该独立，不依赖其他测试
5. **Mock 使用**：使用 `unittest.mock` 模拟外部依赖
6. **条件导入**：使用 `try-except ImportError` 处理 pytest 未安装的情况

## ⚠️ 注意事项

1. **多进程测试**：ProcessWorker 的测试需要特别注意，因为多进程环境下的测试可能比较复杂
2. **依赖检查**：某些测试需要 `psutil` 等外部依赖，测试会检查依赖是否存在
3. **环境隔离**：确保测试不会影响实际运行环境

## ✅ 当前状态

- ✅ 核心功能测试已覆盖
- ✅ 使用 Mock 避免真实依赖
- ✅ 测试运行时间：< 5 秒（取决于系统性能）

## 📊 测试统计

- **测试文件数**：6
- **测试类数**：6
- **测试方法数**：约 30+
