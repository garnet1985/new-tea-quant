# Database 模块文档

## 📁 目录结构

```
utils/db/
├── db_manager.py           # 数据库管理器（核心）
├── schema_manager.py       # Schema 管理器
├── db_config.py           # 数据库配置
├── db_model.py            # BaseTableModel（通用工具类）
├── BASE_TABLE_MODEL_GUIDE.md  # BaseTableModel 使用指南
│   ├── stock_kline/       # K线表
│   ├── stock_list/        # 股票列表
│   ├── gdp/              # GDP数据
│   └── ...               # 其他表
├── README.md             # 本文档
└── REFACTOR_SUMMARY.md   # 重构总结
```

## 🎯 核心组件

### DatabaseManager（数据库管理器）

**职责**：
- 连接池管理（使用 DBUtils）
- 基础 CRUD 操作
- 事务管理
- 数据库初始化

### BaseTableModel（表操作工具类）

**职责**：
- 单表 CRUD 封装
- 时序数据查询（`load_latest_records`、`load_latest_date`）
- 批量操作（`save_many`、`replace`）
- Upsert（插入或更新）

**详细文档**：[BaseTableModel 使用指南](./BASE_TABLE_MODEL_GUIDE.md)

**使用示例**：
```python
from utils.db.db_manager import DatabaseManager

# 初始化
db = DatabaseManager(is_verbose=True)
db.initialize()

# 查询
result = db.fetch_one("SELECT * FROM stock_list WHERE id = %s", ['000001.SZ'])
results = db.fetch_all("SELECT * FROM stock_kline WHERE id = %s", ['000001.SZ'])

# 插入
db.insert('stock_list', {'id': '000001.SZ', 'name': '平安银行'})

# 批量插入
db.bulk_insert('stock_kline', kline_data_list, ignore_duplicates=True)

# 更新
db.update('stock_list', {'name': '新名称'}, 'id = %s', ['000001.SZ'])

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

**API 参考**：
- `initialize()` - 初始化数据库和连接池
- `execute(sql, params)` - 执行 SQL（INSERT/UPDATE/DELETE）
- `fetch_one(sql, params)` - 查询单条记录
- `fetch_all(sql, params)` - 查询多条记录
- `insert(table, data)` - 插入单条记录
- `bulk_insert(table, data_list, ignore_duplicates)` - 批量插入
- `update(table, data, where, params)` - 更新记录
- `delete(table, where, params)` - 删除记录
- `select(table, fields, where, params, order_by, limit)` - 便捷查询
- `transaction()` - 事务上下文管理器
- `get_connection()` - 获取连接（上下文管理器）
- `is_table_exists(table_name)` - 检查表是否存在
- `close()` - 关闭连接池

### SchemaManager（Schema 管理器）

**职责**：
- 加载 schema.json 文件
- 生成 CREATE TABLE SQL
- 创建表和索引
- 管理策略自定义表

**使用示例**：
```python
from utils.db.schema_manager import SchemaManager

# 初始化
schema_mgr = SchemaManager(is_verbose=True)

# 加载 schema
schema = schema_mgr.load_schema_from_file('path/to/schema.json')

# 生成 SQL
create_sql = schema_mgr.generate_create_table_sql(schema)

# 创建表（需要数据库连接）
schema_mgr.create_table_with_indexes(schema, db.get_connection)

# 注册策略表
schema_mgr.register_table('my_strategy_table', schema)

# 获取表信息
fields = schema_mgr.get_table_fields('stock_kline')
```

**API 参考**：
- `load_all_schemas()` - 加载所有 schema
- `load_schema_from_file(file)` - 从文件加载 schema
- `generate_create_table_sql(schema)` - 生成建表 SQL
- `generate_create_index_sql(table, index)` - 生成索引 SQL
- `create_table(schema, db_connection)` - 创建表
- `create_indexes(table, indexes, db_connection)` - 创建索引
- `create_table_with_indexes(schema, db_connection_func)` - 创建表和索引
- `create_all_tables(get_connection_func)` - 创建所有表
- `register_table(name, schema)` - 注册自定义表
- `create_registered_tables(get_connection_func)` - 创建注册的表
- `is_table_exists(table, database, db_connection)` - 检查表是否存在
- `get_table_schema(table)` - 获取表 schema
- `get_table_fields(table)` - 获取表字段列表

## 📊 Schema 定义

每个表在 `tables/` 目录下都有一个 `schema.json` 文件：

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

## 🔧 配置

### 数据库配置（db_config.py）

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
    },
    'pool': {
        'pool_size_min': 5,      # 最小连接数
        'pool_size_max': 30,     # 最大连接数
    },
    'timeout': {
        'connection': 60,
        'read': 60,
        'write': 60,
    }
}
```

