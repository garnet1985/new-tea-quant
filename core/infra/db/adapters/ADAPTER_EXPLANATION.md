# 适配器工作原理详解

## 你的理解基本正确，但有几个细节需要澄清

### ✅ 正确的理解

1. **是的，所有数据库操作都必须通过适配器统一接口**
   - `execute_sync_query()` → `adapter.execute_query()`
   - `queue_write()` → `adapter.execute_batch()`
   - `transaction()` → `adapter.transaction()`

2. **是的，适配器在"执行层面"做适配**
   - 不是"翻译SQL语句"（SQL本身是标准的）
   - 而是在"如何执行SQL"上做适配

### ❌ 需要澄清的理解

1. **不是"hack"，是标准的适配器模式设计**
   - 这是经典的设计模式，不是临时方案

2. **不是"翻译SQL语句"，而是在"执行层面"适配**
   - SQL语句本身基本不需要翻译（都是标准SQL）
   - 主要适配的是：连接管理、占位符、结果格式、事务处理

## 🔍 实际工作流程（代码追踪）

### 示例：执行一个查询

```python
# 1. 业务代码调用
results = db.execute_sync_query(
    "SELECT * FROM stock_kline WHERE id = %s",
    ('000001.SZ',)
)
```

**代码追踪：**

```python
# 2. DatabaseManager.execute_sync_query() (db_manager.py:432)
def execute_sync_query(self, query: str, params: Any = None):
    # 直接委托给适配器，不做任何处理
    return self.adapter.execute_query(query, params)
    #      ↑
    #      这里 self.adapter 可能是 PostgreSQLAdapter 或 DuckDBAdapter
```

```python
# 3a. 如果是 PostgreSQLAdapter (postgresql_adapter.py:106)
def execute_query(self, query: str, params: Any = None):
    # SQL 语句不变（已经是 %s）
    # 主要处理：
    conn = self._get_connection()  # 从连接池获取连接
    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, params)  # 执行SQL（query 不变）
        results = cursor.fetchall()
        return [dict(row) for row in results]  # 转换为字典列表
    # 最后归还连接到连接池
```

```python
# 3b. 如果是 DuckDBAdapter (duckdb_adapter.py:178)
def execute_query(self, query: str, params: Any = None):
    # 唯一需要"翻译"的地方：占位符转换
    query = query.replace("%s", "?")  # %s -> ?
    
    # 执行SQL
    cursor = self.conn.execute(query, params)
    result = cursor.fetchall()
    
    # 结果格式转换（DuckDB可能返回元组，需要转字典）
    if isinstance(result[0], dict):
        return list(result)
    else:
        # 元组转字典
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in result]
```

## 📊 关键点总结

### 1. SQL语句本身不需要翻译

```python
# 业务代码写的SQL（标准SQL）
query = "SELECT * FROM stock_kline WHERE id = %s AND date = %s"

# PostgreSQL适配器：直接使用（%s 已经是正确的）
cursor.execute(query, params)  # query 不变

# DuckDB适配器：只转换占位符
query = query.replace("%s", "?")  # 只改占位符，SQL逻辑不变
cursor.execute(query, params)
```

**为什么SQL不需要翻译？**
- PostgreSQL 和 DuckDB 都支持标准SQL
- `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `WHERE`, `JOIN` 等语法都相同
- 只有占位符不同（`%s` vs `?`）

### 2. 适配器主要适配的是"执行方式"

| 差异点 | PostgreSQL | DuckDB | 适配方式 |
|--------|-----------|--------|----------|
| **占位符** | `%s` | `?` | 适配器内部转换 |
| **连接管理** | 连接池 | 单连接 | 适配器封装 |
| **结果格式** | RealDictRow | 元组/字典 | 统一转换为字典 |
| **事务处理** | 显式commit | 自动提交 | 统一接口 |
| **批量写入** | execute_batch | 循环执行 | 统一接口 |

### 3. 所有操作都通过适配器

```python
# ✅ 正确：通过适配器
results = db.execute_sync_query("SELECT ...", params)
db.queue_write(table, data, keys)

# ❌ 错误：直接访问底层连接（不应该这样做）
# conn = db.adapter.get_connection()  # 不应该直接访问
# conn.execute("SELECT ...")  # 绕过了适配器
```

## 🎯 设计模式：适配器模式（Adapter Pattern）

这不是"hack"，而是经典的设计模式：

```
┌─────────────────────────────────────┐
│      Client (业务代码)              │
│  使用统一的接口                      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Target (DatabaseManager)       │
│  定义统一接口                        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Adapter (BaseDatabaseAdapter)  │
│  适配不同实现                        │
└──────┬───────────────────┬──────────┘
       │                   │
       ▼                   ▼
┌─────────────┐    ┌─────────────┐
│ PostgreSQL   │    │   DuckDB    │
│ Adapter      │    │  Adapter    │
└─────────────┘    └─────────────┘
```

## 💡 实际例子

### 例子1：占位符转换（唯一需要"翻译"的地方）

```python
# 业务代码（统一使用 %s）
query = "SELECT * FROM table WHERE id = %s AND name = %s"
params = ('001', 'test')

# PostgreSQLAdapter.execute_query()
# query 保持不变：%s 已经是正确的
cursor.execute(query, params)  # ✅

# DuckDBAdapter.execute_query()
# 需要转换占位符
query = query.replace("%s", "?")  # "SELECT ... WHERE id = ? AND name = ?"
cursor.execute(query, params)  # ✅
```

### 例子2：结果格式统一

```python
# PostgreSQL 返回 RealDictRow
results = cursor.fetchall()
# results = [RealDictRow({'id': '001', 'name': 'test'}), ...]

# 适配器统一转换
return [dict(row) for row in results]
# 返回: [{'id': '001', 'name': 'test'}, ...]

# DuckDB 可能返回元组
results = cursor.fetchall()
# results = [('001', 'test'), ...]

# 适配器统一转换
columns = ['id', 'name']
return [dict(zip(columns, row)) for row in results]
# 返回: [{'id': '001', 'name': 'test'}, ...]
```

### 例子3：连接管理封装

```python
# PostgreSQLAdapter
def execute_query(self, query, params):
    conn = self._get_connection()  # 从连接池获取
    try:
        # 执行查询
        ...
    finally:
        self._put_connection(conn)  # 归还到连接池

# DuckDBAdapter
def execute_query(self, query, params):
    # 直接使用单连接，无需池管理
    cursor = self.conn.execute(query, params)
    ...
```

## ✅ 总结

1. **是的，所有数据库操作都必须通过适配器**
   - `execute_sync_query()` → `adapter.execute_query()`
   - `queue_write()` → `adapter.execute_batch()`
   - `transaction()` → `adapter.transaction()`

2. **不是"翻译SQL语句"，而是在"执行层面"适配**
   - SQL语句本身基本不需要翻译（标准SQL）
   - 主要适配：占位符、连接管理、结果格式、事务处理

3. **这是标准的适配器模式，不是"hack"**
   - 经典设计模式
   - 易于扩展和维护

4. **占位符转换是唯一需要"翻译"的地方**
   - 业务代码统一使用 `%s`
   - DuckDB适配器内部转换为 `?`
   - PostgreSQL适配器保持不变
