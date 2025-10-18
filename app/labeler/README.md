# 股票标签算法系统 (Labeler)

## 系统概述

股票标签算法系统负责为股票计算和存储各种标签（如市值规模、行业分类、波动性等），支持增量更新和回测使用。

## 核心设计理念

### 1. 增量更新机制
- **更新周期**：统一2周更新一次
- **智能检测**：只更新距离上次更新超过2周的股票
- **灵活时间点**：每个股票的上次更新时间可以不同
- **非覆盖更新**：保留历史标签数据，只新增或更新

### 2. 标签存储策略
- **数据库结构**：每个股票每个日期一行记录
- **标签格式**：逗号分隔的标签ID字符串存储在`labels`字段
- **标签映射**：通过`LabelMapping`硬编码配置解析标签含义

### 3. 静态标签处理
- **行业标签**：相对稳定，不需要重新计算
- **动态标签**：市值、波动性、成交量、财务指标等需要定期重新计算

## 系统架构

### 核心组件

```
app/labeler/
├── __init__.py              # 主服务入口 LabelerService
├── base_calculator.py       # 标签计算器基类
├── label_mapping.py         # 标签映射定义（硬编码配置）
├── conf/
│   └── config.py           # 标签配置（投入周期、静态分类等）
├── calculators/            # 具体标签计算器
│   ├── market_cap_calculator.py
│   ├── industry_calculator.py
│   ├── volatility_calculator.py
│   ├── volume_calculator.py
│   └── financial_calculator.py
└── evaluator.py            # 标签质量评估
```

### 数据表结构

#### stock_labels 表
```sql
CREATE TABLE stock_labels (
    stock_id VARCHAR(20) NOT NULL,           -- 股票代码
    label_date DATE NOT NULL,                -- 标签计算日期
    labels TEXT NOT NULL,                    -- 标签ID字符串，逗号分隔
    created_at DATETIME,                     -- 创建时间
    updated_at DATETIME,                     -- 更新时间
    PRIMARY KEY (stock_id, label_date)
);
```

## 关键算法流程

### 1. 增量更新流程 (`renew`方法)

```python
def renew(last_market_open_day: str, force_update: bool = False):
    """
    标签数据增量更新接口
    """
    # 1. 生成更新任务列表
    update_jobs = self._generate_update_jobs(last_market_open_day, force_update)
    
    # 2. 执行更新任务
    self._execute_update_jobs(update_jobs, last_market_open_day)
```

### 2. 任务生成逻辑 (`_generate_update_jobs`)

```python
def _generate_update_jobs(last_market_open_day: str, force_update: bool = False):
    """
    生成标签更新任务列表（增量更新）
    """
    if force_update:
        # 强制更新所有股票
        jobs.append({
            'stock_ids': all_stock_ids,
            'target_date': last_market_open_day,
            'force_update': True
        })
    else:
        # 增量更新：检查每个股票是否需要更新
        stocks_needing_update = []
        for stock_id in all_stock_ids:
            if self._stock_needs_incremental_update(stock_id, last_market_open_day):
                stocks_needing_update.append(stock_id)
```

### 3. 股票更新需求判断 (`_stock_needs_incremental_update`)

```python
def _stock_needs_incremental_update(stock_id: str, last_market_open_day: str) -> bool:
    """
    检查股票是否需要增量更新标签（基于2周周期）
    """
    # 1. 获取股票的最后标签更新时间
    last_update_date = self._get_stock_last_label_update_date(stock_id)
    
    # 2. 如果没有标签记录，需要更新
    if last_update_date is None:
        return True
    
    # 3. 计算距离上次更新的天数
    days_since_update = (current_dt - last_update_dt).days
    
    # 4. 判断是否超过更新周期（2周）
    return LabelConfig.should_update_stock(days_since_update)
```

### 4. 标签计算执行 (`_execute_single_update_job`)

