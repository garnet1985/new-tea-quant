# Database 模块

数据库基础设施层，提供统一的数据库访问接口，支持 PostgreSQL、MySQL 和 SQLite。

## 📁 模块结构

```
core/infra/db/
├── db_manager.py                  # 数据库管理器（入口）
│
├── connection_management/         # 连接管理
│   └── connection_manager.py      # ConnectionManager
│
├── schema_management/             # Schema 管理
│   ├── schema_manager.py          # SchemaManager
│   ├── db_schema_manager.py       # DbSchemaManager
│   └── field/                     # Field 类型定义
│       ├── __init__.py
│       ├── base.py                # Field
│       ├── string.py              # StringField, CharField, TextField
│       ├── numeric.py             # IntField, BigIntField, FloatField, etc.
│       ├── datetime.py            # DateField, DateTimeField, TimestampField
│       ├── boolean.py             # BooleanField
│       ├── json.py                # JsonField
│       ├── uuid.py                # UuidField
│       ├── blob.py                # BlobField
│       └── enum.py                # EnumField
│
├── table_management/              # 表管理
│   └── table_manager.py           # TableManager
│
├── table_queryers/                # 表查询器
│   ├── db_base_model.py          # DbBaseModel（表查询基类）
│   ├── query_helpers.py          # TimeSeriesHelper, DataFrameHelper, SchemaFormatter
│   ├── adapters/                  # 数据库适配器
│   │   ├── base_adapter.py        # BaseDatabaseAdapter
│   │   ├── factory.py              # DatabaseAdapterFactory
│   │   ├── postgresql_adapter.py  # PostgreSQLAdapter
│   │   ├── mysql_adapter.py       # MySQLAdapter
│   │   └── sqlite_adapter.py     # SQLiteAdapter
│   └── services/                   # 表查询服务
│       ├── batch_operation.py     # BatchOperation
│       └── batch_operation_queue.py # BatchWriteQueue, WriteRequest
│
├── helpers/                        # 辅助工具（静态类或纯业务无关）
│   ├── db_helpers.py              # DBHelper, DatabaseCursor
│
├── __init__.py                    # 包导出
├── README.md                      # 本文档
└── DESIGN.md                      # 设计文档
```

## 🎯 核心概念

### DatabaseManager（数据库管理器）

数据库连接和操作的核心入口，负责：
- 数据库连接管理（通过 ConnectionManager）
- Schema 管理（通过 SchemaManager）
- 表操作 API（通过 TableManager）
- 默认实例机制（多进程安全）

**基本使用**：

```python
from core.infra.db import DatabaseManager

# 初始化
db = DatabaseManager(is_verbose=True)
db.initialize()
DatabaseManager.set_default(db)

# 查询
results = db.execute_sync_query(
    "SELECT * FROM stock_list WHERE id = %s", 
    ('000001.SZ',)
)

# 写入（使用队列，支持批量）
db.queue_write(
    'stock_kline', 
    kline_data_list, 
    unique_keys=['id', 'date']
)

# 事务
with db.transaction() as cursor:
    cursor.execute("INSERT INTO ...")
    cursor.execute("UPDATE ...")
```

**默认实例机制**：

支持多进程场景下的自动初始化，子进程会自动创建只读实例：

```python
# 主进程：初始化并设置为默认
db = DatabaseManager(is_verbose=True)
db.initialize()
DatabaseManager.set_default(db)

# 任何地方（包括子进程）
from core.modules.data_manager.base_tables import StockKlineModel

kline_model = StockKlineModel()  # 自动使用默认 db
```

### DbBaseModel（表操作基类）

所有基础表的 Model 类都继承自此类，提供单表的 CRUD 操作。

**基本使用**：

```python
from core.infra.db import DbBaseModel

# 方式 1: 直接使用
model = DbBaseModel('stock_kline', db)
records = model.load("id = %s", ('000001.SZ',))

# 方式 2: 继承使用（推荐）
class StockKlineModel(DbBaseModel):
    def __init__(self, db=None):
        super().__init__('stock_kline', db)
    
    def load_by_date_range(self, stock_id, start_date, end_date):
        return self.load(
            "id = %s AND date BETWEEN %s AND %s",
            (stock_id, start_date, end_date),
            order_by="date ASC"
        )
```

**核心方法**：

