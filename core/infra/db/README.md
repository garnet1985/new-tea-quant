# Database 模块文档

## 📁 目录结构

```
app/core/infra/db/
├── db_manager.py              # 数据库管理器（核心）
├── db_schema_manager.py       # Schema 管理器
├── db_config_manager.py       # 数据库配置加载器
├── db_base_model.py           # DbBaseModel / DbModel（通用表操作工具）
├── adapters/                  # 数据库适配器
│   ├── base_adapter.py       # 适配器基类
│   ├── postgresql_adapter.py # PostgreSQL 适配器
│   ├── mysql_adapter.py      # MySQL 适配器
│   ├── sqlite_adapter.py     # SQLite 适配器
│   └── factory.py            # 适配器工厂
├── __init__.py                # 包导出
└── README.md                  # 本文档
```

---

## 🎯 核心组件

### 1. DatabaseManager（数据库管理器）

**职责**：
- 多数据库支持（PostgreSQL、MySQL、SQLite）
- 基础 CRUD 操作
- 事务管理
- 数据库初始化
- **默认实例机制（多进程安全）** ⭐

#### 核心特性

**✅ 默认实例机制（多进程安全）**

DatabaseManager 提供默认实例机制，支持多进程场景下的自动初始化：

```python
from app.core.infra.db.db_manager import DatabaseManager

# 主进程：初始化并设置为默认
db = DatabaseManager(is_verbose=True)
db.initialize()
DatabaseManager.set_default(db)

# 任何地方（包括子进程）
from app.core.modules.data_manager.base_tables import StockKlineModel

kline_model = StockKlineModel()  # ✅ 自动使用默认 db
# 如果在子进程中 context 丢失，会自动重新初始化
```

**API**：
- `DatabaseManager.set_default(instance)` - 设置默认实例
- `DatabaseManager.get_default()` - 获取默认实例（自动初始化）
- `DatabaseManager.reset_default()` - 重置默认实例（测试用）

**支持的数据库**：
- PostgreSQL（推荐，支持多进程并发读）
- MySQL/MariaDB
- SQLite（开发/测试环境）

#### 基础 CRUD 示例

```python
from app.core.infra.db.db_manager import DatabaseManager

# 初始化
db = DatabaseManager(is_verbose=True)
db.initialize()

# 查询
results = db.execute_sync_query("SELECT * FROM stock_list WHERE id = %s", ('000001.SZ',))

# 写入（使用队列，支持批量）
db.queue_write('stock_kline', kline_data_list, unique_keys=['id', 'date'])

# 事务
with db.transaction() as cursor:
    cursor.execute("INSERT INTO ...")
    cursor.execute("UPDATE ...")

# 删除
db.delete('stock_kline', 'date < %s', ['20200101'])

# 便捷查询
results = db.select('stock_list', fields='id, name', where='id LIKE %s', params=['000001%'], limit=10)

# 事务
with db.transaction() as cursor:
    cursor.execute("INSERT INTO ...")
    cursor.execute("UPDATE ...")
    # 自动提交或回滚

# 关闭
db.close()
```

#### 完整 API

**初始化与管理**：
- `initialize()` - 初始化数据库和连接池
- `close()` - 关闭连接池
- `get_stats()` - 获取连接池统计信息

**查询操作**：
- `execute_sync_query(sql, params)` - 执行查询
- `fetch_one(sql, params)` - 查询单条记录
- `fetch_all(sql, params)` - 查询多条记录
- `select(table, fields, where, params, order_by, limit, offset)` - 便捷查询

**写入操作**：
- `execute(sql, params)` - 执行 SQL（INSERT/UPDATE/DELETE）
- `insert(table, data)` - 插入单条记录
- `bulk_insert(table, data_list, ignore_duplicates)` - 批量插入
- `update(table, data, where, params)` - 更新记录
- `delete(table, where, params)` - 删除记录

