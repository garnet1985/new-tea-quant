# Drupal 数据库抽象层设计学习

## 🎯 Drupal 的设计理念

Drupal 的数据库抽象层（Database Abstraction Layer, DAL）是一个非常成熟的设计，值得我们学习。它和我们的适配器模式有很多相似之处，但也有一些不同的设计选择。

---

## 📐 核心架构

### 1. 分层设计

```
┌─────────────────────────────────────────┐
│   Module Code (业务代码)                │
│   使用统一的 Database API               │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   Connection (连接抽象层)                │
│   - query()                              │
│   - select() / insert() / update()      │
│   - transaction()                        │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   Driver (驱动层)                        │
│   - MySQL Driver                         │
│   - PostgreSQL Driver                    │
│   - SQLite Driver                        │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   PDO (PHP 数据库抽象)                   │
└─────────────────────────────────────────┘
```

### 2. 关键组件

| 组件 | 职责 | 对应我们的实现 |
|------|------|---------------|
| **Connection** | 统一的数据库连接接口 | `DatabaseManager` |
| **Driver** | 处理数据库特定逻辑 | `PostgreSQLAdapter`, `MySQLAdapter`, `SQLiteAdapter` |
| **Query Builder** | 构建 SQL 查询（可选） | 我们直接使用 SQL |
| **Schema API** | 表结构管理 | `DbSchemaManager` |
| **Transaction Manager** | 事务管理 | `adapter.transaction()` |

---

## 🔍 Drupal 的设计模式

### 1. Bridge Pattern（桥接模式）

**Drupal 的做法：**
```php
// 抽象层
interface ConnectionInterface {
    public function query($query, array $args = []);
    public function select($table, $alias = NULL);
}

// 实现层（驱动）
class MysqlConnection implements ConnectionInterface {
    public function query($query, array $args = []) {
        // MySQL 特定实现
    }
}

class PgsqlConnection implements ConnectionInterface {
    public function query($query, array $args = []) {
        // PostgreSQL 特定实现
    }
}
```

**我们的做法（类似）：**
```python
# 抽象层
class BaseDatabaseAdapter(ABC):
    @abstractmethod
    def execute_query(self, query: str, params: Any = None):
        pass

# 实现层（适配器）
class PostgreSQLAdapter(BaseDatabaseAdapter):
    def execute_query(self, query: str, params: Any = None):
        # PostgreSQL 特定实现
        pass

class MySQLAdapter(BaseDatabaseAdapter):
    def execute_query(self, query: str, params: Any = None):
        # MySQL 特定实现
        pass
```

**✅ 我们已经在使用相同的模式！**

---

### 2. Query Builder Pattern（查询构建器）

**Drupal 的做法：**
```php
// 使用查询构建器（避免直接写 SQL）
$query = \Drupal::database()->select('node', 'n');
$query->fields('n', ['nid', 'title']);
$query->condition('n.type', 'article');
$query->range(0, 10);
$results = $query->execute()->fetchAll();
```

**我们的做法：**
```python
# 直接使用 SQL（更灵活，性能更好）
results = db.execute_sync_query(
    "SELECT nid, title FROM node WHERE type = %s LIMIT 10",
    ('article',)
)
```

**对比：**
- **Drupal 方式**：更安全，自动处理 SQL 方言，但可能有性能开销
- **我们的方式**：更灵活，性能更好，但需要手动处理 SQL 差异

---

### 3. Driver Factory Pattern（驱动工厂）

**Drupal 的做法：**
```php
// 根据配置自动选择驱动
$databases['default']['default'] = [
    'driver' => 'mysql',  // 或 'pgsql', 'sqlite'
    'database' => 'drupal',
    // ...
];

// 工厂自动创建对应的驱动
$connection = Database::getConnection('default', 'default');
// 内部会根据 'driver' 创建 MysqlConnection 或 PgsqlConnection
```

**我们的做法（完全一致）：**
```python
# 根据配置自动选择适配器
config = {
    'database_type': 'postgresql',  # 或 'mysql', 'sqlite'
    'postgresql': {...}
}

# 工厂自动创建对应的适配器
adapter = DatabaseAdapterFactory.create(config)
# 内部会根据 'database_type' 创建 PostgreSQLAdapter 或 MySQLAdapter
```

**✅ 我们已经在使用相同的模式！**

---

## 🎨 Drupal 的关键设计决策

### 1. 基于 PDO 构建

**Drupal：**
- 使用 PHP 的 PDO（PHP Data Objects）作为底层
- PDO 已经提供了基本的数据库抽象
- Drupal 在此基础上添加了查询构建器、Schema API 等

**我们：**
- 直接使用数据库驱动（`psycopg2`, `pymysql`, `sqlite3`）
- 没有中间层，性能更好
- 需要自己处理所有差异

**对比：**
- **Drupal 方式**：有 PDO 作为基础，减少了一些工作
- **我们的方式**：更底层，完全控制，性能更好

