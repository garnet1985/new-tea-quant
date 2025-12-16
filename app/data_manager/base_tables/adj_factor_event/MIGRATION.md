# 复权因子优化方案 - 数据库迁移指南

## 📋 概述

本文档说明如何从旧的 `adj_factor` 表（每日存储）迁移到新的 `adj_factor_events` 表（只存储复权事件）。

---

## 🎯 迁移目标

### 旧方案（`adj_factor` 表）
- **存储方式**：每日存储复权因子（qfq, hfq）
- **存储量**：~250 条/年/股（每个交易日）
- **问题**：98.8% 的数据是重复的（因子不变）

### 新方案（`adj_factor_events` 表）
- **存储方式**：只存储复权因子变化的日期（除权除息日）
- **存储量**：~3 条/年/股（平均每年 3 次除权）
- **优势**：减少 98.8% 的存储空间

---

## 📊 表结构对比

### 旧表：`adj_factor`

```sql
CREATE TABLE adj_factor (
    id VARCHAR(16) NOT NULL,           -- 股票代码
    date VARCHAR(8) NOT NULL,          -- 日期（YYYYMMDD）
    qfq FLOAT NOT NULL,                -- 前复权因子
    hfq FLOAT NOT NULL,                -- 后复权因子
    last_update TIMESTAMP,             -- 更新时间
    PRIMARY KEY (id, date),
    INDEX idx_ts_code (id),
    INDEX idx_date (date)
);
```

### 新表：`adj_factor_events`

```sql
CREATE TABLE adj_factor_events (
    id VARCHAR(16) NOT NULL,           -- 股票代码
    event_date DATE NOT NULL,         -- 除权日期（YYYY-MM-DD）
    adj_factor DECIMAL(12,6) NOT NULL, -- 复权因子 F(t)
    constant_diff DECIMAL(12,4) DEFAULT 0.0, -- 与 AKShare 的差异
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id, event_date),
    INDEX idx_id (id),
    INDEX idx_event_date (event_date),
    INDEX idx_id_date_desc (id, event_date)
);
```

---

## 🔄 迁移步骤

### 步骤 1：创建新表

新表会在 `DataManager.initialize()` 时自动创建（通过 `schema.json`）。

如果手动创建：

```sql
-- 表结构已由 schema.json 定义，通过 DatabaseManager 自动创建
-- 或手动执行：
CREATE TABLE adj_factor_events (
    id VARCHAR(16) NOT NULL,
    event_date DATE NOT NULL,
    adj_factor DECIMAL(12,6) NOT NULL,
    constant_diff DECIMAL(12,4) DEFAULT 0.0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id, event_date),
    INDEX idx_id (id),
    INDEX idx_event_date (event_date),
    INDEX idx_id_date_desc (id, event_date)
);
```

### 步骤 2：数据迁移脚本

从旧表提取复权因子变化事件：

```python
"""
从 adj_factor 表提取复权因子变化事件，迁移到 adj_factor_events 表
"""
from app.data_manager import DataManager
from utils.date.date_utils import DateUtils

def migrate_adj_factor_events():
    """
    迁移复权因子数据
    """
    # 初始化
    data_manager = DataManager(is_verbose=True)
    data_manager.initialize()
    
    old_model = data_manager.get_model('adj_factor')
    new_model = data_manager.get_model('adj_factor_events')
    
    # 获取所有股票
    stock_list_model = data_manager.get_model('stock_list')
    stocks = stock_list_model.load_active_stocks()
    
    print(f"开始迁移 {len(stocks)} 只股票的复权因子数据...")
    
    total_events = 0
    
    for stock in stocks:
        stock_id = stock['id']
        
        # 获取该股票的所有复权因子（按日期排序）
        factors = old_model.load_by_stock(stock_id)
        
        if not factors:
            continue
        
        # 找出复权因子变化的日期
        events = []
        prev_qfq = None
        
        for factor in factors:
            current_qfq = factor['qfq']
            current_date = factor['date']
            
            # 转换为标准日期格式
            event_date = DateUtils.yyyymmdd_to_yyyy_mm_dd(current_date)
            
            # 检测因子变化（阈值 > 0.0001）
            if prev_qfq is not None and abs(current_qfq - prev_qfq) > 0.0001:
                # 这是一个复权事件
                events.append({
                    'id': stock_id,
                    'event_date': event_date,
                    'adj_factor': current_qfq,
                    'constant_diff': 0.0,  # 初始值，后续通过 AKShare API 更新
                })
            
            prev_qfq = current_qfq
        
        # 如果没有事件，但第一条记录也需要保存（作为初始因子）
        if not events and factors:
            first_factor = factors[0]
            events.append({
                'id': stock_id,
                'event_date': DateUtils.yyyymmdd_to_yyyy_mm_dd(first_factor['date']),
                'adj_factor': first_factor['qfq'],
                'constant_diff': 0.0,
            })
        
        # 保存事件
        if events:
            new_model.save_events(events)
            total_events += len(events)
            print(f"  ✅ {stock_id}: {len(events)} 个复权事件")
    
    print(f"\n✅ 迁移完成！共迁移 {total_events} 个复权事件")
    print(f"   平均每只股票: {total_events / len(stocks):.2f} 个事件")

if __name__ == '__main__':
    migrate_adj_factor_events()
```

