# 复权因子事件表（adj_factor_event）

## 📋 概述

`adj_factor_event` 表用于存储复权因子的变化事件（除权除息日），而不是每日的复权因子。

这是复权因子优化方案的核心表，相比旧的 `adj_factor` 表（每日存储），可以减少 **98.8%** 的存储空间。

---

## 🎯 设计目标

1. **只存储变化点**：只在复权因子变化时（除权除息日）插入记录
2. **支持精确计算**：存储复权因子和与 EastMoney 的差异（`qfq_diff`），支持精确的前复权价格计算
3. **高效查询**：通过索引快速查询指定日期的有效因子

---

## 📊 表结构

### 字段说明

| 字段名 | 类型 | 说明 | 示例 |
|-------|------|------|------|
| `id` | VARCHAR(16) | 股票代码（含市场后缀） | `000001.SZ` |
| `event_date` | VARCHAR(8) | 除权除息日期（YYYYMMDD） | `20240614` |
| `factor` | FLOAT | Tushare 复权因子 F(t) | `125.049600` |
| `qfq_diff` | FLOAT | 与 EastMoney 前复权价格的固定差异 | `-1.8500` |
| `last_update` | DATETIME | 记录最后更新时间 | `2024-06-14 10:00:00` |

### 主键和索引

- **主键**：`(id, event_date)` - 确保每个股票的每个除权日只有一条记录
- **索引**：
  - `idx_id_event_date` - 主键索引（唯一）
  - `idx_id` - 按股票查询
  - `idx_event_date` - 按日期查询
  - `idx_id_date_desc` - 用于查询最近的有效因子（`ORDER BY event_date DESC`）

---

## 🔧 使用方法

### 1. 获取 Model 实例

```python
from app.core_modules.data_manager.data_manager import DataManager

data_manager = DataManager()
data_manager.initialize()

adj_factor_event_model = data_manager.get_model('adj_factor_event')
```

### 2. 查询指定日期的复权因子

```python
# 查询指定日期的有效因子（使用最近的有效因子）
factor_event = adj_factor_event_model.load_factor_by_date('000001.SZ', '20241212')

if factor_event:
    factor = factor_event['factor']  # 127.784100
    qfq_diff = factor_event['qfq_diff']  # -1.8500
```

### 3. 查询最新复权因子

```python
# 查询股票的最新复权因子
latest_event = adj_factor_event_model.load_latest_factor('000001.SZ')

if latest_event:
    latest_factor = latest_event['factor']  # 134.579400
```

### 4. 保存复权因子事件

```python
# 保存单个事件
adj_factor_event_model.save_event(
    stock_id='000001.SZ',
    event_date='20240614',  # YYYYMMDD 格式
    factor=125.049600,
    qfq_diff=-1.8500
)

# 批量保存
events = [
    {
        'id': '000001.SZ',
        'event_date': '20240614',  # YYYYMMDD 格式
        'factor': 125.049600,
        'qfq_diff': -1.8500,
    },
    # ... 更多事件
]
adj_factor_event_model.save_events(events)
```

### 5. 计算前复权价格

```python
def calculate_qfq_price(stock_id: str, date: str, raw_price: float) -> float:
    """
    计算精确的前复权价格（EastMoney 标准）
    
    根据最新发现：在除权日之间的区间内，Tushare 裸价与 EastMoney 前复权价的差值为常量 qfq_diff
    计算公式：qfq_price = raw_price - qfq_diff
    """
    # 查询指定日期的有效因子事件
    factor_event = adj_factor_event_model.load_factor_by_date(stock_id, date)
    
    if not factor_event:
        # 如果没有复权因子，返回原始价格
        return raw_price
    
    qfq_diff = factor_event.get('qfq_diff', 0.0)
    
    # 计算公式：EastMoney_QFQ = raw_price - qfq_diff
    qfq_price = raw_price - qfq_diff
    
    return qfq_price
```

### 6. 使用 DataService 计算前复权 K 线

```python
from app.core_modules.data_manager.data_manager import DataManager

data_manager = DataManager()
data_manager.initialize()

stock_service = data_manager.get_data_service('stock_related.stock')

# 加载前复权 K 线数据
qfq_klines = stock_service.load_qfq_klines(
    stock_id='000001.SZ',
    term='daily',
    start_date='2024-01-01',
    end_date='2024-12-31'
)
```

---

## 📈 数据示例

### 平安银行（000001.SZ）的复权事件

