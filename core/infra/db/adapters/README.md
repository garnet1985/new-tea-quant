# 数据库适配器架构说明

## 🎯 适配器的目的

**是的，适配器就是为了抹平各种数据库之间的差异！**

适配器模式（Adapter Pattern）的核心思想是：
- **统一接口**：为不同的数据库提供相同的操作接口
- **隐藏差异**：业务代码不需要关心底层是 PostgreSQL 还是 DuckDB
- **易于切换**：只需修改配置，无需修改业务代码

## 📊 工作流程

### 1. 初始化阶段

```
用户代码
  ↓
DatabaseManager.__init__(config)
  ↓
DatabaseManager.initialize()
  ↓
DatabaseAdapterFactory.create(config)
  ↓
根据 config['database_type'] 创建对应适配器：
  - 'postgresql' → PostgreSQLAdapter
  - 'duckdb' → DuckDBAdapter
  ↓
适配器.connect() → 建立数据库连接
  ↓
DatabaseManager.adapter = 适配器实例
```

**示例代码：**
```python
# 配置
config = {
    'database_type': 'postgresql',  # 或 'duckdb'
    'postgresql': {
        'host': 'localhost',
        'port': 5432,
        'database': 'stocks_py',
        'user': 'postgres',
        'password': 'xxx'
    }
}

# 初始化
db = DatabaseManager(config)
db.initialize()  # 内部会创建适配器并连接
```

### 2. 查询执行流程

```
用户代码：db.execute_sync_query("SELECT * FROM stock_kline WHERE id = %s", ('000001.SZ',))
  ↓
DatabaseManager.execute_sync_query(query, params)
  ↓
self.adapter.execute_query(query, params)
  ↓
【适配器内部处理差异】
  ↓
PostgreSQLAdapter:
  - 占位符：%s → %s（不变）
  - 使用连接池获取连接
  - 使用 RealDictCursor 返回字典
  - 归还连接到连接池
  
DuckDBAdapter:
  - 占位符：%s → ?（转换）
  - 使用单连接执行
  - 手动转换结果为字典
  ↓
返回统一格式：List[Dict[str, Any]]
```

**示例代码：**
```python
# 业务代码完全一样，不管底层是什么数据库
results = db.execute_sync_query(
    "SELECT * FROM stock_kline WHERE id = %s",
    ('000001.SZ',)
)
# results = [{'id': '000001.SZ', 'date': '2024-01-01', ...}, ...]
```

### 3. 写入执行流程

```
用户代码：db.queue_write('stock_kline', data_list, unique_keys=['id', 'date'])
  ↓
DatabaseManager.queue_write()
  ↓
DatabaseManager._direct_write()
  ↓
构建 SQL：INSERT ... ON CONFLICT ...
  ↓
self.adapter.execute_batch(sql, values)
  ↓
【适配器内部处理差异】
  ↓
PostgreSQLAdapter:
  - 使用 psycopg2.extras.execute_batch
  - 自动提交事务
  
DuckDBAdapter:
  - 循环执行每条 SQL
  - 自动提交（DuckDB 特性）
  ↓
返回影响行数
```

## 🔄 如何抹平差异

### 差异 1：占位符不同

**问题：**
- PostgreSQL/MySQL 使用 `%s`
- DuckDB/SQLite 使用 `?`

**解决方案：**
```python
# BaseDatabaseAdapter
def normalize_query(self, query: str) -> str:
    placeholder = self.get_placeholder()
    if placeholder == '?':
        return query.replace("%s", "?")  # DuckDB
    else:
        return query  # PostgreSQL

# 业务代码统一使用 %s
query = "SELECT * FROM table WHERE id = %s"
# 适配器内部自动转换
```

### 差异 2：结果格式不同

**问题：**
- PostgreSQL 返回 `RealDictRow`（类似字典）
- DuckDB 返回元组或字典（不一致）

**解决方案：**
```python
# PostgreSQLAdapter
def execute_query(self, query, params):
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, params)
        results = cursor.fetchall()
        return [dict(row) for row in results]  # 统一转换为字典

# DuckDBAdapter
def execute_query(self, query, params):
    query = query.replace("%s", "?")  # 转换占位符
    cursor = self.conn.execute(query, params)
    result = cursor.fetchall()
    # 统一转换为字典列表
    if isinstance(result[0], dict):
        return list(result)
    else:
        # 元组转字典
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in result]
```

### 差异 3：连接管理不同

**问题：**
- PostgreSQL 需要连接池（多进程场景）
- DuckDB 单连接即可（文件数据库）

