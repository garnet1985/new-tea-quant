# System Cache 表

## 📋 概述

`system_cache` 表用于存储系统级的状态和配置信息，如批量更新的偏移量等。

## 📁 表结构

```json
{
    "name": "system_cache",
    "primaryKey": "id",
    "fields": [
        {
            "name": "id",
            "type": "int",
            "isRequired": true,
            "autoIncrement": true
        },
        {
            "name": "value",
            "type": "text",
            "isRequired": true
        }
    ]
}
```

## 🔄 从 meta_info 迁移

如果数据库中已有 `meta_info` 表，需要：

1. **确认 system_cache 表是否存在**：
   - 如果存在，检查字段名是否为 `value`（如果是 `info`，需要重命名）

2. **迁移数据**（如果 meta_info 表有数据）：
   ```sql
   -- 如果 system_cache 表不存在，先创建
   CREATE TABLE IF NOT EXISTS system_cache (
       id INT AUTO_INCREMENT PRIMARY KEY,
       value TEXT NOT NULL
   );
   
   -- 如果 system_cache 表存在但字段是 info，需要重命名
   ALTER TABLE system_cache CHANGE COLUMN info value TEXT NOT NULL;
   
   -- 迁移数据（如果 meta_info 表有数据）
   INSERT INTO system_cache (id, value)
   SELECT id, info FROM meta_info
   ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
   
   -- 删除 meta_info 表（迁移完成后）
   -- DROP TABLE IF EXISTS meta_info;
   ```

## 📝 使用方法

```python
from app.core.modules.data_manager import DataManager

data_mgr = DataManager()
data_mgr.initialize()

# 获取系统缓存
cache_model = data_mgr.get_model('system_cache')
cache_value = cache_model.load_by_key('corporate_finance_batch_offset')

# 保存系统缓存
cache_model.save_cache('corporate_finance_batch_offset', '123')
```

## 🔑 预定义的缓存键

- `corporate_finance_batch_offset`: 企业财务批量更新的偏移量

未来可以扩展更多缓存键。
