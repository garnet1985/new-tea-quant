# DuckDB 语法迁移审计报告

## 🔍 审计目标

全面检查底层 model 和数据库操作代码，找出所有需要从 MySQL 语法转换为 DuckDB 语法的地方。

**注意**：已移除所有兼容性代码和参数，不再支持 MySQL 语法。所有 MySQL 特定的参数（如 `charset`）和配置都已移除。

---

## ✅ 已修复的问题

### 1. 反引号问题
- ✅ **SystemCacheModel** - 已修复 `"key"` 使用双引号
- ✅ **db_schema_manager.py** - 已修复索引创建时的反引号

### 2. 占位符转换
- ✅ **execute_sync_query** - 已自动转换 `%s` → `?`
- ✅ **DuckDBCursor.execute** - 已自动转换 `%s` → `?`
- ✅ **update()** - 已修复占位符使用

### 3. REPLACE INTO 语句
- ✅ **replace() 兜底方案** - 已改为使用 `INSERT ... ON CONFLICT DO UPDATE`

### 4. cursor.connection.commit() 调用
- ✅ **所有 commit() 调用** - 已移除或添加兼容性处理
- ✅ **DuckDBCursor.connection** - 已添加包装类，提供空操作的 commit() 方法

### 5. executemany() 方法
- ✅ **insert() 方法** - 已改为使用批量 VALUES 语法
- ✅ **replace() 方法** - 已改为使用批量 VALUES 语法

### 6. cursor.rowcount 属性
- ✅ **所有 rowcount 使用** - 已添加兼容性检查

---

## ⚠️ 已修复的问题

### 1. ✅ `cursor.connection.commit()` - 不必要的提交调用

**问题**：DuckDB 是自动提交的，不需要手动调用 `commit()`

**修复**：
- ✅ 移除了所有 `cursor.connection.commit()` 调用
- ✅ 移除了 `DuckDBConnectionWrapper` 兼容类
- ✅ 移除了 `DuckDBCursor.connection` 属性

**修复位置**：
- ✅ `drop_table()` - 已移除 commit()
- ✅ `clear_table()` - 已移除 commit()
- ✅ `delete()` - 已移除 commit()
- ✅ `insert()` - 已移除 commit()
- ✅ `update()` - 已移除 commit()
- ✅ `replace()` - 已移除 commit()
- ✅ `execute_raw_update()` - 已移除 commit()

---

### 2. ✅ `REPLACE INTO` 语句

**问题**：DuckDB 不支持 `REPLACE INTO`，应该使用 `INSERT ... ON CONFLICT DO UPDATE`

**修复**：
- ✅ 已将 `replace()` 方法的兜底方案改为使用 `INSERT ... ON CONFLICT DO UPDATE`
- ✅ 使用批量 VALUES 语法，与批量写入队列保持一致

---

### 3. ✅ `executemany()` 方法

**问题**：虽然 DuckDB 支持 `executemany()`，但批量 VALUES 语法更高效

**修复**：
- ✅ `insert()` 方法已改为使用批量 VALUES 语法
- ✅ `replace()` 方法已改为使用批量 VALUES 语法

---

### 4. ✅ `cursor.rowcount` 属性

**问题**：DuckDB 的 cursor 有 `rowcount` 属性（值为 -1 表示未知）

**修复**：
- ✅ 添加了兼容性检查：`cursor.rowcount if hasattr(cursor, 'rowcount') else 0`
- ✅ `DuckDBCursor` 类已提供 `rowcount` 属性

---

### 5. ✅ `ON DUPLICATE KEY UPDATE` 语句

**问题**：DuckDB 不支持 MySQL 的 `ON DUPLICATE KEY UPDATE`，需要使用 `ON CONFLICT DO UPDATE`

**修复**：
- ✅ `meta_info/model.py` - 已改为使用 `INSERT ... ON CONFLICT DO UPDATE`

---

### 6. ✅ 占位符在条件字符串中的使用

**问题**：虽然 `execute_sync_query` 会自动转换 `%s` → `?`，但在构建 SQL 字符串时直接使用 `%s` 可能有问题

**修复**：
- ✅ `update()` 方法已改为使用 `?` 占位符
- ✅ 添加了统一的占位符转换：`query = query.replace("%s", "?")`

