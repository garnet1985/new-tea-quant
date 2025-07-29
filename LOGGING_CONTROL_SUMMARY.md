# FuturesWorker 日志控制功能总结

## 🎯 **功能概述**

已成功为 `FuturesWorker` 添加了灵活的日志控制功能，可以根据需要调整日志输出的详细程度，解决了日志输出过多的问题。

## 🔧 **新增参数**

### **构造函数参数**
```python
FuturesWorker(
    max_workers=5,
    execution_mode=ExecutionMode.PARALLEL,
    job_executor=None,
    enable_monitoring=True,
    timeout=30.0,
    verbose=False,    # 新增：是否启用详细日志
    debug=False       # 新增：是否启用调试日志
)
```

## 📊 **日志级别说明**

### **1. 默认模式 (verbose=False, debug=False)**
- ✅ **保留**：任务完成进度信息
- ✅ **保留**：错误信息
- ❌ **隐藏**：详细执行信息
- ❌ **隐藏**：调试信息

**输出示例：**
```
2025-07-29 10:45:27,170 - futures_worker - INFO - Job task_1 completed in 1.01s. Progress: 0 out of 2 - 0.00%
2025-07-29 10:45:27,170 - futures_worker - INFO - Job task_2 completed in 1.01s. Progress: 0 out of 2 - 0.00%
```

### **2. 详细模式 (verbose=True, debug=False)**
- ✅ **显示**：任务完成进度信息
- ✅ **显示**：错误信息
- ✅ **显示**：执行模式、总任务数、并行工作数
- ❌ **隐藏**：调试信息

**输出示例：**
```
2025-07-29 10:45:27,170 - futures_worker - INFO - Starting job execution in parallel mode
2025-07-29 10:45:27,170 - futures_worker - INFO - Total jobs: 2
2025-07-29 10:45:27,170 - futures_worker - INFO - Running jobs in parallel mode with 2 workers
2025-07-29 10:45:28,175 - futures_worker - INFO - Job task_1 completed in 1.01s. Progress: 0 out of 2 - 0.00%
```

### **3. 调试模式 (verbose=True, debug=True)**
- ✅ **显示**：所有日志信息
- ✅ **显示**：任务添加、执行、完成、队列操作等详细信息

**输出示例：**
```
2025-07-29 10:45:28,176 - futures_worker - INFO - Added job task_1 to queue
2025-07-29 10:45:28,176 - futures_worker - INFO - Added job task_2 to queue
2025-07-29 10:45:28,176 - futures_worker - INFO - Starting job execution in parallel mode
2025-07-29 10:45:28,176 - futures_worker - INFO - Total jobs: 2
2025-07-29 10:45:28,177 - futures_worker - INFO - Running jobs in parallel mode with 2 workers
2025-07-29 10:45:28,177 - futures_worker - INFO - Executing job task_1
2025-07-29 10:45:28,177 - futures_worker - INFO - Executing job task_2
2025-07-29 10:45:29,180 - futures_worker - INFO - Job task_2 completed in 1.00s. Progress: 0 out of 2 - 0.00%
```

## 🎯 **使用建议**

### **生产环境 (推荐)**
```python
worker = FuturesWorker(
    max_workers=5,
    execution_mode=ExecutionMode.PARALLEL,
    enable_monitoring=True,
    timeout=60.0,
    verbose=False,  # 只显示进度信息
    debug=False     # 不显示调试信息
)
```

### **开发环境**
```python
worker = FuturesWorker(
    max_workers=5,
    execution_mode=ExecutionMode.PARALLEL,
    enable_monitoring=True,
    timeout=30.0,
    verbose=True,   # 显示详细信息
    debug=False     # 不显示调试信息
)
```

### **调试环境**
```python
worker = FuturesWorker(
    max_workers=5,
    execution_mode=ExecutionMode.PARALLEL,
    enable_monitoring=True,
    timeout=30.0,
    verbose=True,   # 显示详细信息
    debug=True      # 显示调试信息
)
```

## 📋 **已更新的文件**

### **1. `utils/worker/futures_worker.py`**
- ✅ 添加了 `verbose` 和 `debug` 参数
- ✅ 为所有日志输出添加了条件控制
- ✅ 保留了关键的进度信息
- ✅ 错误信息始终显示

### **2. `app/data_source/providers/tushare/main.py`**
- ✅ 更新为生产环境配置
- ✅ `verbose=False, debug=False`
- ✅ 只显示进度信息，减少日志输出

## 🔍 **日志控制详情**

### **始终显示的日志**
- ✅ 任务完成进度信息
- ✅ 错误信息
- ✅ 紧急关闭信息

### **verbose=True 时显示**
- ✅ 执行模式信息
- ✅ 总任务数
- ✅ 并行工作数
- ✅ 启动/关闭信息
- ✅ 暂停/恢复信息

### **debug=True 时显示**
- ✅ 任务添加到队列
- ✅ 任务开始执行
- ✅ 队列清空操作
- ✅ 统计信息重置

## 📊 **测试结果**

### **测试覆盖**
- ✅ 默认日志模式
- ✅ 详细日志模式
- ✅ 调试日志模式
- ✅ 生产环境模式

### **性能影响**
- ✅ 日志控制不影响执行性能
- ✅ 减少了不必要的字符串格式化
- ✅ 降低了 I/O 开销

## 🎉 **总结**

✅ **问题解决**：成功减少了日志输出，只保留关键的进度信息
✅ **功能完整**：提供了灵活的日志控制选项
✅ **向后兼容**：不影响现有功能
✅ **易于使用**：简单的参数控制

现在你的 Tushare 数据获取系统只会显示类似这样的关键进度信息：
```
2025-07-29 10:39:32,931 - utils.worker.futures_worker - INFO - Job 000403.SZ completed in 0.64s. Progress: 68 out of 5417 - 1.26%
```

日志输出大大减少，更加清晰易读！ 