# Database 模块 API 文档

本文档采用统一 API 条目格式：函数名、状态、描述、诞生版本、参数（三列表格）、返回值。

---

## DatabaseManager

### 函数名
`DatabaseManager(config: Dict | None = None, is_verbose: bool = False)`

- 状态：`stable`
- 描述：创建数据库管理器实例。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `config` (可选) | `Dict | None` | 未传则按项目上下文加载默认配置 |
| `is_verbose` (可选) | `bool` | 默认 `False`；是否输出详细日志 |

- 返回值：`DatabaseManager`

### 函数名
`initialize() -> None`

- 状态：`stable`
- 描述：初始化连接、表管理器和基础表结构。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`None`

### 函数名
`set_default(instance: DatabaseManager) -> None`

- 状态：`stable`
- 描述：设置全局默认数据库实例。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `instance` | `DatabaseManager` | 必填 |

- 返回值：`None`

### 函数名
`get_default(auto_init: bool = True) -> DatabaseManager`

- 状态：`stable`
- 描述：获取默认数据库实例，可自动初始化。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `auto_init` (可选) | `bool` | 默认 `True`；无默认实例时可自动初始化 |

- 返回值：`DatabaseManager`

### 函数名
`reset_default() -> None`

- 状态：`stable`
- 描述：重置默认数据库实例。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`None`

### 函数名
`execute_sync_query(query: str, params: Any = None) -> List[Dict[str, Any]]`

- 状态：`stable`
- 描述：执行同步 SQL 查询并返回字典列表。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `query` | `str` | 必填 |
| `params` (可选) | `Any` | 参数化查询绑定值；默认 `None` |

- 返回值：`List[Dict[str, Any]]`

### 函数名
`transaction() -> ContextManager[Cursor]`

- 状态：`stable`
- 描述：事务上下文，支持自动提交/回滚。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`ContextManager[Cursor]`

### 函数名
`get_connection() -> ContextManager[Connection]`

- 状态：`stable`
- 描述：获取数据库连接上下文。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`ContextManager[Connection]`

### 函数名
`get_sync_cursor() -> ContextManager[Cursor]`

- 状态：`stable`
- 描述：获取同步游标上下文。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`ContextManager[Cursor]`

### 函数名
`register_table(table_name: str, schema: Dict) -> None`

- 状态：`stable`
- 描述：注册自定义表 schema。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `table_name` | `str` | 必填 |
| `schema` | `Dict` | 必填 |

- 返回值：`None`

### 函数名
`create_registered_tables() -> None`

- 状态：`stable`
- 描述：创建所有已注册的自定义表。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`None`

### 函数名
`is_table_exists(table_name: str) -> bool`

- 状态：`stable`
- 描述：检查表是否存在。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `table_name` | `str` | 必填 |

- 返回值：`bool`

### 函数名
`get_table_schema(table_name: str) -> Dict | None`

- 状态：`stable`
- 描述：获取指定表 schema。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `table_name` | `str` | 必填 |

- 返回值：`Dict | None`

### 函数名
`get_table_fields(table_name: str) -> List[str]`

- 状态：`stable`
- 描述：获取指定表字段列表。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `table_name` | `str` | 必填 |

- 返回值：`List[str]`

### 函数名
`queue_write(table_name: str, data_list: List[Dict], unique_keys: List[str], callback: Callable | None = None) -> None`

- 状态：`stable`
- 描述：提交批量写入任务到队列。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `table_name` | `str` | 必填 |
| `data_list` | `List[Dict]` | 必填 |
| `unique_keys` | `List[str]` | 必填 |
| `callback` (可选) | `Callable | None` | 队列刷盘后回调；默认 `None` |

- 返回值：`None`

### 函数名
`flush_writes(table_name: str | None = None) -> None`

- 状态：`stable`
- 描述：主动 flush 指定表或全部写入队列。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `table_name` (可选) | `str | None` | 仅 flush 指定表；默认 `None` 表示全部 |

- 返回值：`None`

### 函数名
`wait_for_writes(timeout: float = 30.0) -> None`

- 状态：`stable`
- 描述：等待写入队列处理完成。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `timeout` (可选) | `float` | 秒；默认 `30.0` |