**事务与连接**：
- `transaction()` - 事务上下文管理器
- `get_connection()` - 获取连接（上下文管理器）
- `get_sync_cursor()` - 获取游标（上下文管理器）

**兼容方法**：
- `queue_write(table, data_list, unique_keys, callback)` - 队列写入（兼容）
- `wait_for_writes(timeout)` - 等待写入完成（兼容）

**工具方法**：
- `is_table_exists(table_name)` - 检查表是否存在

---

### 2. DbBaseModel（表操作工具类）

**职责**：
- 单表 CRUD 封装
- 时序数据查询（`load_latest_records`、`load_latest_date`）
- 批量操作（`save_many`、`replace`）
- Upsert（插入或更新）
- **自动获取默认 db 实例** ⭐

**定位**：纯工具类，不涉及业务逻辑

**特点**：
- 🚀 性能优先（直接 SQL，无 ORM 开销）
- 🛡️ 安全（参数化查询，防 SQL 注入）
- 📊 时序数据优化
- 🔄 重试机制（应对高并发）
- 📦 批量操作优化

#### 核心方法

##### 查询操作

**`load()` - 通用查询**
```python
records = model.load(
    condition="id = %s AND date BETWEEN %s AND %s",
    params=('000001.SZ', '20200101', '20201231'),
    order_by="date ASC",
    limit=100
)
```

**`load_one()` - 查询单条**
```python
latest = model.load_one("id = %s", ('000001.SZ',), order_by="date DESC")
```

**`load_latest_date()` - 查询最新日期（时序数据）**
```python
latest_date = model.load_latest_date()  # 自动识别日期字段
```

**`load_latest_records()` - 查询最新记录（时序数据）⭐**
```python
# 查询每个股票的最新 K 线
latest_klines = kline_model.load_latest_records()
```

**`load_paginated()` - 分页查询**
```python
result = model.load_paginated(page=1, page_size=20, order_by="date DESC")
# 返回: {'data': [...], 'total': 1000, 'page': 1, 'page_size': 20, 'total_pages': 50}
```

##### 写入操作

**`save()` - 保存单条**
```python
model.save({'id': '000001.SZ', 'date': '20240101', 'close': 10.0})
```

**`save_many()` - 批量保存**
```python
model.save_many([
    {'id': '000001.SZ', 'date': '20240101', 'close': 10.0},
    {'id': '000001.SZ', 'date': '20240102', 'close': 10.5},
])
```

**`replace()` / `upsert()` - 插入或更新⭐**
```python
# 基于 (id, date) 判断是否存在，存在则更新，不存在则插入
model.replace(
    [{'id': '000001.SZ', 'date': '20240101', 'close': 10.0}],
    unique_keys=['id', 'date']
)
```

##### 删除操作

```python
# 删除指定条件的记录
deleted = model.delete("date < %s", ('20200101',))

# 删除单条
deleted = model.delete_one("id = %s AND date = %s", ('000001.SZ', '20240101'))

# 清空表
model.clear_table()
```

##### 统计操作

```python
# 统计数量
total = model.count()
count = model.count("close > %s", (10.0,))

# 检查是否存在
if model.exists("id = %s AND date = %s", ('000001.SZ', '20240101')):
    print("记录已存在")
```

#### 使用示例

**示例 1：直接使用（自动获取 db）**
```python
from app.core.infra.db.db_manager import DatabaseManager
from app.core.modules.data_manager.base_tables import StockKlineModel

# 主进程初始化一次
db = DatabaseManager(is_verbose=True)
db.initialize()
DatabaseManager.set_default(db)

# 任何地方直接使用（自动获取 db）
kline_model = StockKlineModel()  # ✅ 不需要传 db 参数
records = kline_model.load_by_stock_and_date_range(
    '000001.SZ', '20200101', '20201231'
)
```