| event_date | factor | qfq_diff | 说明 |
|-----------|--------|---------|------|
| 20231212 | 116.713000 | -1.8500 | initial |
| 20240614 | 125.049600 | -0.7953 | dividend |
| 20241010 | 127.784100 | 0.0000 | dividend |
| 20250612 | 131.787800 | 0.1427 | dividend |
| 20251015 | 134.579400 | 0.0000 | dividend |

**说明**：
- `event_date` 使用 `YYYYMMDD` 格式（字符串）
- `factor` 是 Tushare 的复权因子
- `qfq_diff` 是 `raw_price - eastmoney_qfq`，在除权日之间的区间内为常量
- 2023-12-12 到 2024-06-13：使用因子 116.713000，qfq_diff = -1.8500
- 2024-06-14 到 2024-10-09：使用因子 125.049600，qfq_diff = -0.7953
- 2024-10-10 到 2025-06-11：使用因子 127.784100，qfq_diff = 0.0000
- 2025-06-12 到 2025-10-14：使用因子 131.787800，qfq_diff = 0.1427
- 2025-10-15 至今：使用因子 134.579400，qfq_diff = 0.0000

---

## 🔍 查询示例

### 查询所有复权事件

```python
events = adj_factor_event_model.load_by_stock('000001.SZ')
# 返回按日期升序排列的所有事件
```

### 查询日期范围内的事件

```python
events = adj_factor_event_model.load_by_date_range(
    stock_id='000001.SZ',
    start_date='20240101',  # YYYYMMDD 格式
    end_date='20241231'     # YYYYMMDD 格式
)
```

### 查询最新价格差异

```python
qfq_diff = adj_factor_event_model.load_latest_qfq_diff('000001.SZ', '20241212')
# 返回该日期最近的有效 qfq_diff
```

### 批量查询多只股票的最新因子

```python
stock_ids = ['000001.SZ', '600000.SH', '600519.SH']
latest_factors_map = adj_factor_event_model.load_latest_factors_batch(stock_ids)
# 返回: {'000001.SZ': {...}, '600000.SH': {...}, ...}
```

---

## ⚠️ 注意事项

1. **日期格式**：`event_date` 使用 `VARCHAR(8)` 类型存储 `YYYYMMDD` 格式字符串（如 `20240614`），查询时也支持 `YYYY-MM-DD` 格式，会自动转换
2. **因子精度**：`factor` 使用 `FLOAT` 类型
3. **差异计算**：`qfq_diff = raw_price - eastmoney_qfq`，在除权日之间的区间内为常量，只在除权日更新
4. **唯一性**：主键 `(id, event_date)` 确保不会重复插入
5. **第一根 K 线**：如果股票有 K 线数据但没有复权事件，会在第一根 K 线日期创建一条记录（factor 使用第一个可用因子或 1.0，qfq_diff 根据实际情况计算）

---

## 🔬 算法说明

### 前复权价格计算公式

根据实际验证，发现以下规律：

**对于 EastMoney 的前复权数据**：
- 在除权日之间的区间内，`raw_price - eastmoney_qfq = qfq_diff`（常量）
- 计算公式：`qfq_price = raw_price - qfq_diff`
- `qfq_diff` 只在除权日发生变化

**注意**：此规律仅适用于前复权（QFQ），不适用于后复权（HFQ）。

### 数据获取流程

1. **预筛选**：使用 Tushare `adj_factor` API 找出有因子变化的股票
2. **全量获取**：对需要更新的股票，获取：
   - Tushare `adj_factor`（全量复权因子）
   - Tushare `daily_kline`（全量原始收盘价）
   - EastMoney `qfq_kline`（全量前复权价格）
3. **计算差异**：对每个除权日，计算 `qfq_diff = raw_close - eastmoney_qfq`
4. **保存事件**：只保存除权日的记录（包括第一根 K 线日期）

---

## 📚 相关文档

- [复权因子优化方案文档](../../../../tmp/ADJ_FACTOR_OPTIMIZATION_FINAL.md)
- [Schema 设计文档](./SCHEMA_DESIGN.md)
- [Model API 文档](./model.py)
- [Handler 实现](../../../data_source/defaults/handlers/adj_factor_event_handler.py)

---

## 🔄 数据更新

数据通过 `AdjFactorEventHandler` 自动更新：

- **触发条件**：
  1. 股票没有复权记录（首次构建）
  2. 股票超过 15 天未更新且有新的复权事件
- **更新策略**：全量更新（删除旧数据，插入新数据），确保数据一致性
- **保存策略**：每完成一只股票的处理就立即保存，避免中断导致数据丢失

---

**最后更新：** 2025-12-18
