# Database 模块 API 文档

按「描述、函数签名、参数、输出、示例」列出 Database 模块中**应用/基础设施代码会直接使用的入口**；底层适配器和内部 helper 不列入。架构与设计见 `architecture.md` / `decisions.md`，快速上手见 `overview.md`。

---

## DatabaseManager

### DatabaseManager（构造函数）

**描述**：数据库管理器（基础设施层的总入口）。负责加载数据库配置、创建连接管理器、Schema 管理器和表管理器，统一封装连接池、事务、批量写入等能力。

**函数签名**：`DatabaseManager(config: Dict | None = None, is_verbose: bool = False)`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `config` | `Dict \| None` | 数据库配置；`None` 时通过 `ConfigManager.load_database_config()` 自动加载 |
| `is_verbose` | `bool` | 是否输出更详细日志，默认 `False` |

**输出**：无（构造实例）

**Example**：

```python
from core.infra.db import DatabaseManager

db = DatabaseManager(is_verbose=True)
db.initialize()
DatabaseManager.set_default(db)
```

---

### initialize

**描述**：初始化 DatabaseManager。创建连接池和适配器、初始化 `TableManager`，并为后续表操作和批量写入做好准备。

**函数签名**：`DatabaseManager.initialize() -> None`

**参数**：无

**输出**：`None`

**Example**：

```python
db = DatabaseManager(is_verbose=True)
db.initialize()
```

---

### set_default / get_default / reset_default

**描述**：管理全局默认 `DatabaseManager` 实例，方便在任何地方通过 `DatabaseManager.get_default()` 获取已初始化的 db。

**函数签名**：

- `DatabaseManager.set_default(instance: DatabaseManager) -> None`  
- `DatabaseManager.get_default(auto_init: bool = True) -> DatabaseManager`  
- `DatabaseManager.reset_default() -> None`

**参数（摘选）**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `instance` | `DatabaseManager` | 需要设置为默认实例的对象 |
| `auto_init` | `bool` | 无默认实例时，是否自动创建并 `initialize()` 一个新实例 |

**输出**：

- `set_default` / `reset_default`：`None`  
- `get_default`：`DatabaseManager` 实例

**Example**：

```python
db = DatabaseManager(is_verbose=True)
db.initialize()
DatabaseManager.set_default(db)

# 其他模块获取默认实例
db2 = DatabaseManager.get_default()
```

---

### 连接与事务相关 API

#### get_connection

**描述**：获取数据库连接的上下文管理器，适合执行多条原生 SQL。

**函数签名**：`DatabaseManager.get_connection() -> ContextManager[Connection]`

**Example**：

```python
with db.get_connection() as conn:
    with conn.cursor() as cursor:
        cursor.execute("SELECT 1")
```

#### transaction

**描述**：事务上下文管理器，在 `with` 代码块中自动提交/回滚。

**函数签名**：`DatabaseManager.transaction() -> ContextManager[Cursor]`

**Example**：

```python
with db.transaction() as cursor:
    cursor.execute("INSERT INTO ...")
    cursor.execute("UPDATE ...")
```

#### get_sync_cursor

**描述**：获取同步游标的上下文管理器，适合简单读写操作。

**函数签名**：`DatabaseManager.get_sync_cursor() -> ContextManager[Cursor]`

**Example**：

```python
with db.get_sync_cursor() as cursor:
    cursor.execute("SELECT * FROM stock_list WHERE id = %s", ("000001.SZ",))
    rows = cursor.fetchall()
```

#### execute_sync_query

**描述**：执行同步查询并返回字典列表，是最常用的「直接 SQL 查询」入口。

**函数签名**：`DatabaseManager.execute_sync_query(query: str, params: Any = None) -> List[Dict[str, Any]]`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | `str` | SQL 语句，应使用占位符 `%s` |
| `params` | `Any` | 参数（元组或列表），与 `%s` 对应 |

**输出**：`List[Dict[str, Any]]` —— 每行一个字典，键为列名。

**Example**：

```python
rows = db.execute_sync_query(
    "SELECT * FROM stock_list WHERE id = %s",
    ("000001.SZ",),
)
```

---

### 表与 Schema 相关 API

> 这些接口主要用于**自定义表**和工具脚本中检查表结构。应用层更推荐通过 `DataManager.register_table()` 间接使用。

#### register_table

**描述**：注册自定义表（策略/用户表）。注册后可通过 `create_registered_tables()` 创建表。

**函数签名**：`DatabaseManager.register_table(table_name: str, schema: Dict) -> None`

#### create_registered_tables

**描述**：创建所有已注册的自定义表（通常在策略初始化阶段调用一次）。

**函数签名**：`DatabaseManager.create_registered_tables() -> None`

#### is_table_exists / get_table_schema / get_table_fields

**描述**：检查表是否存在、读取表的 schema 和字段列表。

**函数签名**：

- `DatabaseManager.is_table_exists(table_name: str) -> bool`  
- `DatabaseManager.get_table_schema(table_name: str) -> Optional[Dict]`  
- `DatabaseManager.get_table_fields(table_name: str) -> List[str]`

**Example**：