**示例 2：继承使用（推荐）**
```python
# app/data_manager/base_tables/stock_kline/model.py
from typing import List, Dict, Any
from app.core.infra.db.db_base_model import DbBaseModel 

class StockKlineModel(DbBaseModel):
    """K线数据 Model"""
    
    def __init__(self, db=None):
        super().__init__('stock_kline', db)
    
    def load_by_stock_and_date_range(
        self, 
        stock_id: str, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """查询指定日期范围的 K 线"""
        return self.load(
            "id = %s AND date BETWEEN %s AND %s",
            (stock_id, start_date, end_date),
            order_by="date ASC"
        )
    
    def load_latest(self, stock_id: str) -> Dict[str, Any]:
        """查询最新 K 线"""
        return self.load_one("id = %s", (stock_id,), order_by="date DESC")

# 使用
kline_model = StockKlineModel()  # 自动获取 db
klines = kline_model.load_by_stock_and_date_range('000001.SZ', '20200101', '20201231')
```

**示例 3：时序数据查询**
```python
# 查询每个股票的最新 K 线
kline_model = StockKlineModel()
latest_klines = kline_model.load_latest_records()

# 查询最新日期
latest_date = kline_model.load_latest_date()
print(f"最新数据日期: {latest_date}")
```

---

### 3. SchemaManager（Schema 管理器）

**职责**：
- 加载 schema.json 文件
- 根据数据库类型生成对应的 CREATE TABLE SQL
- 创建表和索引
- 管理策略自定义表

**特性**：
- ✅ 自动适配不同数据库的 SQL 语法
- ✅ 支持 PostgreSQL、MySQL、SQLite
- ✅ 自动处理类型映射（AUTO_INCREMENT、BOOLEAN 等）

**使用示例**：
```python
from app.core.infra.db.db_schema_manager import DbSchemaManager

# 初始化（自动根据 DatabaseManager 的配置选择数据库类型）
schema_mgr = db.schema_manager

# 加载 schema
schema = schema_mgr.load_schema_from_file('path/to/schema.json')

# 生成 SQL（自动适配当前数据库类型）
create_sql = schema_mgr.generate_create_table_sql(schema)

# 创建表（需要数据库连接）
schema_mgr.create_table_with_indexes(schema, db.get_connection)

# 注册策略表
schema_mgr.register_table('my_strategy_table', schema)
```

**API**：
- `load_all_schemas()` - 加载所有 schema
- `load_schema_from_file(file)` - 从文件加载 schema
- `generate_create_table_sql(schema)` - 生成建表 SQL（自动适配数据库类型）
- `create_table_with_indexes(schema, db_connection_func)` - 创建表和索引
- `create_all_tables(get_connection_func)` - 创建所有表
- `is_table_exists(table, database, db_connection)` - 检查表是否存在

---

### 4. DBService（数据库工具类）

**职责**：提供 SQL 构建的静态工具方法

**位置**：`app/core/infra/db/db_base_model.py`（内部工具类）

**方法**：
- `to_columns_and_values(data_list)` - 转换为 INSERT 参数
- `to_upsert_params(data_list, unique_keys)` - 转换为 UPSERT 参数

**使用示例**：
```python
from app.core.infra.db.db_base_model import DBService

# INSERT 参数
columns, placeholders = DBService.to_columns_and_values([
    {'id': '001', 'name': 'test'}
])
# columns = ['id', 'name']
# placeholders = '%s, %s'

# UPSERT 参数
columns, values, update_clause = DBService.to_upsert_params(
    [{'id': '001', 'name': 'test', 'price': 10.0}],
    unique_keys=['id']
)
# update_clause = 'name = VALUES(name), price = VALUES(price)'
```

---

## 📊 Schema 定义

每个表在 `app/data_manager/base_tables/` 目录下都有一个 `schema.json` 文件：

```json
{
    "name": "stock_kline",
    "primaryKey": ["id", "term", "date"],
    "fields": [
        {
            "name": "id",
            "type": "varchar",
            "length": 16,
            "isRequired": true,
            "description": "股票代码"
        },
        {
            "name": "close",
            "type": "float",
            "isRequired": true,
            "description": "收盘价"
        }
    ],
    "indexes": [
        {
            "name": "idx_id_date",
            "fields": ["id", "date"],
            "unique": false
        }
    ]
}
```

