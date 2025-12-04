# BaseTableModel 使用指南

## 📖 简介

`BaseTableModel` 是一个通用的数据库表操作工具类，提供了完整的 CRUD 接口和针对时序数据的特殊查询方法。

**定位**：纯工具类，不涉及业务逻辑，放在 `utils/db/` 下

**特点**：
- 🚀 性能优先（直接 SQL，无 ORM 开销）
- 🛡️ 安全（参数化查询，防 SQL 注入）
- 📊 时序数据优化（`load_latest_records`、`load_latest_date` 等）
- 🔄 重试机制（应对高并发场景）
- 📦 批量操作（高性能的批量插入/更新）

---

## 🎯 核心方法

### 1. 查询操作

#### `load()` - 通用查询
```python
def load(
    self, 
    condition: str = "1=1",      # WHERE 条件
    params: tuple = (),          # 参数（防 SQL 注入）
    order_by: str = None,        # 排序
    limit: int = None,           # 限制数量
    offset: int = None           # 偏移量
) -> List[Dict[str, Any]]
```

**示例**：
```python
# 基础查询
records = model.load("id = %s", ('000001.SZ',))

# 带排序
records = model.load("id = %s", ('000001.SZ',), order_by="date DESC")

# 分页
records = model.load("1=1", limit=10, offset=20)

# 复杂条件
records = model.load(
    "id = %s AND date BETWEEN %s AND %s AND close > %s",
    ('000001.SZ', '20200101', '20201231', 10.0)
)
```

#### `load_one()` - 查询单条
```python
def load_one(
    self, 
    condition: str = "1=1",
    params: tuple = (),
    order_by: str = None
) -> Optional[Dict[str, Any]]
```

**示例**：
```python
# 查询最新记录
latest = model.load_one("id = %s", ('000001.SZ',), order_by="date DESC")

# 查询最老记录
oldest = model.load_one("id = %s", ('000001.SZ',), order_by="date ASC")
```

#### `load_latest_date()` - 查询最新日期（时序数据特有）
```python
def load_latest_date(self, date_field: str = None) -> Optional[str]
```

**示例**：
```python
# 自动从 schema 中查找日期字段
latest_date = model.load_latest_date()  # 返回: "20240101"

# 指定日期字段
latest_date = model.load_latest_date(date_field="trade_date")
```

#### `load_latest_records()` - 查询最新记录（时序数据特有）⭐
```python
def load_latest_records(
    self,
    date_field: str = None,      # 日期字段
    primary_keys: List[str] = None  # 主键列表
) -> List[Dict[str, Any]]
```

**功能**：查询每个分组的最新记录（例如每个股票的最新 K 线）

**示例**：
```python
# 查询每个股票的最新 K 线
# 自动从 schema 获取日期字段和主键
latest_klines = kline_model.load_latest_records()
# 返回: [{'id': '000001.SZ', 'date': '20240101', ...}, ...]

# 指定字段
latest_records = model.load_latest_records(
    date_field='trade_date',
    primary_keys=['id', 'trade_date']
)
```

#### `load_paginated()` - 分页查询
```python
def load_paginated(
    self,
    page: int = 1,
    page_size: int = 20,
    order_by: str = None
) -> Dict[str, Any]
```

**示例**：
```python
result = model.load_paginated(page=1, page_size=20, order_by="date DESC")
# 返回:
# {
#     'data': [...],          # 当前页数据
#     'total': 1000,          # 总记录数
#     'page': 1,              # 当前页
#     'page_size': 20,        # 每页大小
#     'total_pages': 50       # 总页数
# }
```

---

### 2. 写入操作

#### `save()` - 保存单条
```python
def save(self, data: Dict[str, Any]) -> int
```

**示例**：
```python
model.save({
    'id': '000001.SZ',
    'date': '20240101',
    'open': 10.0,
    'close': 10.5
})
```

