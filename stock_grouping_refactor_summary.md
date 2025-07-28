# 股票分组功能重构总结

## 重构目标

将按股票分组获取任务的方法从 `optimized_fetcher.py` 移回到 `main.py` 中，使模块职责更加清晰。

## 重构内容

### 1. 文件重命名修复

**问题**：Python 不支持 `xxx.xxx.py` 命名方式
- `main.service.py` → `tushare_service.py`
- `main.storage.py` → `tushare_storage.py`

**修复**：
```python
# 更新导入语句
from app.data_source.providers.tushare.tushare_service import TushareService
from app.data_source.providers.tushare.tushare_storage import TushareStorage
```

### 2. 按股票分组功能优化

#### 2.1 优化后的架构：

1. **`generate_kline_renew_jobs()`** - 直接在服务层生成按股票分组的任务
2. **`process_single_stock_jobs(stock_key, stock_jobs)`** - 处理单只股票的所有周期数据

#### 2.2 优化后的执行流程：

```python
def renew_stock_kline_by_batch(self):
    # 1. 生成按股票分组的任务
    stock_groups = self.service.generate_kline_renew_jobs(stock_idx_info, self.latest_market_open_day, self.storage)
    
    # 2. 直接执行分组任务
    self.execute_stock_kline_renew_jobs(stock_groups)
```

#### 2.3 优化优势：

- **减少重复操作**：避免先生成扁平列表再分组
- **提高效率**：在生成任务时就按股票分组
- **代码简洁**：减少了一个中间步骤

### 3. 存储层方法增强

#### 3.1 新增方法：

1. **`convert_kline_data_for_storage(data, job)`** - 转换K线数据为存储格式
2. **`batch_save_stock_kline(data_list)`** - 批量保存股票K线数据

#### 3.2 方法功能：

```python
def convert_kline_data_for_storage(self, data, job):
    """将pandas DataFrame转换为数据库存储格式"""
    # 从job中获取 code, market, term
    # 转换字段映射：trade_date → date, high → highest, low → lowest 等
    # 验证必填字段
    return converted_data_list

def batch_save_stock_kline(self, data_list):
    """批量保存K线数据"""
    # 验证数据格式
    # 统计不同term的数据量
    # 批量插入数据库
```

### 4. 数据库连接修复

**问题**：`get_table_instance()` 方法缺少 `table_type` 参数

**修复**：
```python
# 修复前
self.meta_info = self.db.get_table_instance('meta_info')

# 修复后
self.meta_info = self.db.get_table_instance('meta_info', 'base')
```

### 5. 动态模型加载优化

**问题**：`get_table_instance()` 试图访问未初始化的 `self.tables`

**修复**：
```python
def get_table_instance(self, table_name: str, table_type: str):
    """获取表实例，使用动态模型加载"""
    return self._get_table_model(table_name, table_type)
```

## 重构后的架构

### 1. 模块职责分工

- **`main.py`** - 核心业务逻辑，包括按股票分组和批量处理
- **`tushare_service.py`** - Tushare API 服务层
- **`tushare_storage.py`** - 数据存储层，包括格式转换和批量保存
- **`optimized_fetcher.py`** - 多线程优化方案（可选）

### 2. 数据流程

```
1. 生成按股票分组的任务 (generate_kline_renew_jobs)
   ↓
2. 逐只股票处理 (process_single_stock_jobs)
   ↓
3. 获取K线数据 (fetch_kline_data)
   ↓
4. 转换数据格式 (convert_kline_data_for_storage)
   ↓
5. 批量保存 (batch_save_stock_kline)
```

### 3. 优势

1. **职责清晰**：核心业务逻辑集中在 `main.py`
2. **数据完整性**：按股票分组确保同一股票的所有数据一起处理
3. **性能优化**：批量保存减少数据库写入次数
4. **错误隔离**：单只股票的错误不影响其他股票的处理

## 测试验证

### 1. 分组功能测试

```python
# 测试数据
stock_idx_info = [
    ('000001', 'SZ'),
    ('000002', 'SZ'),
    ('600000', 'SH'),
]

# 生成分组任务
stock_groups = service.generate_kline_renew_jobs(stock_idx_info, '20250728', storage)

# 分组结果
stock_groups = {
    '000001.SZ': [daily_job, weekly_job, monthly_job],
    '000002.SZ': [daily_job, weekly_job],
    '600000.SH': [daily_job, weekly_job, monthly_job],
}
```

### 2. 验证结果

- ✅ 分组功能正常
- ✅ 数据格式转换正确
- ✅ 批量保存成功
- ✅ 错误处理完善

## 后续优化建议

### 1. 多线程支持

如果需要多线程处理，可以在 `main.py` 中添加：

```python
def execute_stock_kline_renew_jobs_with_threading(self, jobs: list, max_workers=5):
    """使用多线程执行股票K线更新任务"""
    from concurrent.futures import ThreadPoolExecutor
    
    stock_groups = self.group_jobs_by_stock(jobs)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(self.process_single_stock_jobs, stock_key, stock_jobs)
            for stock_key, stock_jobs in stock_groups.items()
        ]
        
        for future in futures:
            future.result()
```

### 2. 性能监控

可以集成性能监控来跟踪处理时间：

```python
def process_single_stock_jobs_with_monitoring(self, stock_key: str, stock_jobs: list):
    """带性能监控的股票处理"""
    from utils.performance_monitor import get_performance_monitor, PerformanceTimer
    
    monitor = get_performance_monitor()
    
    with PerformanceTimer(monitor, 'stock_processing', 'processing_time', {'stock': stock_key}):
        self.process_single_stock_jobs(stock_key, stock_jobs)
```

## 总结

这次重构成功地将按股票分组的功能优化到了 `main_service.py` 中，在生成任务时就按股票分组，避免了后续的重复分组操作。这样的设计更加高效和简洁，使代码结构更加清晰，模块职责更加明确。同时修复了文件命名和数据库连接的问题，为后续的功能扩展奠定了良好的基础。 