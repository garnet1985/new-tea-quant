# Database Tables - 数据库表操作指南

## 概述

本目录包含了系统中所有数据库表的定义和操作说明。表分为两大类：基础表（base）和策略表（strategy）。

## 目录结构

```
tables/
├── base/                   # 基础表（核心业务数据）
│   ├── adj_factor/         # 复权因子表
│   ├── meta_info/          # 元信息表
│   ├── stock_index/        # 股票指数表
│   └── stock_kline/        # 股票K线表
├── strategy/               # 策略表（策略相关数据）
│   └── historicLow/        # 历史低点策略表
└── README.md               # 本文档
```

## 基础表操作指南

### 1. 复权因子表 (`adj_factor/`)

**用途**: 存储股票的复权因子数据，用于计算前复权、后复权价格。

**表结构**:
```sql
CREATE TABLE adj_factor (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ts_code VARCHAR(10) NOT NULL,      -- 股票代码
    trade_date DATE NOT NULL,          -- 交易日期
    adj_factor DECIMAL(10,6) NOT NULL, -- 复权因子
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**常用操作**:
```python
from utils.db import DatabaseManager

db = DatabaseManager()
db.connect_sync()

# 查询某股票的复权因子
query = """
SELECT trade_date, adj_factor 
FROM adj_factor 
WHERE ts_code = %s 
ORDER BY trade_date DESC 
LIMIT 10
"""
result = db.execute_sync_query(query, ('000001.SZ',))

# 插入复权因子数据
insert_query = """
INSERT INTO adj_factor (ts_code, trade_date, adj_factor) 
VALUES (%s, %s, %s)
"""
db.execute_sync_query(insert_query, ('000001.SZ', '2024-01-15', 1.0))