- **查询**：`load()`, `load_one()`, `load_all()`, `load_many()`, `load_paginated()`
- **写入**：`insert()`, `replace()`, `batch_insert()`, `batch_replace()`
- **删除**：`delete()`
- **表管理**：`create_table()`, `drop_table()`, `clear_table()`, `describe()`

### 三层架构

DatabaseManager 内部使用三层架构：

1. **ConnectionManager** - 连接和事务管理
2. **SchemaManager** - Schema 管理和表初始化
3. **TableManager** - 表操作 API

### 适配器系统

通过适配器模式支持多种数据库，业务代码无需关心底层数据库类型。

**支持的数据库**：
- PostgreSQL（推荐，支持多进程并发读）
- MySQL/MariaDB
- SQLite（开发/测试环境）

**配置示例**：

```json
{
  "database_type": "postgresql",
  "postgresql": {
    "host": "localhost",
    "port": 5432,
    "database": "stocks_py",
    "user": "postgres",
    "password": "password"
  },
  "batch_write": {
    "enable": true,
    "batch_size": 1000,
    "flush_interval": 5.0
  }
}
```

### Schema 管理器

负责表结构的管理：
- 从 JSON Schema 文件加载表定义
- 根据数据库类型生成对应的 SQL
- 创建表和索引

### 批量写入队列

解决数据库并发写入问题：
- 收集多线程的写入请求
- 达到阈值后批量写入
- 单线程执行写入，避免锁冲突

## 🚀 快速开始

### 1. 初始化数据库

```python
from core.infra.db import DatabaseManager

db = DatabaseManager(is_verbose=True)
db.initialize()
DatabaseManager.set_default(db)
```

### 2. 使用 Model

```python
from core.modules.data_manager.base_tables import StockKlineModel

kline_model = StockKlineModel()  # 自动获取默认 db
klines = kline_model.load_by_stock_and_date_range(
    '000001.SZ', 
    '20200101', 
    '20201231'
)
```

### 3. 直接使用 DatabaseManager

```python
# 查询
results = db.execute_sync_query(
    "SELECT * FROM stock_list WHERE id = %s",
    ('000001.SZ',)
)

# 写入
db.queue_write(
    'stock_kline',
    data_list,
    unique_keys=['id', 'date']
)
```

## 📝 最佳实践

### 1. 使用默认实例（推荐）

主进程初始化一次，任何地方直接使用：

```python
# 主进程
db = DatabaseManager(is_verbose=True)
db.initialize()
DatabaseManager.set_default(db)

# 任何地方
kline_model = StockKlineModel()  # 自动获取 db
```

### 2. 使用参数化查询（防 SQL 注入）

```python
# ✅ 正确
db.execute_sync_query(
    "SELECT * FROM stock_list WHERE id = %s",
    ['000001.SZ']
)

# ❌ 错误
db.execute_sync_query(
    f"SELECT * FROM stock_list WHERE id = '{stock_id}'"
)
```

### 3. 批量操作优化性能

```python
# ✅ 推荐：批量插入
db.queue_write('stock_kline', kline_list, unique_keys=['id', 'date'])

# ❌ 不推荐：循环插入
for kline in kline_list:
    db.insert('stock_kline', kline)
```

### 4. 使用事务保证一致性

```python
with db.transaction() as cursor:
    cursor.execute("UPDATE account SET balance = balance - 100 WHERE id = 1")
    cursor.execute("UPDATE account SET balance = balance + 100 WHERE id = 2")
    # 自动提交，出错自动回滚
```

## 🔧 配置

数据库配置通过 `ConfigManager.load_database_config()` 加载，支持：
- 默认配置：`core/default_config/database/{database_type}.json`
- 用户配置：`userspace/config/database/{database_type}.json`
- 环境变量覆盖（最高优先级）

配置必须包含：
- `database_type`: 数据库类型（postgresql, mysql, sqlite）
- `{database_type}`: 对应的数据库配置
- `batch_write`: 批量写入配置（可选，有默认值）

详细配置说明请参考 `core/default_config/database/README.md`。

## 📚 更多信息

- **设计文档**：查看 `DESIGN.md` 了解设计思路和架构背景
- **适配器系统**：查看 `table_queryers/adapters/` 目录了解适配器实现
- **Schema 管理**：查看 `schema_management/` 目录了解表结构管理
