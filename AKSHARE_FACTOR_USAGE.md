# AKShare 复权因子使用指南

## 功能概述

AKShare 复权因子功能专门用于获取和存储复权因子到数据库表中，配合 Tushare 的不复权K线数据使用。AKShare 类不提供任何对外换算接口，只负责数据获取和存储。

## 架构设计

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Tushare   │    │   AKShare   │    │   策略层    │
│             │    │             │    │             │
│ 不复权K线数据 │    │  复权因子    │    │ 复权价格计算 │
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ stock_kline │    │ adj_factor  │    │ 策略回测    │
│   表        │    │   表        │    │ 实时交易    │
└─────────────┘    └─────────────┘    └─────────────┘
```

## 主要特性

1. **专注复权因子**：只负责获取和存储复权因子，不处理K线数据
2. **更新频率控制**：默认7天更新间隔，避免频繁更新
3. **主流一致性**：使用 AKShare 的复权因子，与主流数据源一致
4. **纯数据存储**：不提供任何对外换算接口，只负责数据获取和存储

## 使用方法

### 1. 初始化

```python
from utils.db.db_manager import DatabaseManager
from app.data_source.providers.akshare.main import AKShare

# 初始化数据库连接
db = DatabaseManager()
db.initialize()

# 初始化 AKShare
akshare = AKShare(db, is_verbose=True)
```

### 2. 更新复权因子

```python
# 正常更新（带时间控制）
test_stocks = [
    {'code': '000001', 'market': 'SZ'},
    {'code': '600000', 'market': 'SH'}
]
result = akshare.renew_stock_K_line_factors(stock_index=test_stocks)

# 强制更新（忽略时间限制）
result = akshare.force_update_adj_factors(stock_index=test_stocks)
```

### 3. 验证复权因子存储

```python
# 直接从存储层获取复权因子
factor = akshare.storage.get_adj_factor('000001', 'SZ', '20250801')
print(f"复权因子: {factor}")
# 输出: {'qfq_factor': 1.0, 'hfq_factor': 154.336319, ...}

# 获取最新复权因子
latest_factor = akshare.storage.get_latest_adj_factor('000001', 'SZ')

# 批量获取复权因子
factors = akshare.storage.get_adj_factors_by_date_range('000001', 'SZ', '20250801', '20250802')
```

## 策略层集成示例

### 回测场景

```python
def calculate_adj_price_for_backtest(stock_code, market, trade_date, raw_price, adj_type='hfq'):
    """
    回测时计算复权价格
    
    Args:
        stock_code: 股票代码
        market: 市场代码
        trade_date: 交易日期
        raw_price: Tushare 提供的不复权价格
        adj_type: 复权类型 ('qfq' 或 'hfq')
    
    Returns:
        复权价格
    """
    # 从数据库获取复权因子
    factor = akshare.storage.get_adj_factor(stock_code, market, trade_date)
    if not factor:
        return None
    
    # 根据复权类型选择因子
    if adj_type.lower() == 'qfq':
        factor_value = factor['qfq_factor']
    elif adj_type.lower() == 'hfq':
        factor_value = factor['hfq_factor']
    else:
        return None
    
    # 计算复权价格
    return raw_price * factor_value

# 使用示例
raw_close = 10.0  # 从 Tushare 获取的不复权收盘价
adj_close = calculate_adj_price_for_backtest('000001', 'SZ', '20250801', raw_close, 'hfq')
```

### 实时交易场景

```python
def get_real_time_adj_price(stock_code, market, current_raw_price):
    """
    实时交易时计算复权价格
    
    Args:
        stock_code: 股票代码
        market: 市场代码
        current_raw_price: 当前不复权价格
    
    Returns:
        复权价格
    """
    # 获取最新复权因子
    latest_factor = akshare.storage.get_latest_adj_factor(stock_code, market)
    if not latest_factor:
        return None
    
    # 计算复权价格
    adj_price = current_raw_price * latest_factor['hfq_factor']
    return adj_price
```

## 数据表结构

### adj_factor 表

```sql
CREATE TABLE adj_factor (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(10) NOT NULL,           -- 股票代码
    market VARCHAR(2) NOT NULL,          -- 市场代码 (SZ/SH)
    date VARCHAR(8) NOT NULL,            -- 交易日期 (YYYYMMDD)
    qfq_factor DECIMAL(10,6) NOT NULL,   -- 前复权因子
    hfq_factor DECIMAL(10,6) NOT NULL,   -- 后复权因子
    created_at DATETIME NOT NULL,        -- 创建时间
    updated_at DATETIME NOT NULL,        -- 更新时间
    UNIQUE KEY uk_code_market_date (code, market, date)
);
```

### meta_info 表

```sql
-- 存储更新状态信息
akshare_adj_factors_last_update = '2025-08-02 14:20:57'
```

## 配置选项

### 更新间隔设置

在 `app/data_source/providers/akshare/main_settings.py` 中：

```python
factor_update_interval_days = 7  # 默认7天更新间隔
```

## 注意事项

1. **数据一致性**：确保 Tushare 和 AKShare 使用相同的股票代码格式
2. **更新频率**：复权因子变化不频繁，7天更新间隔通常足够
3. **错误处理**：如果某个日期的复权因子不存在，需要自行处理
4. **性能考虑**：大量计算时建议批量获取复权因子，避免频繁数据库查询
5. **接口限制**：AKShare 类不提供任何对外换算接口，只负责数据获取和存储

## 故障排除

### 常见问题

1. **复权因子不存在**
   ```python
   # 检查是否已更新复权因子
   status = akshare.check_update_status()
   print(f"更新状态: {status}")
   ```

2. **计算价格异常**
   ```python
   # 检查复权因子值
   factor = akshare.storage.get_adj_factor('000001', 'SZ', '20250801')
   print(f"复权因子: {factor}")
   ```

3. **更新失败**
   ```python
   # 强制更新
   result = akshare.force_update_adj_factors(stock_index=test_stocks)
   print(f"更新结果: {result}")
   ``` 