**字段类型支持**：
- `varchar(length)` - 字符串
- `text` - 长文本
- `int` / `bigint` - 整数
- `float` / `double` - 浮点数
- `tinyint(1)` - 布尔值
- `datetime` - 日期时间
- `json` - JSON 数据

---

## 🔧 配置

### 数据库配置

配置文件位于：`config/database/db_config.json`（已 gitignore）

**新格式（推荐）**：
```json
{
    "database_type": "postgresql",
    "postgresql": {
        "host": "localhost",
        "port": 5432,
        "database": "stocks_py",
        "user": "postgres",
        "password": "your_password",
        "pool_size": 10
    },
    "batch_write": {
        "enable": true,
        "batch_size": 1000,
        "flush_interval": 5.0
    }
}
```

**支持的数据库类型**：
- `postgresql`: PostgreSQL（推荐，支持多进程并发读）
- `mysql`: MySQL/MariaDB
- `sqlite`: SQLite（开发/测试环境）

**旧格式（自动兼容）**：
```json
{
    "db_path": "data/stocks.db"  # 自动识别为 SQLite
}
```
或
```json
{
    "host": "localhost",
    "database": "stocks_py",
    "user": "root",
    "password": "password",
    "port": 3306  # 3306=MySQL, 5432=PostgreSQL
}
```

**示例文件**：`config/database/db_config.example.json`

---

## 🚀 技术特性

### 1. 多数据库支持
- ✅ PostgreSQL（连接池，支持多进程并发读）
- ✅ MySQL（连接池）
- ✅ SQLite（单连接，支持只读模式）
- ✅ 统一的适配器接口
- ✅ 自动 SQL 方言适配

### 2. 默认实例机制（多进程安全）⭐
- ✅ 主进程初始化，全局共享
- ✅ 子进程自动检测并重新初始化
- ✅ 测试场景支持覆盖
- ✅ 类似 SQLAlchemy 的 scoped_session

### 3. 事务支持
```python
with db.transaction() as cursor:
    cursor.execute("INSERT INTO ...")
    cursor.execute("UPDATE ...")
    # 自动提交，出错自动回滚
```

### 4. 批量操作
```python
# 批量插入（性能优化）
db.bulk_insert('stock_kline', data_list, ignore_duplicates=True)

# Upsert（大数据量自动优化）
model.replace(large_data_list, unique_keys=['id', 'date'])
```

### 5. Schema 自动建表
- 从 JSON 定义自动生成 SQL
- 支持主键、索引、字段约束
- 支持策略自定义表

---

## 🏗️ 架构建议

```
app/core/infra/db/                 ← 基础设施层（工具类）
├── db_manager.py                  # 连接池 + 基础 CRUD
├── db_base_model.py               # DbBaseModel / DbModel（通用工具）
├── db_schema_manager.py           # Schema 管理
└── db_config_manager.py           # 配置加载

app/data_manager/                  ← 业务层
├── base_tables/                   # Schema 定义（JSON）⭐
│   ├── stock_kline/
│   │   ├── schema.json
│   │   └── model.py               # StockKlineModel（继承 DbBaseModel
│   ├── gdp/
│   │   ├── schema.json
│   │   └── model.py
│   └── ...
├── repositories/                  # 跨表查询 ⭐
│   ├── stock_repository.py
│   └── ...
└── loaders/                       # 数据加载器（兼容层）
    ├── kline_loader.py
    └── ...
```