---

## 📊 问题分类

### ✅ 已全部修复

所有发现的问题都已修复：
1. ✅ **REPLACE INTO 语句** - 已改为 `INSERT ... ON CONFLICT DO UPDATE`
2. ✅ **cursor.connection.commit()** - 已移除或添加兼容性处理
3. ✅ **executemany()** - 已改为批量 VALUES 语法
4. ✅ **cursor.rowcount** - 已添加兼容性检查
5. ✅ **get_sync_cursor() 兼容性** - 已添加 connection 包装类
6. ✅ **占位符转换** - 已统一处理

---

## 🔧 详细修复计划

### TODO-1: 修复 REPLACE INTO 语句

**文件**：`app/core/infra/db/db_base_model.py:689-699`

**当前代码**：
```python
# 兜底方案：直接构建 REPLACE INTO 语句
columns, values, _ = DBService.to_upsert_params(data_list, unique_keys)
placeholders = ', '.join(['%s'] * len(columns))
query = f"REPLACE INTO {self.table_name} ({', '.join(columns)}) VALUES ({placeholders})"

with self.db.get_sync_cursor() as cursor:
    cursor.executemany(query, values)
    if hasattr(cursor, 'connection'):
        cursor.connection.commit()
```

**修复后**：
```python
# 兜底方案：使用 INSERT ... ON CONFLICT DO UPDATE
columns, values, update_clause = DBService.to_upsert_params(data_list, unique_keys)
columns_sql = ', '.join(columns)
conflict_cols = ', '.join(unique_keys)

# 构建批量 VALUES
# ... (使用批量 VALUES 语法，类似 batch_write_queue)
```

---

### TODO-2: 移除或修复 commit() 调用

**文件**：`app/core/infra/db/db_base_model.py`

**修复方案 A（推荐）**：完全移除 commit() 调用
```python
# 移除所有 cursor.connection.commit() 调用
```

**修复方案 B**：添加兼容性检查
```python
# 只在 MySQL 模式下调用 commit
if hasattr(cursor, 'connection') and hasattr(cursor.connection, 'commit'):
    try:
        cursor.connection.commit()
    except:
        pass  # DuckDB 不需要 commit
```

---

### TODO-3: 测试 executemany() 兼容性

**测试代码**：
```python
import duckdb
conn = duckdb.connect(':memory:')
cursor = conn.cursor()
cursor.execute("CREATE TABLE test (id INT, name VARCHAR)")
try:
    cursor.executemany("INSERT INTO test VALUES (?, ?)", [(1, 'a'), (2, 'b')])
    print("✅ executemany 支持")
except Exception as e:
    print(f"❌ executemany 不支持: {e}")
    # 需要使用其他方法
```

---

### TODO-4: 测试 rowcount 属性

**测试代码**：
```python
import duckdb
conn = duckdb.connect(':memory:')
cursor = conn.execute("CREATE TABLE test (id INT)")
cursor = conn.execute("INSERT INTO test VALUES (1), (2)")
if hasattr(cursor, 'rowcount'):
    print(f"✅ rowcount 支持: {cursor.rowcount}")
else:
    print("❌ rowcount 不支持")
```

---

## 📝 检查清单

### 语法检查

- [x] 反引号 → 双引号（已修复）
- [x] 占位符 %s → ?（已自动转换）
- [x] REPLACE INTO → INSERT ... ON CONFLICT（已修复）
- [x] cursor.connection.commit()（已移除或修复）
- [x] executemany() → 批量 VALUES（已修复）
- [x] cursor.rowcount（已添加兼容性检查）

### 数据类型检查

- [x] AUTO_INCREMENT（已忽略）
- [x] TINYINT(1) → BOOLEAN（已转换）
- [x] TEXT → VARCHAR（已转换）
- [x] DATETIME → TIMESTAMP（已转换）

### 函数检查

- [x] MySQL 特定函数（未发现使用）

---

## 🔗 相关文件

- [数据库基础模型](./app/core/infra/db/db_base_model.py)
- [数据库管理器](./app/core/infra/db/db_manager.py)
- [Schema 管理器](./app/core/infra/db/db_schema_manager.py)
- [批量写入队列](./app/core/infra/db/batch_write_queue.py)