db.disconnect_sync()
```

### 2. 元信息表 (`meta_info/`)

**用途**: 存储系统配置、版本信息等元数据。

**表结构**:
```sql
CREATE TABLE meta_info (
    id INT PRIMARY KEY AUTO_INCREMENT,
    key_name VARCHAR(100) NOT NULL UNIQUE,  -- 配置键名
    key_value TEXT,                         -- 配置值
    description VARCHAR(500),                -- 描述
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**常用操作**:
```python
# 查询系统配置
query = "SELECT key_name, key_value FROM meta_info WHERE key_name = %s"
result = db.execute_sync_query(query, ('system_version',))

# 更新配置
update_query = """
UPDATE meta_info 
SET key_value = %s, updated_at = CURRENT_TIMESTAMP 
WHERE key_name = %s
"""
db.execute_sync_query(update_query, ('2.0.0', 'system_version'))
```

### 3. 股票指数表 (`stock_index/`)

**用途**: 存储股票的基本信息，如代码、名称、行业等。

**表结构**:
```sql
CREATE TABLE stock_index (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ts_code VARCHAR(10) NOT NULL UNIQUE,    -- 股票代码
    symbol VARCHAR(6) NOT NULL,             -- 股票代码（不含后缀）
    name VARCHAR(100) NOT NULL,             -- 股票名称
    area VARCHAR(50),                       -- 地区
    industry VARCHAR(50),                   -- 行业
    market VARCHAR(20),                     -- 市场类型
    list_date DATE,                         -- 上市日期
    is_hs VARCHAR(1),                       -- 是否沪深港通
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**常用操作**:
```python
# 查询所有A股股票
query = """
SELECT ts_code, name, industry, area 
FROM stock_index 
WHERE market = '主板' 
ORDER BY ts_code
"""
result = db.execute_sync_query(query)

# 查询特定行业的股票
query = """
SELECT ts_code, name, list_date 
FROM stock_index 
WHERE industry = %s 
ORDER BY list_date DESC
"""
result = db.execute_sync_query(query, ('银行',))

# 批量插入股票信息
stocks_data = [
    ('000001.SZ', '000001', '平安银行', '深圳', '银行', '主板', '1991-04-03', 'N'),
    ('000002.SZ', '000002', '万科A', '深圳', '房地产', '主板', '1991-01-29', 'N')
]

insert_query = """
INSERT INTO stock_index (ts_code, symbol, name, area, industry, market, list_date, is_hs) 
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""
for stock in stocks_data:
    db.execute_sync_query(insert_query, stock)
```

### 4. 股票K线表 (`stock_kline/`)

**用途**: 存储股票的K线数据，包括开盘价、收盘价、最高价、最低价、成交量等。

**表结构**:
```sql
CREATE TABLE stock_kline (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ts_code VARCHAR(10) NOT NULL,      -- 股票代码
    trade_date DATE NOT NULL,          -- 交易日期
    open DECIMAL(10,2) NOT NULL,       -- 开盘价
    high DECIMAL(10,2) NOT NULL,       -- 最高价
    low DECIMAL(10,2) NOT NULL,        -- 最低价
    close DECIMAL(10,2) NOT NULL,      -- 收盘价
    pre_close DECIMAL(10,2),           -- 前收盘价
    change DECIMAL(10,2),              -- 涨跌额
    pct_chg DECIMAL(10,4),            -- 涨跌幅
    vol DECIMAL(20,2),                 -- 成交量
    amount DECIMAL(20,2),              -- 成交额
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_ts_date (ts_code, trade_date)
);
```

**常用操作**:
```python
# 查询某股票的K线数据
query = """
SELECT trade_date, open, high, low, close, vol, amount 
FROM stock_kline 
WHERE ts_code = %s 
ORDER BY trade_date DESC 
LIMIT 100
"""
result = db.execute_sync_query(query, ('000001.SZ',))

# 查询某时间段的K线数据
query = """
SELECT trade_date, open, high, low, close, vol 
FROM stock_kline 
WHERE ts_code = %s 
  AND trade_date BETWEEN %s AND %s 
ORDER BY trade_date
"""
result = db.execute_sync_query(query, ('000001.SZ', '2024-01-01', '2024-01-31'))

# 计算技术指标（移动平均线）
query = """
SELECT trade_date, close,
       AVG(close) OVER (ORDER BY trade_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as ma5,
       AVG(close) OVER (ORDER BY trade_date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as ma20
FROM stock_kline 
WHERE ts_code = %s 
ORDER BY trade_date DESC 
LIMIT 50
"""
result = db.execute_sync_query(query, ('000001.SZ',))

# 批量插入K线数据
kline_data = [
    ('000001.SZ', '2024-01-15', 10.50, 10.80, 10.30, 10.60, 10.40, 0.20, 1.92, 1000000, 10600000),
    ('000001.SZ', '2024-01-16', 10.60, 10.90, 10.50, 10.80, 10.60, 0.20, 1.89, 1200000, 12960000)
]

insert_query = """
INSERT INTO stock_kline (ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount) 
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
for kline in kline_data:
    db.execute_sync_query(insert_query, kline)
```

## 高级查询示例

### 1. 多表联合查询

```python
# 查询股票基本信息和最新K线数据
query = """
SELECT 
    s.ts_code,
    s.name,
    s.industry,
    k.trade_date,
    k.close,
    k.vol,
    k.amount
FROM stock_index s
JOIN stock_kline k ON s.ts_code = k.ts_code
WHERE s.industry = %s
  AND k.trade_date = (
      SELECT MAX(trade_date) 
      FROM stock_kline 
      WHERE ts_code = s.ts_code
  )
ORDER BY k.vol DESC
LIMIT 20
"""
result = db.execute_sync_query(query, ('银行',))
```

### 2. 统计分析查询

```python
# 统计各行业股票数量
query = """
SELECT 
    industry,
    COUNT(*) as stock_count,
    AVG(DATEDIFF(CURDATE(), list_date)/365) as avg_list_years
FROM stock_index 
WHERE market = '主板'
GROUP BY industry 
HAVING stock_count > 5
ORDER BY stock_count DESC
"""
result = db.execute_sync_query(query)

# 计算某股票的收益率统计
query = """
SELECT 
    ts_code,
    COUNT(*) as trading_days,
    AVG(pct_chg) as avg_return,
    STDDEV(pct_chg) as return_std,
    MIN(pct_chg) as min_return,
    MAX(pct_chg) as max_return
FROM stock_kline 
WHERE ts_code = %s 
  AND trade_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
GROUP BY ts_code
"""
result = db.execute_sync_query(query, ('000001.SZ',))
```

### 3. 数据更新和维护

```python
# 更新股票名称
update_query = """
UPDATE stock_index 
SET name = %s, updated_at = CURRENT_TIMESTAMP 
WHERE ts_code = %s
"""
db.execute_sync_query(update_query, ('新股票名称', '000001.SZ'))

# 删除过期的K线数据（保留最近2年）
delete_query = """
DELETE FROM stock_kline 
WHERE trade_date < DATE_SUB(CURDATE(), INTERVAL 2 YEAR)
"""
db.execute_sync_query(delete_query)

# 创建索引优化查询性能
index_queries = [
    "CREATE INDEX idx_stock_kline_ts_date ON stock_kline(ts_code, trade_date)",
    "CREATE INDEX idx_stock_index_industry ON stock_index(industry)",
    "CREATE INDEX idx_adj_factor_ts_date ON adj_factor(ts_code, trade_date)"
]

for index_query in index_queries:
    try:
        db.execute_sync_query(index_query)
        print(f"索引创建成功: {index_query}")
    except Exception as e:
        print(f"索引创建失败: {e}")
```

## 数据导入导出

### 1. 从CSV导入数据

```python
import pandas as pd
from utils.db import DatabaseManager

def import_stock_data_from_csv(csv_file, table_name):
    """从CSV文件导入股票数据"""
    # 读取CSV文件
    df = pd.read_csv(csv_file)
    
    # 连接数据库
    db = DatabaseManager()
    db.connect_sync()
    
    try:
        # 批量插入数据
        for _, row in df.iterrows():
            # 根据表名构建不同的插入语句
            if table_name == 'stock_index':
                query = """
                INSERT INTO stock_index (ts_code, symbol, name, area, industry, market, list_date) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                values = (row['ts_code'], row['symbol'], row['name'], 
                         row['area'], row['industry'], row['market'], row['list_date'])
            elif table_name == 'stock_kline':
                query = """
                INSERT INTO stock_kline (ts_code, trade_date, open, high, low, close, vol, amount) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (row['ts_code'], row['trade_date'], row['open'], 
                         row['high'], row['low'], row['close'], row['vol'], row['amount'])
            
            db.execute_sync_query(query, values)
        
        print(f"成功导入 {len(df)} 条数据到 {table_name} 表")
        
    except Exception as e:
        print(f"导入失败: {e}")
        db.rollback()
    finally:
        db.disconnect_sync()

# 使用示例
import_stock_data_from_csv('stock_index.csv', 'stock_index')
import_stock_data_from_csv('stock_kline.csv', 'stock_kline')
```

### 2. 导出数据到CSV

```python
def export_table_to_csv(table_name, output_file, where_clause=""):
    """导出表数据到CSV文件"""
    db = DatabaseManager()
    db.connect_sync()
    
    try:
        # 构建查询语句
        if where_clause:
            query = f"SELECT * FROM {table_name} WHERE {where_clause}"
        else:
            query = f"SELECT * FROM {table_name}"
        
        # 执行查询
        result = db.execute_sync_query(query)
        
        if result:
            # 转换为DataFrame并导出
            df = pd.DataFrame(result)
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"成功导出 {len(df)} 条数据到 {output_file}")
        else:
            print("没有数据需要导出")
            
    except Exception as e:
        print(f"导出失败: {e}")
    finally:
        db.disconnect_sync()

# 使用示例
export_table_to_csv('stock_index', 'exported_stock_index.csv')
export_table_to_csv('stock_kline', 'exported_stock_kline.csv', "ts_code = '000001.SZ'")
```

## 性能优化建议

### 1. 索引优化

- 为经常查询的字段创建索引
- 使用复合索引优化多字段查询
- 定期分析索引使用情况

### 2. 查询优化

- 避免使用 `SELECT *`，只查询需要的字段
- 使用 `LIMIT` 限制结果集大小
- 合理使用 `WHERE` 条件过滤数据

### 3. 批量操作

- 使用批量插入替代单条插入
- 使用事务包装批量操作
- 定期清理历史数据

### 4. 连接池管理

- 合理设置连接池大小
- 及时释放数据库连接
- 使用连接池监控工具

## 注意事项

1. **数据一致性**: 在修改基础表数据前，确保没有其他进程正在使用
2. **备份策略**: 定期备份重要数据，特别是基础表数据
3. **权限控制**: 限制对基础表的写权限，只允许授权用户修改
4. **数据验证**: 插入数据前验证数据格式和完整性
5. **性能监控**: 监控查询性能，及时发现和解决性能问题

## 联系支持

如有问题或建议，请查看：
- [utils/db/README.md](../README.md) - 数据库模块主文档
- 代码注释和错误日志
- 数据库管理员
