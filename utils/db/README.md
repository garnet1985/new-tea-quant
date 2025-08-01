# Database Module - 数据库模块

## 概述

数据库模块提供了统一的MySQL数据库管理功能，支持自动创建数据库、表结构管理、以及同步/异步操作。

## 目录结构

```
utils/db/
├── __init__.py              # 包初始化文件
├── config.py               # 数据库配置
├── db_manager.py           # 数据库管理器
├── db_model.py             # 数据表基本的删查增改的API
├── README.md               # 本文档
└── tables/                 # 表结构定义
    ├── base/               # 基础表（不建议修改）
    │   └── stock_index/
    │       └── schema.json（必要）
    │       └── model.py    (可选，需要继承 db_model.py 中的基类TableModel)
    └── strategy/           # 策略表（可自定义）
        └── [your_table]/
            └── schema.json（必要）
            └── model.py    (可选，需要继承 db_model.py 中的基类TableModel)
```

## 重要说明

### 1. 目录结构限制

**⚠️ 重要：`tables` 下的 `base` 和 `strategy` 目录名是固定的，不能修改！**

- 新的文件夹不会被自动识别
- 只有 `base` 和 `strategy` 目录下的表会被自动创建
- 目录结构必须严格按照上述格式

### 2. 表分类

#### Base Tables（基础表）
- **位置**: `tables/base/`
- **用途**: 存储核心业务数据（股票信息、K线数据等）
- **建议**: 不建议修改，保持与现有数据库的兼容性
- **示例**: `stock_index`, `stock_kline`, `industry_index` 等

#### Strategy Tables（策略表）
- **位置**: `tables/strategy/`
- **用途**: 存储策略相关的数据
- **特点**: 可以自由添加、修改、删除
- **示例**: `hl_opportunity_history`, `test_strategy` 等

### 3. 添加新表的步骤

#### 步骤1：创建目录
```bash
mkdir -p utils/db/tables/strategy/your_table_name
```

#### 步骤2：创建 schema.json
```json
{
    "name": "your_table_name",
    "primaryKey": "id",
    "fields": [
        {
            "name": "id",
            "type": "int",
            "isRequired": true
        },
        {
            "name": "name",
            "type": "varchar",
            "length": 255,
            "isRequired": true
        },
        {
            "name": "created_at",
            "type": "datetime",
            "isRequired": true
        }
    ],
    "indexes": [
        {
            "name": "idx_name",
            "columns": ["name"],
            "type": "BTREE"
        }
    ]
}
```

#### 步骤3：更新配置
在 `config.py` 中添加表映射：
```python
STRATEGY_TABLES = {
    'your_table_name': 'your_table_name',
    # ... 其他表
}
```

## 使用方法

### 基本使用

```python
from utils.db import DatabaseManager

# 创建数据库管理器
db = DatabaseManager()

# 连接数据库（自动创建数据库和表）
db.connect_sync()

# 执行查询
result = db.execute_sync_query("SELECT * FROM stock_index LIMIT 5")

# 断开连接
db.disconnect_sync()
```

### 在应用中使用

```python
from utils.db import DatabaseManager

class App:
    def __init__(self):
        self.db = DatabaseManager()
    
    def setup_database(self):
        """设置数据库"""
        self.db.connect_sync()  # 自动创建数据库
        self.db.create_tables() # 自动创建表
```

## Schema.json 格式说明

### 必需字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | 表名（必须与目录名一致） |
| `primaryKey` | string | 主键字段名 |
| `fields` | array | 字段定义数组 |

### 字段定义

```json
{
    "name": "字段名",
    "type": "字段类型",
    "length": "长度（可选）",
    "isRequired": "是否必填"
}
```

### 支持的字段类型

- `varchar` - 可变长度字符串
- `text` - 长文本
- `int` - 整数
- `bigint` - 大整数
- `tinyint` - 小整数
- `datetime` - 日期时间
- `date` - 日期
- `decimal` - 小数
- `json` - JSON数据

