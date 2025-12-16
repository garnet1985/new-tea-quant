# 复权因子事件表（adj_factor_events）

## 📋 概述

`adj_factor_events` 表用于存储复权因子的变化事件（除权除息日），而不是每日的复权因子。

这是复权因子优化方案的核心表，相比旧的 `adj_factor` 表（每日存储），可以减少 **98.8%** 的存储空间。

---

## 🎯 设计目标

1. **只存储变化点**：只在复权因子变化时（除权除息日）插入记录
2. **支持精确计算**：存储复权因子和与 AKShare 的差异，支持精确的前复权价格计算
3. **高效查询**：通过索引快速查询指定日期的有效因子

---

## 📊 表结构

### 字段说明

| 字段名 | 类型 | 说明 | 示例 |
|-------|------|------|------|
| `id` | VARCHAR(16) | 股票代码（含市场后缀） | `000001.SZ` |
| `event_date` | DATE | 除权除息日期 | `2024-06-14` |
| `adj_factor` | DECIMAL(12,6) | 复权因子 F(t) | `125.049600` |
| `constant_diff` | DECIMAL(12,4) | 与 AKShare 前复权价格的固定差异 | `0.0000` |
| `created_at` | DATETIME | 记录创建时间 | `2024-06-14 10:00:00` |
| `updated_at` | DATETIME | 记录更新时间 | `2024-06-14 10:00:00` |

### 主键和索引

- **主键**：`(id, event_date)` - 确保每个股票的每个除权日只有一条记录
- **索引**：
  - `idx_id` - 按股票查询
  - `idx_event_date` - 按日期查询
  - `idx_id_date_desc` - 用于查询最近的有效因子（`ORDER BY event_date DESC`）

---

## 🔧 使用方法

### 1. 获取 Model 实例

```python
from app.data_manager import DataManager

data_manager = DataManager()
data_manager.initialize()

adj_factor_events_model = data_manager.get_model('adj_factor_events')
```

### 2. 查询指定日期的复权因子

```python
# 查询指定日期的有效因子（使用最近的有效因子）
factor_event = adj_factor_events_model.load_factor_by_date('000001.SZ', '2024-12-12')

if factor_event:
    adj_factor = factor_event['adj_factor']  # 127.784100
    constant_diff = factor_event['constant_diff']  # 0.0000
```

### 3. 查询最新复权因子

```python
# 查询股票的最新复权因子
latest_event = adj_factor_events_model.load_latest_factor('000001.SZ')

if latest_event:
    latest_factor = latest_event['adj_factor']  # 134.579400
```

### 4. 保存复权因子事件

```python
# 保存单个事件
adj_factor_events_model.save_event(
    stock_id='000001.SZ',
    event_date='2024-06-14',
    adj_factor=125.049600,
    constant_diff=0.0000
)

# 批量保存
events = [
    {
        'id': '000001.SZ',
        'event_date': '2024-06-14',
        'adj_factor': 125.049600,
        'constant_diff': 0.0000,
    },
    # ... 更多事件
]
adj_factor_events_model.save_events(events)
```

### 5. 计算前复权价格

```python
def calculate_qfq_price(stock_id: str, date: str, raw_price: float) -> float:
    """
    计算精确的前复权价格（AKShare 标准）
    """
    # 查询当日和最新的复权因子
    factor_event = adj_factor_events_model.load_factor_by_date(stock_id, date)
    latest_event = adj_factor_events_model.load_latest_factor(stock_id)
    
    if not factor_event or not latest_event:
        # 如果没有复权因子，返回原始价格
        return raw_price
    
    F_t = factor_event['adj_factor']
    F_T = latest_event['adj_factor']
    constant_diff = factor_event['constant_diff']
    
    # 计算公式：AKShare_QFQ = raw_price × F(t) / F(T) + constantDiff
    qfq_price = raw_price * F_t / F_T + constant_diff
    
    return qfq_price
```

---

## 📈 数据示例

### 平安银行（000001.SZ）的复权事件

| event_date | adj_factor | constant_diff |
|-----------|------------|---------------|------------|
| 2023-12-12 | 116.713000 | 0.0000 | initial |
| 2024-06-14 | 125.049600 | 0.0000 | dividend |
| 2024-10-10 | 127.784100 | 0.0000 | dividend |
| 2025-06-12 | 131.787800 | 0.0000 | dividend |
| 2025-10-15 | 134.579400 | 0.0000 | dividend |

**说明**：
- 2023-12-12 到 2024-06-13：使用因子 116.713000
- 2024-06-14 到 2024-10-09：使用因子 125.049600
- 2024-10-10 到 2025-06-11：使用因子 127.784100
- 2025-06-12 到 2025-10-14：使用因子 131.787800
- 2025-10-15 至今：使用因子 134.579400

---

## 🔍 查询示例

### 查询所有复权事件

```python
events = adj_factor_events_model.load_by_stock('000001.SZ')
# 返回按日期升序排列的所有事件
```

### 查询日期范围内的事件

```python
events = adj_factor_events_model.load_by_date_range(
    stock_id='000001.SZ',
    start_date='2024-01-01',
    end_date='2024-12-31'
)
```

### 查询价格差异

```python
constant_diff = adj_factor_events_model.load_latest_constant_diff('000001.SZ', '2024-12-12')
# 返回该日期最近的有效 constant_diff
```

---

## ⚠️ 注意事项

1. **日期格式**：`event_date` 使用 `DATE` 类型（YYYY-MM-DD），但查询时也支持 YYYYMMDD 格式
2. **因子精度**：`adj_factor` 使用 `DECIMAL(12,6)`，保证精度
3. **差异初始值**：`constant_diff` 初始为 0.0，需要通过 AKShare API 更新
4. **唯一性**：主键 `(id, event_date)` 确保不会重复插入

---

## 📚 相关文档

- [复权因子优化方案文档](../../../../tmp/ADJ_FACTOR_OPTIMIZATION_FINAL.md)
- [数据库迁移指南](./MIGRATION.md)
- [Model API 文档](./model.py)

---

**最后更新：** 2025-12-15