```python
if not db.is_table_exists("custom_table"):
    # 注册并创建表 ...
schema = db.get_table_schema("stock_kline")
fields = db.get_table_fields("stock_kline")
```

---

### 批量写入相关 API

#### queue_write

**描述**：将写入任务推入批量写入队列，由后台线程统一落库，减少频繁 I/O。

**函数签名**：`DatabaseManager.queue_write(table_name: str, data_list: List[Dict], unique_keys: List[str], callback: Callable | None = None) -> None`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `table_name` | `str` | 表名 |
| `data_list` | `List[Dict]` | 要写入的数据行列表 |
| `unique_keys` | `List[str]` | 唯一键字段列表，用于 upsert |
| `callback` | `Callable \| None` | 可选回调，在写入完成后调用 |

#### flush_writes / wait_for_writes / get_write_stats

**描述**：手动控制和监控批量写入队列。

**函数签名**：

- `DatabaseManager.flush_writes(table_name: Optional[str] = None) -> None`  
- `DatabaseManager.wait_for_writes(timeout: float = 30.0) -> None`  
- `DatabaseManager.get_write_stats() -> Dict[str, Any]`

**Example**：

```python
db.queue_write("stock_kline", kline_rows, unique_keys=["id", "date"])
db.flush_writes("stock_kline")
db.wait_for_writes(timeout=60.0)
stats = db.get_write_stats()
```

---

### 关闭与状态

#### close / get_stats

**描述**：关闭数据库连接与写入队列，并获取当前数据库配置与状态。

**函数签名**：

- `DatabaseManager.close() -> None`  
- `DatabaseManager.get_stats() -> Dict[str, Any]`

---

## DbBaseModel（表操作基类）

**模块路径**：`core.infra.db.table_queriers.db_base_model.DbBaseModel`

### DbBaseModel（构造函数）

**描述**：单表 CRUD 封装的基类。所有基础表 Model 和自定义表 Model 都推荐继承此类，以获得统一的增删改查能力。

**函数签名**：`DbBaseModel(table_name: str, db: DatabaseManager | None = None)`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `table_name` | `str` | 表名 |
| `db` | `DatabaseManager \| None` | 可选 `DatabaseManager`；不传时使用 `DatabaseManager.get_default(auto_init=True)` |

**输出**：无（构造实例）

**Example**：

```python
from core.infra.db import DbBaseModel

model = DbBaseModel("stock_kline")
```

---

### count / is_exists

**描述**：统计记录数、检查记录是否存在。

**函数签名**：

- `DbBaseModel.count(condition: str = "1=1", params: tuple = ()) -> int`  
- `DbBaseModel.is_exists(condition: str, params: tuple = ()) -> bool`

**Example**：

```python
total = model.count()
has_daily = model.is_exists("term = %s", ("daily",))
```

---

### load / load_one / load_paginated

**描述**：按条件查询记录，支持排序、分页等。

**函数签名（部分）**：

- `DbBaseModel.load(condition: str = "1=1", params: tuple = (), order_by: str | None = None, limit: int | None = None, offset: int | None = None) -> List[Dict[str, Any]]`  
- `DbBaseModel.load_one(condition: str = "1=1", params: tuple = (), order_by: str | None = None) -> Optional[Dict[str, Any]]`  
- `DbBaseModel.load_paginated(page: int = 1, page_size: int = 20, order_by: str | None = None) -> Dict[str, Any]`

**Example**：

```python
records = model.load("id = %s", ("000001.SZ",), order_by="date DESC", limit=100)
one = model.load_one("id = %s AND date = %s", ("000001.SZ", "20250101"))
page = model.load_paginated(page=1, page_size=50, order_by="date DESC")
```

---

### insert_many / upsert_many（同步）

**描述**：批量插入或 upsert 数据（同步写入）。

**函数签名**：

- `DbBaseModel.insert_many(rows: List[Dict[str, Any]], unique_keys: List[str] | None = None) -> int`  
- `DbBaseModel.upsert_many(rows: List[Dict[str, Any]], unique_keys: List[str]) -> int`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `rows` | `List[Dict[str, Any]]` | 待写入的记录列表 |
| `unique_keys` | `List[str]` | 唯一键字段列表，用于 upsert |

**输出**：`int` —— 实际写入/更新的行数。

**Example**：

```python
rows = [
    {"id": "000001.SZ", "date": "20250101", "close": 10.5},
    {"id": "000001.SZ", "date": "20250102", "close": 10.8},
]
model.upsert_many(rows, unique_keys=["id", "date"])
```

---

### delete / delete_all

**描述**：按条件删除数据，或清空整张表。

**函数签名**：

- `DbBaseModel.delete(condition: str, params: tuple = (), limit: int | None = None) -> int`  
- `DbBaseModel.delete_all() -> int`

**Example**：

```python
# 删除某只股票的数据
deleted = model.delete("id = %s", ("000001.SZ",))

# 清空整张表（慎用）
model.delete_all()
```

---

## 相关文档

- [Database 概览](./overview.md)  
- [Database 架构](./architecture.md)  
- [Database 设计决策](./decisions.md)  