**职责划分**：
- `DatabaseManager`（utils/db）：连接池、基础 CRUD、默认实例
- `DbBaseModel`（utils/db）：通用工具，单表 CRUD
- 具体 Model（app/data_manager/base_tables/*/model.py）：业务封装，继承 DbBaseModel
- Repository（app/data_manager/repositories）：跨表查询
- Loader（app/data_manager/loaders）：数据加载封装

---

## 📚 最佳实践

### 1. 使用默认实例（推荐）
```python
# 主进程初始化一次
db = DatabaseManager(is_verbose=True)
db.initialize()
DatabaseManager.set_default(db)

# 任何地方直接使用
kline_model = StockKlineModel()  # ✅ 自动获取 db
```

### 2. 使用连接上下文管理器
```python
# 好的做法
with db.get_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute(...)

# 更好的做法（使用封装方法）
result = db.fetch_all(sql, params)
```

### 3. 使用参数化查询（防 SQL 注入）
```python
# ✅ 好
db.fetch_all("SELECT * FROM stock_list WHERE id = %s", ['000001.SZ'])

# ❌ 差
db.fetch_all(f"SELECT * FROM stock_list WHERE id = '{stock_id}'")
```

### 4. 批量操作优化性能
```python
# ✅ 好 - 批量插入
db.bulk_insert('stock_kline', kline_list)

# ❌ 差 - 循环插入
for kline in kline_list:
    db.insert('stock_kline', kline)
```

### 5. 使用事务保证一致性
```python
with db.transaction() as cursor:
    cursor.execute("UPDATE account SET balance = balance - 100 WHERE id = 1")
    cursor.execute("UPDATE account SET balance = balance + 100 WHERE id = 2")
```

### 6. 时序数据优化
```python
# 使用专用方法
latest_records = model.load_latest_records()  # 每个分组的最新记录
latest_date = model.load_latest_date()  # 最新日期
```

---

## 🔍 故障排查

### 连接池耗尽
```python
# 检查连接池状态
stats = db.get_stats()
print(stats)

# 增加最大连接数（修改配置文件）
{
    "pool": {
        "pool_size_max": 50
    }
}
```

### 表不存在
```python
# 检查表是否存在
if not db.is_table_exists('my_table'):
    # 创建表
    db.schema_manager.create_table_with_indexes(schema, db.get_connection)
```

### 查询超时
```python
# 增加超时时间（修改配置文件）
{
    "timeout": {
        "read": 120
    }
}
```

### 多进程场景
```python
# 无需特殊处理，DatabaseManager 会自动检测并重新初始化
# 日志会显示: "🔄 检测到 DatabaseManager 未初始化（可能是多进程场景），自动创建实例"
```

---

## 📖 相关文档

- [DataManager 文档](../../app/data_manager/README.md) - 数据管理器
- [Strategy 文档](../../app/analyzer/strategy/README.md) - 策略开发

---

## 🤝 贡献

如需修改数据库结构：
1. 修改对应的 `schema.json`（位于 `app/data_manager/base_tables/`）
2. 运行 `db.initialize()` 或让 `DataManager.initialize()` 自动创建/更新表
3. 更新相关 Model（如果需要添加业务方法）
4. 更新文档

---

## 📞 FAQ

**Q: DatabaseManager 和 DbBaseModel 的关系？**  
A: DatabaseManager 管理连接池和基础 DbBaseModel 基于 DatabaseManager DbBaseModel 自动获取 DatabaseManager 的默认实例。

**Q: 什么时候应该继承 DbBaseModel？**  
A: 当你需要为特定表添加业务方法时。例如 `StockKlineModel` 添加 `load_by_date_range()` 等方法。

**Q: 跨表查询怎么办？**  
A: 使用 Repository 模式。Repository 内部可以使用多个 Model，或直接使用 `db.execute_sync_query()` 执行复杂 SQL。

**Q: 多进程场景如何处理？**  
A: 无需特殊处理。在主进程中初始化并设置默认实例，子进程中 Model 会自动检测并重新初始化 DatabaseManager。

**Q: DbBaseModel 和 ORM 的区别？**  
A: DbBaseModel 是轻量级的数据访问层，不是完整的 ORM。优势是性能更好、更灵活，但没有关系映射、类型安全等 ORM 特性。

**Q: 如何添加类型提示？**  
A: 使用 `TypedDict` 定义返回类型：
```python
from typing import TypedDict, List

class KlineData(TypedDict):
    id: str
    date: str
    open: float
    close: float

class StockKlineModel(DbBaseModel):
    def load_by_stock(self, stock_id: str) -> List[KlineData]:
        return super().load("id = %s", (stock_id,))
```

---

## 📅 更新日志

### 2025-01-15

**✅ 多数据库支持**：
- 实现数据库适配器抽象层（PostgreSQL、MySQL、SQLite）
- 重构 DatabaseManager 使用适配器模式
- Schema 管理器支持多数据库类型自动适配
- 移除 DuckDB 支持（解决多进程并发读问题）

**✅ 适配器架构**：
- `BaseDatabaseAdapter` - 适配器基类
- `PostgreSQLAdapter` - PostgreSQL 适配器（连接池）
- `MySQLAdapter` - MySQL 适配器
- `SQLiteAdapter` - SQLite 适配器（支持只读模式）
- `DatabaseAdapterFactory` - 适配器工厂

**✅ Schema 管理器增强**：
- 根据数据库类型自动生成对应的 SQL
- 支持 AUTO_INCREMENT 类型映射（SERIAL/AUTO_INCREMENT/AUTOINCREMENT）
- 支持 COMMENT（PostgreSQL/MySQL）
- 支持不同数据库的标识符引用（双引号/反引号）

### 2024-12-04

**✅ 重大重构**：
- 重构 DatabaseManager（使用适配器模式）
- 新增 SchemaManager（独立 schema 管理）
- 配置外部化到 `config/database/db_config.json`

**✅ 默认实例机制**：
- DatabaseManager 支持默认实例（`set_default`/`get_default`）
- DbBaseModel 自动获取默认 db 实例（`db` 参数可选）
- 多进程安全（自动检测并重新初始化）

**✅ 工具类补充**：
- 添加 DBService（纯静态工具类）
- 补充 `get_sync_cursor()`、`execute_sync_query()`
- 补充兼容方法 `queue_write()`、`wait_for_writes()`

**✅ 架构优化**：
- DbBaseModel 保留在 `app/core/infra/db/`（通用工具类定位）
- 具体 Model 放在 `app/core/modules/data_manager/base_tables/*/model.py`
- 跨表查询使用 Repository 模式

---

## 🎉 总结

`app/core/infra/db` 模块提供了完整的数据库基础设施：

- 🔌 **DatabaseManager**：多数据库支持、CRUD、事务、默认实例
- 🔧 **适配器系统**：PostgreSQL、MySQL、SQLite 适配器
- 📦 **DbBaseModel**：单表操作、时序数据优化、自动获取 db
- 🗂️ **SchemaManager**：Schema 加载、多数据库 SQL 生成、建表
- 🛠️ **DBService**：SQL 构建工具

**核心优势**：
- ✅ 多数据库支持（PostgreSQL、MySQL、SQLite）
- ✅ 性能优先（连接池 + 直接 SQL）
- ✅ 多进程安全（默认实例 + 自动初始化）
- ✅ 使用简单（90% 场景不需要传 db）
- ✅ 灵活扩展（支持继承和覆盖）
- ✅ 类型安全（参数化查询 + TypedDict）
- ✅ 自动 SQL 适配（根据数据库类型生成对应的 SQL）

开始使用：
```python
# 1. 初始化（主进程）
from app.core.infra.db import DatabaseManager

db = DatabaseManager(is_verbose=True)
db.initialize()
DatabaseManager.set_default(db)

# 2. 使用 Model（任何地方）
from app.core.modules.data_manager.base_tables import StockKlineModel

kline_model = StockKlineModel()  # ✅ 自动获取 db
klines = kline_model.load_by_stock_and_date_range('000001.SZ', '20200101', '20201231')
```