---

### 2. Query Builder vs Raw SQL

**Drupal：**
```php
// 推荐使用查询构建器
$query = \Drupal::database()->select('users', 'u')
    ->fields('u', ['uid', 'name'])
    ->condition('u.status', 1)
    ->execute();

// 也支持原始 SQL（但不推荐）
$results = \Drupal::database()->query(
    "SELECT uid, name FROM {users} WHERE status = :status",
    [':status' => 1]
);
```

**我们：**
```python
# 直接使用 SQL（推荐）
results = db.execute_sync_query(
    "SELECT uid, name FROM users WHERE status = %s",
    (1,)
)
```

**对比：**
- **Drupal 方式**：更安全，自动处理 SQL 方言，但学习曲线陡
- **我们的方式**：更直观，性能更好，但需要手动处理差异

---

### 3. Schema API（表结构管理）

**Drupal：**
```php
// 使用 hook_schema() 定义表结构
function mymodule_schema() {
    $schema['my_table'] = [
        'description' => 'My table description',
        'fields' => [
            'id' => [
                'type' => 'serial',
                'not null' => TRUE,
            ],
            'name' => [
                'type' => 'varchar',
                'length' => 255,
            ],
        ],
        'primary key' => ['id'],
    ];
    return $schema;
}

// Drupal 自动根据数据库类型生成 SQL
// MySQL: AUTO_INCREMENT
// PostgreSQL: SERIAL
// SQLite: INTEGER PRIMARY KEY
```

**我们：**
```python
# 使用 JSON Schema 定义表结构
schema = {
    "name": "my_table",
    "fields": [
        {"name": "id", "type": "INTEGER", "primaryKey": True, "autoIncrement": True},
        {"name": "name", "type": "VARCHAR", "length": 255}
    ]
}

# SchemaManager 根据数据库类型生成 SQL
# PostgreSQL: SERIAL
# MySQL: AUTO_INCREMENT
# SQLite: INTEGER PRIMARY KEY
```

**✅ 我们已经在使用类似的 Schema API！**

---

### 4. 占位符处理

**Drupal：**
```php
// 使用命名占位符（:name）
$query = "SELECT * FROM {users} WHERE name = :name AND age > :age";
$args = [':name' => 'John', ':age' => 18];
$results = \Drupal::database()->query($query, $args);

// 驱动内部转换为数据库特定的占位符
// MySQL/PostgreSQL: :name -> ?
// SQLite: :name -> ?
```

**我们：**
```python
# 使用位置占位符（%s）
query = "SELECT * FROM users WHERE name = %s AND age > %s"
params = ('John', 18)
results = db.execute_sync_query(query, params)

# 适配器内部转换为数据库特定的占位符
# PostgreSQL/MySQL: %s -> %s（不变）
# SQLite: %s -> ?
```

**对比：**
- **Drupal 方式**：命名占位符更清晰，但需要字典参数
- **我们的方式**：位置占位符更简单，但需要记住参数顺序

---

### 5. 结果格式统一

**Drupal：**
```php
// 统一返回 StatementInterface，可以迭代
$results = \Drupal::database()->query("SELECT * FROM users");
foreach ($results as $row) {
    // $row 是对象，可以 $row->name 或 $row['name']
    echo $row->name;
}
```

**我们：**
```python
# 统一返回字典列表
results = db.execute_sync_query("SELECT * FROM users")
for row in results:
    # row 是字典
    print(row['name'])
```

**✅ 我们已经在统一结果格式！**

---

## 💡 我们可以从 Drupal 学习的地方

### 1. Query Builder（可选增强）

**当前：**
```python
# 直接写 SQL
query = "SELECT * FROM users WHERE name = %s AND age > %s"
results = db.execute_sync_query(query, ('John', 18))
```

**可以学习 Drupal 添加查询构建器（可选）：**
```python
# 使用查询构建器（更安全，自动处理 SQL 方言）
query = db.select('users')
    .fields(['name', 'age'])
    .condition('name', 'John')
    .condition('age', 18, '>')
    .range(0, 10)
    .execute()
```

**建议：**
- 保持当前直接 SQL 的方式（性能好，灵活）
- 如果需要，可以添加查询构建器作为可选功能

---

### 2. Schema API 增强

**Drupal 的 Schema API 特点：**
- 自动处理数据库类型差异（AUTO_INCREMENT vs SERIAL）
- 支持表前缀（多站点共享数据库）
- 自动生成迁移脚本

**我们的 Schema API 可以增强：**
```python
# 当前：手动处理类型差异
if database_type == 'postgresql':
    type_def = "SERIAL"
elif database_type == 'mysql':
    type_def = "INT AUTO_INCREMENT"

# 可以学习 Drupal：在 SchemaManager 中统一处理
type_def = schema_manager.get_auto_increment_type(database_type)
```

---