#### `save_many()` - 批量保存
```python
def save_many(self, data_list: List[Dict[str, Any]]) -> int
```

**示例**：
```python
model.save_many([
    {'id': '000001.SZ', 'date': '20240101', 'close': 10.0},
    {'id': '000001.SZ', 'date': '20240102', 'close': 10.5},
])
```

#### `upsert()` / `replace()` - 插入或更新⭐
```python
def replace(
    self,
    data_list: List[Dict[str, Any]],
    unique_keys: List[str]  # 唯一键（用于判断是否已存在）
) -> int
```

**功能**：如果记录存在则更新，不存在则插入

**示例**：
```python
# 基于 (id, date) 判断是否存在
model.replace(
    [
        {'id': '000001.SZ', 'date': '20240101', 'close': 10.0},
        {'id': '000001.SZ', 'date': '20240102', 'close': 10.5},
    ],
    unique_keys=['id', 'date']
)

# 大数据量自动使用异步写入队列
model.replace(large_data_list, unique_keys=['id', 'date'])
```

---

### 3. 删除操作

#### `delete()` - 删除记录
```python
def delete(
    self,
    condition: str,
    params: tuple = (),
    limit: int = None
) -> int  # 返回删除的记录数
```

**示例**：
```python
# 删除指定日期之前的数据
deleted = model.delete("date < %s", ('20200101',))

# 删除单条
deleted = model.delete_one("id = %s AND date = %s", ('000001.SZ', '20240101'))

# 清空表
model.clear_table()
```

---

### 4. 统计操作

#### `count()` - 统计数量
```python
def count(self, condition: str = "1=1", params: tuple = ()) -> int
```

**示例**：
```python
# 统计总数
total = model.count()

# 条件统计
count = model.count("close > %s", (10.0,))
```

#### `exists()` - 检查是否存在
```python
def exists(self, condition: str, params: tuple = ()) -> bool
```

**示例**：
```python
if model.exists("id = %s AND date = %s", ('000001.SZ', '20240101')):
    print("记录已存在")
```

---

## 📚 完整使用示例

### 示例 1: 直接使用（简单场景）

```python
from utils.db.db_manager import DatabaseManager
from utils.db.db_model import BaseTableModel

# 初始化
db = DatabaseManager(is_verbose=True)
db.initialize()

# 创建 Model
kline_model = BaseTableModel('stock_kline', db)

# 查询
records = kline_model.load(
    "id = %s AND date BETWEEN %s AND %s",
    ('000001.SZ', '20200101', '20201231'),
    order_by="date ASC"
)

# 写入
kline_model.save({
    'id': '000001.SZ',
    'date': '20240101',
    'open': 10.0,
    'close': 10.5
})
```

---

### 示例 2: 继承使用（推荐，业务场景）

```python
# app/data_manager/models/stock_kline_model.py
from typing import List, Dict, Any
from utils.db.db_model import BaseTableModel

class StockKlineModel(BaseTableModel):
    """K线数据 Model"""
    
    def __init__(self, db):
        super().__init__('stock_kline', db)
    
    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        """查询指定股票的所有 K 线"""
        return self.load("id = %s", (stock_id,), order_by="date ASC")
    
    def load_by_date_range(
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
        return self.load_one(
            "id = %s", 
            (stock_id,),
            order_by="date DESC"
        )
    
    def save_klines(self, klines: List[Dict[str, Any]]) -> int:
        """批量保存 K 线（自动去重）"""
        return self.replace(klines, unique_keys=['id', 'date'])

# 使用
db = DatabaseManager()
db.initialize()

kline_model = StockKlineModel(db)

# 使用业务方法
klines = kline_model.load_by_date_range('000001.SZ', '20200101', '20201231')
latest = kline_model.load_latest('000001.SZ')
```

---

### 示例 3: 时序数据查询

