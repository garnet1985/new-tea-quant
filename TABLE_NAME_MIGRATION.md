# 表名迁移说明：stock_kline → stock_kline_qfq

## 修改概述

由于数据源从不复权改为前复权，需要将表名从 `stock_kline` 更新为 `stock_kline_qfq` 以区分不同复权方式的数据。

## 已完成的修改

### 1. 数据库表结构
- ✅ `stocks-py/utils/db/tables/stock_kline/schema.json`
  - 表名：`stock_kline` → `stock_kline_qfq`

### 2. 数据模型层
- ✅ `stocks-py/utils/db/tables/stock_kline/model.py`
  - SQL查询中的表名：`stock_kline` → `stock_kline_qfq`

### 3. 数据存储层
- ✅ `stocks-py/app/data_source/providers/tushare/main_storage.py`
  - 表实例获取：`stock_kline` → `stock_kline_qfq`
  - SQL查询中的表名：`stock_kline` → `stock_kline_qfq`

### 4. 策略层
- ✅ `stocks-py/app/analyzer/strategy/historicLow/strategy.py`
  - 表实例获取：`stock_kline` → `stock_kline_qfq`

### 5. 测试文件
- ✅ `stocks-py/test_strategy_simple.py`
- ✅ `stocks-py/debug_data.py`
- ✅ `stocks-py/debug_dates.py`
- ✅ `stocks-py/test_db.py`
- ✅ `stocks-py/check_earlier_data.py`

### 6. 文档
- ✅ `stocks-py/utils/db/README.md`
  - 表映射配置示例

## 数据库操作

### 1. 创建新表
```sql
-- 如果需要保留旧数据，先创建新表
CREATE TABLE stock_kline_qfq LIKE stock_kline;
```

### 2. 数据迁移（可选）
```sql
-- 如果需要迁移现有数据
INSERT INTO stock_kline_qfq SELECT * FROM stock_kline;
```

### 3. 删除旧表（谨慎操作）
```sql
-- 确认新表数据正常后，可以删除旧表
DROP TABLE stock_kline;
```

## 验证步骤

### 1. 检查表结构
```python
from utils.db.db_manager import DatabaseManager

db = DatabaseManager()
kline_table = db.get_table_instance('stock_kline_qfq')
print(f"表名: {kline_table.table_name}")
```

### 2. 测试数据查询
```python
# 测试数据查询是否正常
data = kline_table.get_all_klines_by_term('000001', 'daily')
print(f"查询到 {len(data)} 条数据")
```

### 3. 测试策略
```bash
python test_strategy_simple.py
```

## 注意事项

1. **数据一致性**：确保所有代码都使用新的表名
2. **备份数据**：在删除旧表前先备份数据
3. **测试验证**：在生产环境应用前充分测试
4. **监控日志**：观察是否有表名相关的错误

## 回滚方案

如果出现问题，可以：
1. 恢复旧表名
2. 重新指向旧表
3. 检查数据完整性

## 总结

所有代码层面的表名引用已经更新完成。现在系统将使用 `stock_kline_qfq` 表来存储前复权数据，与原来的不复权数据完全分离。 