**环境变量支持**：
- `DB_HOST` - 数据库主机
- `DB_USER` - 数据库用户
- `DB_PASSWORD` - 数据库密码
- `DB_NAME` - 数据库名称
- `DB_PORT` - 数据库端口

## ⚠️ 废弃组件

以下组件已废弃或计划废弃：

### 已删除（2024-12-04）
- ❌ `connection_pool.py` - 已被 DBUtils 替代
- ❌ `db_service.py` - 功能已迁移到 SchemaManager
- ❌ `process_safe_db_manager.py` - 功能已整合到 DatabaseManager

### 计划废弃
- ⚠️ `db_model.py` - BaseTableModel 将迁移到 DataLoader
- ⚠️ `tables/*/model.py` - 表模型将迁移到各 Loader

**迁移指南**：
```python
# 旧代码（不推荐）
from utils.db.db_model import BaseTableModel
model = BaseTableModel('stock_kline', db)
records = model.load(condition="id = %s", params=('000001.SZ',))

# 新代码（推荐）
from app.data_loader import DataLoader
loader = DataLoader(db)
records = loader.kline_loader.load_kline('000001.SZ', '20200101', '20241231')
```

## 🚀 技术特性

### 连接池（DBUtils）
- ✅ 自动扩容（5-30 个连接）
- ✅ 自动健康检查（ping）
- ✅ 线程安全
- ✅ 连接复用
- ✅ 阻塞等待（连接用完时）

### 事务支持
```python
with db.transaction() as cursor:
    cursor.execute("INSERT INTO ...")
    cursor.execute("UPDATE ...")
    # 自动提交，出错自动回滚
```

### 批量操作
```python
# 批量插入（性能优化）
db.bulk_insert('stock_kline', data_list, ignore_duplicates=True)
```

### Schema 自动建表
- 从 JSON 定义自动生成 SQL
- 支持主键、索引、字段约束
- 支持策略自定义表

## 📚 最佳实践

### 1. 使用连接上下文管理器
```python
# 好的做法
with db.get_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute(...)

# 更好的做法（使用封装方法）
result = db.fetch_all(sql, params)
```

### 2. 使用参数化查询（防 SQL 注入）
```python
# ✅ 好
db.fetch_all("SELECT * FROM stock_list WHERE id = %s", ['000001.SZ'])

# ❌ 差
db.fetch_all(f"SELECT * FROM stock_list WHERE id = '{stock_id}'")
```

### 3. 批量操作优化性能
```python
# ✅ 好 - 批量插入
db.bulk_insert('stock_kline', kline_list)

# ❌ 差 - 循环插入
for kline in kline_list:
    db.insert('stock_kline', kline)
```

### 4. 使用事务保证一致性
```python
with db.transaction() as cursor:
    cursor.execute("UPDATE account SET balance = balance - 100 WHERE id = 1")
    cursor.execute("UPDATE account SET balance = balance + 100 WHERE id = 2")
```

## 🔍 故障排查

### 连接池耗尽
```python
# 检查连接池状态
stats = db.get_stats()
print(stats)

# 增加最大连接数
DB_CONFIG['pool']['pool_size_max'] = 50
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
# 增加超时时间
DB_CONFIG['timeout']['read'] = 120
```

## 📖 相关文档

- [REFACTOR_SUMMARY.md](./REFACTOR_SUMMARY.md) - 重构总结
- [DataLoader 文档](../../app/data_loader/README.md) - 数据加载器
- [Strategy 文档](../../app/analyzer/strategy/README.md) - 策略开发

## 🤝 贡献

如需修改数据库结构：
1. 修改对应的 `schema.json`
2. 运行 `db.initialize()` 自动创建/更新表
3. 更新相关文档

## 📅 更新日志

- **2024-12-04**: 
  - ✅ 重构 DatabaseManager（使用 DBUtils）
  - ✅ 新增 SchemaManager
  - ✅ 删除冗余文件（connection_pool, db_service, process_safe_db_manager）
  - ⚠️ 标记 db_model.py 为废弃