```python
def _execute_single_update_job(job: Dict[str, Any], target_date: str):
    """
    执行单个标签更新任务（动态多线程）
    """
    # 1. 获取需要计算的标签分类（排除静态分类）
    categories_to_calculate = []
    for category in LabelMapping.get_categories().keys():
        if not LabelConfig.is_static_category(category):
            categories_to_calculate.append(category)
    
    # 2. 根据股票数量动态决定是否使用多线程
    performance_config = LabelConfig.get_performance_config()
    multithread_threshold = performance_config.get('multithread_threshold', 10)
    
    if len(stock_ids) >= multithread_threshold:
        # 使用多线程计算标签
        self._batch_calculate_labels_multithreaded(stock_ids, target_date, categories_to_calculate)
    else:
        # 使用单线程计算标签
        self.batch_calculate_labels(stock_ids, target_date, categories_to_calculate)
```

### 5. 多线程标签计算 (`_batch_calculate_labels_multithreaded`)

```python
def _batch_calculate_labels_multithreaded(stock_ids: List[str], target_date: str, categories: List[str]):
    """
    多线程批量计算标签（使用FuturesWorker框架）
    """
    # 1. 获取性能配置
    performance_config = LabelConfig.get_performance_config()
    max_workers = performance_config.get('max_workers', 10)
    max_threads_limit = performance_config.get('max_threads_limit', 20)
    
    # 2. 限制最大线程数
    max_workers = min(max_workers, len(stock_ids), max_threads_limit)
    
    # 3. 创建FuturesWorker
    worker = FuturesWorker(
        max_workers=max_workers,
        execution_mode=ThreadExecutionMode.PARALLEL,
        job_executor=self._calculate_single_stock_labels_wrapper,
        enable_monitoring=True,
        timeout=300.0,  # 5分钟超时
        is_verbose=True
    )
    
    # 4. 准备任务数据
    jobs = []
    for stock_id in stock_ids:
        jobs.append({
            'job_id': stock_id,
            'data': {
                'stock_id': stock_id,
                'target_date': target_date,
                'categories': categories
            }
        })
    
    # 5. 执行任务
    stats = worker.run_jobs(jobs)
    
    # 6. 打印统计信息
    worker.print_stats()
```

### 6. 单股票标签计算 (`_calculate_single_stock_labels`)

```python
def _calculate_single_stock_labels(stock_id: str, target_date: str, categories: List[str]):
    """
    计算单只股票的所有标签（多线程调用）
    """
    # 1. 获取数据加载器
    data_loader = self.data_loader
    
    # 2. 计算所有标签分类
    all_labels = []
    for category in categories:
        calculator = self.get_calculator(category)
        if calculator:
            labels = calculator.calculate_labels_for_stock(stock_id, target_date, data_loader)
            if labels:
                all_labels.extend(labels)
    
    # 3. 保存标签到数据库
    if all_labels:
        self._save_stock_labels([stock_id], target_date, {stock_id: all_labels})
    
    return {
        'stock_id': stock_id,
        'labels_count': len(all_labels),
        'categories': categories
    }
```

## 配置管理

### LabelConfig 配置类

```python
class LabelConfig:
    # 统一更新周期（天）
    UPDATE_INTERVAL_DAYS = 14  # 2周更新一次
    
    # 不需要重新计算的标签分类（相对稳定）
    STATIC_CATEGORIES = ['industry']  # 行业标签不需要重新计算
    
    # 性能配置
    PERFORMANCE_CONFIG = {
        'max_workers': 10,                 # 最大工作线程数
        'multithread_threshold': 10,       # 多线程阈值（股票数量）
        'max_threads_limit': 20            # 最大线程数限制
    }
    
    @classmethod
    def should_update_stock(cls, days_since_update: int) -> bool:
        """判断股票是否需要更新标签"""
        return days_since_update >= cls.UPDATE_INTERVAL_DAYS
    
    @classmethod
    def is_static_category(cls, category: str) -> bool:
        """判断标签分类是否为静态（不需要重新计算）"""
        return category in cls.STATIC_CATEGORIES
```

### LabelMapping 标签映射

```python
class LabelMapping:
    # 标签分类定义
    CATEGORIES = {
        'market_cap': '市值规模',
        'industry': '行业分类', 
        'volatility': '波动性',
        'volume': '成交量',
        'financial': '财务指标'
    }
    
    # 具体标签定义
    MARKET_CAP_LABELS = {
        'large_cap': {
            'id': 'large_cap',
            'name': '大盘股',
            'category': 'market_cap',
            'threshold': 10000000000  # 100亿
        },
        # ... 其他标签
    }
```