```python
# 查询每个股票的最新 K 线
kline_model = BaseTableModel('stock_kline', db)
latest_klines = kline_model.load_latest_records()
# 返回: [
#     {'id': '000001.SZ', 'date': '20240101', 'close': 10.0, ...},
#     {'id': '000002.SZ', 'date': '20240101', 'close': 20.0, ...},
#     ...
# ]

# 查询最新日期
latest_date = kline_model.load_latest_date()
print(f"最新数据日期: {latest_date}")  # 20240101

# 查询指定日期的所有股票数据
klines = kline_model.load("date = %s", (latest_date,))
```

---

### 示例 4: 批量操作和性能优化

```python
# 批量插入（小数据量）
kline_model.save_many([
    {'id': '000001.SZ', 'date': '20240101', 'close': 10.0},
    {'id': '000001.SZ', 'date': '20240102', 'close': 10.5},
    # ... 100 条
])

# Upsert（大数据量，自动使用异步队列）
large_data = [...]  # 10000+ 条
kline_model.replace(
    large_data,
    unique_keys=['id', 'date']
)
# 自动使用异步写入队列，不阻塞主线程
```

---

## 🏗️ 架构建议

```
utils/db/                          ← 基础设施层（工具类）
├── db_manager.py                  # 连接池 + 基础 CRUD
├── db_model.py                    # BaseTableModel（通用工具）
└── schema_manager.py              # Schema 管理

app/data_manager/                  ← 业务层
├── base_tables/                   # Schema 定义（JSON）
├── models/                        # 业务 Model（继承 BaseTableModel）⭐
│   ├── stock_kline_model.py
│   ├── gdp_model.py
│   └── ...
├── repositories/                  # 跨表查询 ⭐
│   ├── stock_repository.py
│   └── ...
└── loaders/                       # 数据加载器（兼容层）
```

**职责划分**：
- `BaseTableModel`（utils/db）：通用工具，单表 CRUD
- 具体 Model（app/data_manager/models）：业务封装，继承 BaseTableModel
- Repository（app/data_manager/repositories）：跨表查询

---

## 📝 注意事项

### 1. SQL 注入防护
**始终使用参数化查询**：
```python
# ✅ 正确
model.load("id = %s", ('000001.SZ',))

# ❌ 错误（SQL 注入风险）
model.load(f"id = '{stock_id}'")
```

### 2. 性能优化
- 使用 `load_one()` 而不是 `load()[0]`
- 批量操作使用 `save_many()` 或 `replace()`
- 大数据量（1000+ 条）自动使用异步写入队列

### 3. 时序数据优化
- 使用 `load_latest_records()` 获取每个分组的最新记录
- 使用 `load_latest_date()` 快速获取最新日期
- Schema 中需要定义 `primaryKey` 和日期字段

---

## 🔗 相关文档

- [DatabaseManager 文档](./README.md)
- [SchemaManager 文档](./schema_manager.py)
- [Repository 模式指南](../../app/data_manager/repositories/README.md)

---

## 📞 FAQ

**Q: BaseTableModel 和 ORM 的区别？**  
A: BaseTableModel 是轻量级的数据访问层，不是完整的 ORM。它提供了常用的 CRUD 方法，但没有关系映射、类型安全等 ORM 特性。优势是性能更好、更灵活。

**Q: 什么时候应该继承 BaseTableModel？**  
A: 当你需要为特定表添加业务方法时。例如 `StockKlineModel` 添加 `load_by_date_range()` 等方法。

**Q: 跨表查询怎么办？**  
A: 使用 Repository 模式。Repository 内部可以使用多个 Model，或直接使用 `db.execute_sync_query()` 执行复杂 SQL。

**Q: 如何添加类型提示？**  
A: 使用 `TypedDict` 定义返回类型：
```python
from typing import TypedDict

class KlineData(TypedDict):
    id: str
    date: str
    open: float
    close: float

class StockKlineModel(BaseTableModel):
    def load(self, ...) -> List[KlineData]:
        return super().load(...)
```