- 返回值：`None`

### 函数名
`get_write_stats() -> Dict[str, Any]`

- 状态：`stable`
- 描述：获取写入队列统计信息。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`Dict[str, Any]`

### 函数名
`get_stats() -> Dict[str, Any]`

- 状态：`stable`
- 描述：获取数据库实例状态统计。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`Dict[str, Any]`

### 函数名
`close() -> None`

- 状态：`stable`
- 描述：关闭连接与写入队列资源。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`None`

---

## DbBaseModel

### 函数名
`DbBaseModel(table_name: str, db: DatabaseManager | None = None)`

- 状态：`stable`
- 描述：单表操作基类构造函数。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `table_name` | `str` | 必填 |
| `db` (可选) | `DatabaseManager | None` | 默认使用全局 `DatabaseManager.get_default()` |

- 返回值：`DbBaseModel`

### 函数名
`count(condition: str = "1=1", params: tuple = ()) -> int`

- 状态：`stable`
- 描述：按条件统计记录数。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `condition` (可选) | `str` | 默认 `"1=1"` |
| `params` (可选) | `tuple` | SQL 条件绑定参数；默认 `()` |

- 返回值：`int`

### 函数名
`is_exists(condition: str, params: tuple = ()) -> bool`

- 状态：`stable`
- 描述：按条件判断记录是否存在。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `condition` | `str` | 必填 |
| `params` (可选) | `tuple` | SQL 条件绑定参数；默认 `()` |

- 返回值：`bool`

### 函数名
`load(...) -> List[Dict[str, Any]]`

- 状态：`stable`
- 描述：按条件查询多条记录（支持排序与限制）。
- 诞生版本：`0.2.0`
- params：见函数签名
- 返回值：`List[Dict[str, Any]]`

### 函数名
`load_one(...) -> Dict[str, Any] | None`

- 状态：`stable`
- 描述：按条件查询单条记录。
- 诞生版本：`0.2.0`
- params：见函数签名
- 返回值：`Dict[str, Any] | None`

### 函数名
`load_paginated(page: int = 1, page_size: int = 20, order_by: str | None = None) -> Dict[str, Any]`

- 状态：`stable`
- 描述：分页查询记录。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `page` (可选) | `int` | 默认 `1` |
| `page_size` (可选) | `int` | 默认 `20` |
| `order_by` (可选) | `str | None` | 排序子句；默认 `None` |

- 返回值：`Dict[str, Any]`

### 函数名
`insert_many(rows: List[Dict[str, Any]], unique_keys: List[str] | None = None) -> int`

- 状态：`stable`
- 描述：批量插入数据。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `rows` | `List[Dict[str, Any]]` | 必填 |
| `unique_keys` (可选) | `List[str] | None` | 唯一约束列；默认 `None` |

- 返回值：`int`

### 函数名
`upsert_many(rows: List[Dict[str, Any]], unique_keys: List[str]) -> int`

- 状态：`stable`
- 描述：批量 upsert 数据。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `rows` | `List[Dict[str, Any]]` | 必填 |
| `unique_keys` | `List[str]` | 必填 |

- 返回值：`int`

### 函数名
`delete(condition: str, params: tuple = (), limit: int | None = None) -> int`

- 状态：`stable`
- 描述：按条件删除记录。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `condition` | `str` | 必填 |
| `params` (可选) | `tuple` | SQL 条件绑定参数；默认 `()` |
| `limit` (可选) | `int | None` | 最大删除行数；默认 `None` 表示不限制 |

- 返回值：`int`

### 函数名
`delete_all() -> int`

- 状态：`stable`
- 描述：删除表中所有记录。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`int`

---

## 示例

```python
from core.infra.db import DatabaseManager

db = DatabaseManager(is_verbose=True)
db.initialize()
DatabaseManager.set_default(db)

rows = db.execute_sync_query(
    "SELECT * FROM stock_list WHERE id = %s",
    ("000001.SZ",),
)
print(rows)
```

---

## 相关文档

- `../README.md`
- `./ARCHITECTURE.md`
- `./DECISIONS.md`