## 数据流程

### 1. 启动流程 (start.py)
```python
def main():
    # 1. 获取最新市场开放日
    latest_market_open_day = app.get_latest_market_open_day()
    
    # 2. 更新数据源
    app.renew_data(latest_market_open_day)
    
    # 3. 更新标签
    app.renew_labels(latest_market_open_day)
```

### 2. 标签计算流程
```python
def batch_calculate_labels(stock_ids: List[str], target_date: str, categories: List[str]):
    """
    批量计算标签
    """
    # 1. 获取数据加载器
    data_loader = self.data_loader
    
    # 2. 按分类计算标签
    for category in categories:
        calculator = self.get_calculator(category)
        calculator.calculate_batch_labels(stock_ids, target_date, data_loader)
    
    # 3. 保存标签到数据库
    self._save_stock_labels(stock_ids, target_date, calculated_labels)
```

### 3. 标签存储流程
```python
def _upsert_stock_label(stock_id: str, target_date: str, labels: List[str]):
    """
    插入或更新股票标签记录
    """
    # 1. 将标签列表转换为逗号分隔的字符串
    labels_str = ','.join(labels)
    
    # 2. 使用UPSERT语句
    sql = """
    INSERT INTO stock_labels (stock_id, label_date, labels, created_at, updated_at)
    VALUES (%s, %s, %s, NOW(), NOW())
    ON DUPLICATE KEY UPDATE 
        labels = %s,
        updated_at = NOW()
    """
```

## 使用方式

### 1. 策略回测中使用标签
```python
# 查询股票在指定日期的标签
sql = """
SELECT stock_id, labels 
FROM stock_labels 
WHERE stock_id = %s AND label_date = %s
"""

# 解析标签
labels_str = result['labels']  # "large_cap,finance,high_volatility"
label_ids = labels_str.split(',')

# 通过LabelMapping获取标签含义
for label_id in label_ids:
    label_def = LabelMapping.get_label_by_id(label_id.strip())
    category = label_def['category']
    name = label_def['name']
```

### 2. 手动触发更新
```python
# 强制更新所有标签
labeler.renew('20241201', force_update=True)

# 增量更新（按2周周期）
labeler.renew('20241201', force_update=False)
```

## 关键特性

### 1. 增量更新优势
- **性能优化**：只更新需要更新的股票，避免重复计算
- **资源节约**：减少不必要的API调用和计算资源消耗
- **灵活性**：每个股票可以有不同的上次更新时间

### 2. 动态多线程处理
- **智能切换**：根据股票数量自动选择单线程或多线程模式
- **可配置阈值**：通过配置控制多线程触发条件
- **FuturesWorker框架**：使用我们自己封装的多线程执行器
- **IO密集型优化**：针对标签计算的IO密集型特点优化
- **进度监控**：实时显示多线程处理进度和统计信息

### 3. 数据一致性
- **历史保留**：所有历史标签数据都保留，支持回测
- **原子操作**：使用UPSERT确保数据一致性
- **错误恢复**：失败时不更新last_update，确保下次重新尝试

### 4. 扩展性
- **模块化设计**：每个标签计算器独立，易于添加新标签
- **配置驱动**：通过配置文件控制更新频率和静态分类
- **统一接口**：所有计算器继承自BaseLabelCalculator

## 注意事项

1. **数据依赖**：标签计算依赖K线数据、财务数据等，确保这些数据已更新
2. **计算资源**：批量计算标签可能消耗较多计算资源，建议在低峰期运行
3. **存储空间**：随着时间推移，标签数据会持续增长，需要定期清理或归档
4. **标签一致性**：修改标签定义后，历史数据可能需要重新计算

## 故障排除

### 常见问题

1. **数据库连接错误**：检查数据库配置和连接状态
2. **标签计算失败**：检查依赖数据是否完整（K线数据、财务数据等）
3. **更新任务为空**：检查股票列表和更新条件配置
4. **标签解析错误**：检查LabelMapping配置是否正确

### 调试建议

1. **启用详细日志**：设置日志级别为DEBUG查看详细执行过程
2. **分批测试**：先用少量股票测试，确认逻辑正确后再全量运行
3. **数据验证**：定期检查标签数据的完整性和准确性