### 索引定义（可选）

```json
{
    "indexes": [
        {
            "name": "索引名",
            "columns": ["字段1", "字段2"],
            "type": "BTREE"
        }
    ]
}
```

## 配置说明

### 数据库配置

在 `config.py` 中配置数据库连接：

```python
DB_CONFIG = {
    'base': {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'stocks-py',
        'port': 3306,
        'charset': 'utf8mb4',
        'autocommit': True,
    }
}
```

### 表映射配置

```python
# 基础表映射
TABLES = {
    'stock_index': 'stock_index',
    'stock_kline': 'stock_kline_qfq',
    # ...
}

# 策略表映射
STRATEGY_TABLES = {
    'your_strategy_table': 'your_strategy_table',
    # ...
}
```

## 最佳实践

### 1. 命名规范
- 表名使用小写字母和下划线
- 目录名与表名保持一致
- 字段名使用小写字母和下划线

### 2. 字段设计
- 每个表必须有主键
- 使用 `isRequired` 标记必填字段
- 合理设置字段长度

### 3. 索引设计
- 为经常查询的字段创建索引
- 避免过多索引影响写入性能
- 使用有意义的索引名称

### 4. 数据迁移
- 修改现有表结构时注意数据兼容性
- 建议先备份数据
- 测试环境验证后再应用到生产环境

## 错误处理

### 常见错误

1. **目录名错误**
   ```
   Schema file not found: tables/base/wrong_name/schema.json
   ```
   解决：确保目录名与表名一致

2. **Schema格式错误**
   ```
   Failed to load schema for table_name
   ```
   解决：检查 schema.json 格式是否正确

3. **数据库连接失败**
   ```
   Failed to connect to database
   ```
   解决：检查数据库配置和网络连接

## 扩展功能

### 异步操作
```python
# 异步连接
await db.initialize_async()
result = await db.execute_async_query("SELECT * FROM table")
```

### 事务处理
```python
# 同步事务
with db.get_sync_cursor() as cursor:
    cursor.execute("INSERT INTO table1 VALUES (...)")
    cursor.execute("UPDATE table2 SET ...")
    # 自动提交或回滚
```

## 注意事项

1. **不要手动修改数据库结构** - 所有表结构变更都通过 schema.json 管理
2. **备份重要数据** - 在修改表结构前先备份数据
3. **测试环境验证** - 新表结构先在测试环境验证
4. **版本控制** - 将 schema.json 文件纳入版本控制
5. **文档更新** - 添加新表时更新相关文档

## 实际使用示例

### 创建策略表

1. **创建目录结构**
```bash
mkdir -p crawler/db/tables/strategy/my_strategy
```

2. **创建 schema.json**
```json
{
    "name": "my_strategy",
    "primaryKey": "id",
    "fields": [
        {
            "name": "id",
            "type": "int",
            "isRequired": true
        },
        {
            "name": "strategy_name",
            "type": "varchar",
            "length": 100,
            "isRequired": true
        },
        {
            "name": "signal",
            "type": "varchar",
            "length": 20,
            "isRequired": true
        },
        {
            "name": "created_at",
            "type": "datetime",
            "isRequired": true
        }
    ]
}
```

3. **更新配置**
```python
# 在 config.py 中添加
STRATEGY_TABLES = {
    'my_strategy': 'my_strategy'
}
```

4. **使用表**
```python
from utils.db import DatabaseManager
from datetime import datetime

db = DatabaseManager()
db.connect_sync()
db.create_tables()  # 自动创建新表

# 插入数据
db.execute_sync_query(
    "INSERT INTO my_strategy (id, strategy_name, signal, created_at) VALUES (%s, %s, %s, %s)",
    (1, "TestStrategy", "BUY", datetime.now())
)

# 查询数据
result = db.execute_sync_query("SELECT * FROM my_strategy")
print(result)

db.disconnect_sync()
```

## 联系支持

如有问题或建议，请查看：
- 代码注释
- 错误日志
- 数据库文档 