**解决方案：**
```python
# PostgreSQLAdapter
def __init__(self, config):
    self._connection_pool = pool.ThreadedConnectionPool(...)

def _get_connection(self):
    return self._connection_pool.getconn()  # 从池中获取

def _put_connection(self, conn):
    self._connection_pool.putconn(conn)  # 归还到池

# DuckDBAdapter
def __init__(self, config):
    self.conn = duckdb.connect(db_path)  # 单连接

def get_connection(self):
    return self.conn  # 直接返回，无需池管理
```

### 差异 4：事务处理不同

**问题：**
- PostgreSQL 需要显式 commit/rollback
- DuckDB 自动提交

**解决方案：**
```python
# BaseDatabaseAdapter 统一接口
@contextmanager
def transaction(self):
    # 子类实现具体逻辑
    pass

# PostgreSQLAdapter
@contextmanager
def transaction(self):
    conn = self._get_connection()
    try:
        with conn.cursor() as cursor:
            yield cursor
            conn.commit()  # 显式提交
    except:
        conn.rollback()  # 显式回滚
        raise
    finally:
        self._put_connection(conn)

# DuckDBAdapter
@contextmanager
def transaction(self):
    cursor = DuckDBCursor(self.conn)
    yield cursor
    # DuckDB 自动提交，无需显式操作
```

## 📝 完整示例

### 示例 1：切换数据库（无需修改业务代码）

```python
# 使用 PostgreSQL
config_pg = {
    'database_type': 'postgresql',
    'postgresql': {'host': 'localhost', ...}
}
db_pg = DatabaseManager(config_pg)
db_pg.initialize()

# 使用 DuckDB
config_duckdb = {
    'database_type': 'duckdb',
    'duckdb': {'db_path': 'data/stocks.duckdb'}
}
db_duckdb = DatabaseManager(config_duckdb)
db_duckdb.initialize()

# 业务代码完全一样！
results = db_pg.execute_sync_query("SELECT * FROM stock_kline WHERE id = %s", ('000001.SZ',))
results = db_duckdb.execute_sync_query("SELECT * FROM stock_kline WHERE id = %s", ('000001.SZ',))
```

### 示例 2：适配器自动处理差异

```python
# 业务代码（统一接口）
query = "SELECT * FROM stock_kline WHERE id = %s AND date = %s"
params = ('000001.SZ', '2024-01-01')

# PostgreSQL 适配器内部：
# 1. query 保持不变（已经是 %s）
# 2. 使用连接池获取连接
# 3. 使用 RealDictCursor 执行
# 4. 转换为字典列表返回

# DuckDB 适配器内部：
# 1. query: "%s" → "?"（自动转换）
# 2. 使用单连接执行
# 3. 手动转换为字典列表返回

# 两种适配器返回相同格式：
# [{'id': '000001.SZ', 'date': '2024-01-01', ...}]
```

## 🎨 架构图

```
┌─────────────────────────────────────────────────┐
│           业务代码（DataManager, Models）        │
│  统一使用 DatabaseManager API                   │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│          DatabaseManager                        │
│  - execute_sync_query()                         │
│  - queue_write()                                │
│  - transaction()                                │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│      BaseDatabaseAdapter (抽象接口)              │
│  - execute_query()                              │
│  - execute_write()                              │
│  - transaction()                                │
└──────────┬───────────────────────┬───────────────┘
           │                       │
           ▼                       ▼
┌──────────────────┐    ┌──────────────────────┐
│ PostgreSQLAdapter│    │   DuckDBAdapter      │
│                  │    │                      │
│ - 连接池管理      │    │ - 单连接管理          │
│ - %s 占位符      │    │ - ? 占位符           │
│ - RealDictCursor │    │ - 手动转换结果        │
│ - 显式事务       │    │ - 自动提交           │
└──────────────────┘    └──────────────────────┘
           │                       │
           ▼                       ▼
    ┌──────────┐            ┌──────────┐
    │PostgreSQL│            │  DuckDB   │
    └──────────┘            └──────────┘
```

## ✅ 优势

1. **业务代码无需修改**：切换数据库只需改配置
2. **统一错误处理**：适配器统一处理异常
3. **易于测试**：可以轻松 mock 适配器
4. **易于扩展**：新增数据库只需实现适配器接口
5. **向后兼容**：保留 DuckDB 支持，平滑迁移

## 🔍 关键设计点

1. **占位符统一**：业务代码统一使用 `%s`，适配器内部转换
2. **结果格式统一**：所有适配器返回 `List[Dict[str, Any]]`
3. **连接管理封装**：业务代码不关心连接池还是单连接
4. **事务接口统一**：使用上下文管理器，自动提交/回滚
