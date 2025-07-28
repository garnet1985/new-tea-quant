# 新的表结构实现总结

## 🎯 实现目标

✅ **简化表结构**：去除 `base` 和 `strategy` 的区分，`tables` 文件夹下默认都是 base table  
✅ **统一结构**：每个表文件夹都需要 `schema.json` 和继承 `BaseTableModel` 的 `model.py`  
✅ **动态注册**：通过 `registerTable` 方法注册自定义表，前缀为 `cust_`  
✅ **自动创建**：注册的表在启动时自动创建  

## 📁 新的文件结构

```
utils/db/
├── db_manager.py      # 统一的数据库管理器（默认线程安全）
├── db_model.py        # 基础表模型（支持线程安全）
├── config.py          # 数据库配置
├── __init__.py        # 包初始化文件
├── README.md          # 文档
└── tables/            # 表结构定义
    ├── stock_kline/
    │   ├── schema.json
    │   └── model.py
    ├── stock_index/
    │   ├── schema.json
    │   └── model.py
    └── meta_info/
        ├── schema.json
        └── model.py
```

## 🔧 核心功能

### 1. 基础表（Base Tables）

**位置**：`utils/db/tables/` 目录下的每个子目录  
**要求**：每个表目录必须包含：
- `schema.json` - 表结构定义
- `model.py` - 继承自 `BaseTableModel` 的自定义模型类

**自动加载**：系统启动时自动扫描 `tables/` 目录，发现所有符合结构的表

### 2. 注册表（Registered Tables）

**注册方式**：通过 `register_table()` 方法动态注册  
**命名规则**：自动添加 `cust_` 前缀  
**支持功能**：
- 自定义 schema 定义
- 自定义模型类（可选）
- 自动表创建

## 🚀 使用方法

### 基础表使用

```python
from utils.db.db_manager import get_db_manager

db = get_db_manager()

# 获取基础表实例
stock_kline_table = db.get_table_instance('stock_kline')

# 使用基础方法
count = stock_kline_table.count()
data = stock_kline_table.load_many(condition="code = %s", params=('000001',))

# 使用自定义方法（如果存在）
if hasattr(stock_kline_table, 'get_stock_by_code'):
    stock_info = stock_kline_table.get_stock_by_code('000001')
```

### 注册自定义表

```python
from utils.db.db_manager import get_db_manager
from utils.db.db_model import BaseTableModel

db = get_db_manager()

# 定义自定义表 schema
custom_schema = {
    "name": "cust_user_profile",
    "fields": [
        {"name": "id", "type": "INT", "isRequired": True, "autoIncrement": True},
        {"name": "user_id", "type": "VARCHAR", "length": 50, "isRequired": True},
        {"name": "profile_data", "type": "TEXT", "isRequired": False}
    ],
    "primaryKey": "id",
    "indexes": [
        {"name": "idx_user_id", "fields": ["user_id"], "unique": True}
    ]
}

# 定义自定义模型类
class CustomUserProfileModel(BaseTableModel):
    def __init__(self, table_name, connected_db):
        super().__init__(table_name, connected_db)
    
    def get_user_profile(self, user_id):
        return self.load_one("user_id = %s", (user_id,))

# 注册表
table_name = db.register_table('user_profile', custom_schema, CustomUserProfileModel)
# 返回: 'cust_user_profile'

# 使用注册的表
custom_table = db.get_table_instance('cust_user_profile')
profile = custom_table.get_user_profile('user123')
```

### 表创建

```python
# 创建所有表（包括基础表和注册表）
db.create_tables()
```

## 🔄 兼容性

### 保留的兼容性方法

```python
# 新的统一方法
table = db.get_table_instance('stock_kline')

# 兼容性方法（仍然可用）
table = db.get_base_table_instance('stock_kline')  # 等同于 get_table_instance
table = db.get_strategy_table_instance('stock_kline')  # 已废弃，但可用
```

### 废弃的功能

- ❌ `table_type` 参数（不再需要区分 base/strategy）
- ❌ `TABLES` 和 `STRATEGY_TABLES` 配置（现在直接从目录读取）
- ❌ `TABLE_SCHEMA_PATH` 配置（现在直接从目录读取）

## 🧪 测试验证

### 运行测试

```bash
# 运行功能测试
python test_new_table_structure.py

# 运行使用示例
python table_structure_usage_example.py
```

### 测试覆盖

✅ **文件结构测试**：验证基础表目录结构  
✅ **基础表测试**：验证基础表加载和操作  
✅ **注册表测试**：验证自定义表注册功能  
✅ **表创建测试**：验证自动表创建  
✅ **兼容性测试**：验证向后兼容性  

## 📊 性能特性

### 线程安全

- ✅ 默认启用线程安全
- ✅ 连接池管理
- ✅ 异步写入队列
- ✅ 线程本地连接

### 自动优化

- ✅ 大数据量自动使用异步写入
- ✅ 小数据量直接执行
- ✅ 连接自动重连
- ✅ 错误重试机制

## 🎉 总结

新的表结构实现了以下目标：

1. **简化管理**：去除了复杂的类型区分，统一管理
2. **灵活扩展**：支持动态注册自定义表
3. **自动发现**：自动扫描和加载基础表
4. **向后兼容**：保持现有代码的兼容性
5. **线程安全**：默认支持多线程环境
6. **易于使用**：简洁的 API 设计

这个新的表结构为项目提供了更好的可维护性和扩展性，同时保持了与现有代码的兼容性。 