### 3. 连接管理增强

**Drupal：**
- 支持多个连接（主从复制）
- 支持连接池
- 自动故障转移

**我们可以增强：**
```python
# 当前：单个连接
db = DatabaseManager(config)

# 可以学习 Drupal：支持多个连接
db = DatabaseManager({
    'default': {'database_type': 'postgresql', ...},
    'replica': {'database_type': 'postgresql', ...}  # 只读副本
})

# 自动路由：读操作 -> replica，写操作 -> default
results = db.execute_sync_query("SELECT ...")  # 自动使用 replica
db.execute_write("INSERT ...")  # 自动使用 default
```

---

### 4. 事务嵌套支持

**Drupal：**
```php
// 支持嵌套事务（使用 savepoint）
$transaction = \Drupal::database()->startTransaction();
try {
    // 操作 1
    $transaction2 = \Drupal::database()->startTransaction();  // 嵌套
    try {
        // 操作 2
        $transaction2->rollback();  // 只回滚操作 2
    } catch (\Exception $e) {
        $transaction2->rollback();
    }
    $transaction->commit();  // 提交操作 1
} catch (\Exception $e) {
    $transaction->rollback();
}
```

**我们当前：**
```python
# 简单事务（不支持嵌套）
with db.transaction() as cursor:
    cursor.execute("INSERT ...")
    # 如果出错，整个事务回滚
```

**可以增强：**
```python
# 支持嵌套事务（使用 savepoint）
with db.transaction() as t1:
    t1.execute("INSERT ...")
    with db.transaction() as t2:  # 嵌套事务
        t2.execute("UPDATE ...")
        # 如果出错，只回滚 t2，t1 继续
```

---

## 📊 对比总结

| 特性 | Drupal | 我们的实现 | 建议 |
|------|--------|-----------|------|
| **适配器模式** | ✅ Driver 系统 | ✅ Adapter 系统 | 保持一致 |
| **工厂模式** | ✅ Driver Factory | ✅ Adapter Factory | 保持一致 |
| **查询方式** | Query Builder + Raw SQL | Raw SQL | 保持当前，可选添加 Query Builder |
| **Schema API** | ✅ hook_schema() | ✅ JSON Schema | 可以增强类型处理 |
| **占位符** | 命名占位符 | 位置占位符 | 保持当前（更简单） |
| **结果格式** | StatementInterface | List[Dict] | 保持一致 |
| **连接管理** | 多连接 + 连接池 | 单连接 | 可以增强（主从复制） |
| **事务嵌套** | ✅ Savepoint | ❌ 不支持 | 可以增强 |

---

## 🎯 关键学习点

### 1. 分层清晰
- **抽象层**：统一的 API（Connection）
- **实现层**：数据库特定的驱动（Driver）
- **底层**：PDO 或原生驱动

### 2. 渐进式增强
- **基础功能**：直接 SQL（我们当前的方式）
- **高级功能**：Query Builder（可选添加）

### 3. Schema 统一管理
- 使用声明式 Schema（JSON/YAML）
- 自动处理数据库类型差异
- 支持迁移和版本控制

### 4. 保持简单
- 核心 API 简单直观
- 复杂功能可选
- 性能优先

---

## 💡 建议

### 保持当前设计（已经很好了）
1. ✅ 适配器模式（和 Drupal 的 Driver 类似）
2. ✅ 工厂模式（自动选择适配器）
3. ✅ Schema API（JSON Schema 定义）
4. ✅ 统一结果格式（字典列表）

### 可选增强（参考 Drupal）
1. 🔄 **查询构建器**：如果需要更安全的 SQL 构建
2. 🔄 **多连接支持**：如果需要主从复制
3. 🔄 **嵌套事务**：如果需要复杂的事务场景
4. 🔄 **Schema 类型映射增强**：自动处理更多类型差异

### 不推荐学习的地方
1. ❌ **过度抽象**：Drupal 的 Query Builder 对于简单查询可能过于复杂
2. ❌ **依赖 PDO**：Python 没有类似 PDO 的标准库，直接使用驱动更好
3. ❌ **命名占位符**：位置占位符更简单，性能更好

---

## 🎓 总结

**Drupal 的数据库抽象层设计非常成熟，我们的实现已经采用了类似的核心模式：**

1. ✅ **适配器模式** = Drupal 的 Driver 系统
2. ✅ **工厂模式** = Drupal 的 Driver Factory
3. ✅ **Schema API** = Drupal 的 hook_schema()

**主要区别：**
- Drupal：Query Builder + Raw SQL（更安全，但更复杂）
- 我们：Raw SQL（更灵活，性能更好）

**建议：**
- 保持当前设计（已经很好了）
- 如果需要，可以参考 Drupal 添加可选的高级功能
- 但不要过度设计，保持简单和性能优先

我们的实现已经很好地借鉴了 Drupal 的核心设计理念！🎉