### 步骤 3：更新代码引用

#### 3.1 更新 Model 使用

**旧代码：**
```python
adj_factor_model = data_manager.get_model('adj_factor')
factor = adj_factor_model.load_by_date(stock_id, date)
```

**新代码：**
```python
adj_factor_events_model = data_manager.get_model('adj_factor_events')
factor_event = adj_factor_events_model.load_factor_by_date(stock_id, date)
if factor_event:
    adj_factor = factor_event['adj_factor']
    constant_diff = factor_event['constant_diff']
```

#### 3.2 更新前复权价格计算

**旧代码：**
```python
# 假设直接使用 qfq 因子
qfq_price = raw_price * qfq_factor
```

**新代码：**
```python
# 使用新的公式
factor_event = adj_factor_events_model.load_factor_by_date(stock_id, date)
latest_event = adj_factor_events_model.load_latest_factor(stock_id)

if factor_event and latest_event:
    F_t = factor_event['adj_factor']
    F_T = latest_event['adj_factor']
    constant_diff = factor_event['constant_diff']
    
    # 计算 AKShare 标准的前复权价格
    qfq_price = raw_price * F_t / F_T + constant_diff
```

### 步骤 4：兼容性处理（可选）

如果需要保持向后兼容，可以：

1. **保留旧表**：`adj_factor` 表保留，但不再更新
2. **双写策略**：新代码写入 `adj_factor_events`，同时写入 `adj_factor`（过渡期）
3. **读取降级**：如果 `adj_factor_events` 没有数据，降级到 `adj_factor`

```python
def get_adj_factor(stock_id: str, date: str) -> float:
    """
    获取复权因子（兼容新旧表）
    """
    # 优先使用新表
    new_model = data_manager.get_model('adj_factor_events')
    factor_event = new_model.load_factor_by_date(stock_id, date)
    
    if factor_event:
        return factor_event['adj_factor']
    
    # 降级到旧表
    old_model = data_manager.get_model('adj_factor')
    factor = old_model.load_by_date(stock_id, date)
    
    if factor:
        return factor['qfq']
    
    # 默认返回 1.0
    return 1.0
```

---

## 📝 数据验证

迁移后验证数据完整性：

```python
def validate_migration():
    """
    验证迁移数据的完整性
    """
    data_manager = DataManager(is_verbose=True)
    data_manager.initialize()
    
    old_model = data_manager.get_model('adj_factor')
    new_model = data_manager.get_model('adj_factor_events')
    
    # 随机选择几只股票验证
    stock_list_model = data_manager.get_model('stock_list')
    stocks = stock_list_model.load_active_stocks()[:10]
    
    for stock in stocks:
        stock_id = stock['id']
        
        # 获取旧数据的最新因子
        old_factors = old_model.load_by_stock(stock_id)
        if not old_factors:
            continue
        
        old_latest = old_factors[-1]
        old_latest_qfq = old_latest['qfq']
        
        # 获取新数据的最新因子
        new_latest = new_model.load_latest_factor(stock_id)
        if not new_latest:
            print(f"  ⚠️  {stock_id}: 新表无数据")
            continue
        
        new_latest_factor = new_latest['adj_factor']
        
        # 对比
        diff = abs(old_latest_qfq - new_latest_factor)
        if diff > 0.0001:
            print(f"  ❌ {stock_id}: 因子不一致 (旧={old_latest_qfq}, 新={new_latest_factor})")
        else:
            print(f"  ✅ {stock_id}: 因子一致 ({new_latest_factor})")
```

---

## ⚠️ 注意事项

1. **备份数据**：迁移前务必备份 `adj_factor` 表
2. **测试环境**：先在测试环境验证迁移脚本
3. **逐步迁移**：可以分批迁移，先迁移部分股票验证
4. **监控**：迁移后监控新表的使用情况
5. **回滚方案**：保留旧表一段时间，确保可以回滚

---

## 🚀 后续优化

迁移完成后：

1. **更新 AKShare 差异**：运行脚本更新 `constant_diff` 字段
2. **清理旧表**：确认新表稳定后，可以归档或删除旧表
3. **更新文档**：更新所有相关文档和代码注释

---

**迁移脚本位置：** `app/data_manager/base_tables/adj_factor_events/migrate.py`（待创建）  
**验证脚本位置：** `app/data_manager/base_tables/adj_factor_events/validate.py`（待创建）

