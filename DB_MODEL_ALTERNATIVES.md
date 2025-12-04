# BaseTableModel 替代方案分析

## 📋 问题分析

### 当前 BaseTableModel 提供的功能

```python
class BaseTableModel:
    # CRUD 基础
    def load(condition, params, order_by, limit)
    def load_one()
    def load_all()
    def save(data)
    def save_many(data_list)
    def update(data, condition, params)
    def delete(condition, params)
    
    # 工具方法
    def count(condition, params)
    def exists(condition, params)
    def upsert(data, conflict_fields)
    def load_paginated(page, page_size)
    
    # 表管理
    def create_table()
    def drop_table()
    def clear_table()
```

---

## 🎯 推荐方案（按优先级）

### 方案 1：不需要额外库（强烈推荐）⭐⭐⭐⭐⭐

**结论**：你的 `DatabaseManager` 已经够用了！

**理由**：
- ✅ DatabaseManager 提供了完整的 CRUD
- ✅ 接口简洁清晰
- ✅ 无额外依赖
- ✅ 性能好
- ✅ 易于定制

**对比**：

| 功能 | BaseTableModel | DatabaseManager | 是否满足 |
|------|----------------|-----------------|----------|
| 查询 | load() | select(), fetch_all() | ✅ |
| 插入 | save() | insert(), bulk_insert() | ✅ |
| 更新 | update() | update() | ✅ |
| 删除 | delete() | delete() | ✅ |
| 事务 | ❌ | transaction() | ✅ 更好 |
| 分页 | load_paginated() | select(limit) | ✅ |
| 批量 | save_many() | bulk_insert() | ✅ |

**使用示例**：
```python
# 旧代码（BaseTableModel）
model = BaseTableModel('stock_kline', db)
records = model.load(condition="id = %s", params=('000001.SZ',))

# 新代码（DatabaseManager - 更简洁）
records = db.select('stock_kline', where='id = %s', params=['000001.SZ'])
```

---

### 方案 2：如果需要 ActiveRecord 模式 - Peewee ⭐⭐⭐

如果你真的需要类似 BaseTableModel 的 ORM 风格：

```python
from peewee import *

db = MySQLDatabase('stocks', user='root', host='localhost')

class StockKline(Model):
    id = CharField()
    date = CharField()
    close = FloatField()
    
    class Meta:
        database = db
        table_name = 'stock_kline'

# ActiveRecord 风格
klines = StockKline.select().where(StockKline.id == '000001.SZ')
kline = StockKline.get(StockKline.id == '000001.SZ')
```

**优点**：
- ✅ 轻量级 ORM
- ✅ API 类似 BaseTableModel
- ✅ 自带连接池

**缺点**：
- ❌ 需要定义 Model 类
- ❌ 增加依赖
- ❌ 学习曲线

---

### 方案 3：如果需要类型安全 - Pydantic + 手写 Repository ⭐⭐⭐⭐

```python
from pydantic import BaseModel

class StockKlineSchema(BaseModel):
    id: str
    date: str
    close: float
    # ...

class StockKlineRepository:
    def __init__(self, db):
        self.db = db
        self.table = 'stock_kline'
    
    def find_by_id(self, stock_id: str) -> List[StockKlineSchema]:
        rows = self.db.select(self.table, where='id = %s', params=[stock_id])
        return [StockKlineSchema(**row) for row in rows]
    
    def save(self, kline: StockKlineSchema):
        self.db.insert(self.table, kline.dict())
```

**优点**：
- ✅ 类型安全（Pydantic 验证）
- ✅ 自动文档生成
- ✅ 灵活性高
- ✅ 符合现代 Python 实践

**缺点**：
- ⚠️ 需要手写 Repository
- ⚠️ 代码量稍多

---

### 方案 4：如果需要查询构建器 - PyPika ⭐⭐⭐⭐

```python
from pypika import Query, Table, Field

stock_kline = Table('stock_kline')

# 类型安全的查询
query = Query.from_(stock_kline).select(
    stock_kline.id,
    stock_kline.date,
    stock_kline.close
).where(
    stock_kline.id == '000001.SZ'
).where(
    stock_kline.date >= '20200101'
).orderby(stock_kline.date)

# 执行
sql = str(query)
records = db.fetch_all(sql)
```

**优点**：
- ✅ 类型安全
- ✅ SQL 注入防护
- ✅ 复杂查询支持
- ✅ 轻量级

**推荐场景**：
- 复杂查询多
- 需要动态组装 SQL

---

## 📊 综合对比

| 方案 | 复杂度 | 依赖 | 类型安全 | 推荐度 | 适用场景 |
|------|--------|------|----------|--------|----------|
| **DatabaseManager** | 低 | 无 | ❌ | ⭐⭐⭐⭐⭐ | 所有场景 |
| **Pydantic + Repo** | 中 | Pydantic | ✅ | ⭐⭐⭐⭐ | 需要类型安全 |
| **PyPika** | 低 | PyPika | ✅ | ⭐⭐⭐⭐ | 复杂查询多 |
| **Peewee** | 中 | Peewee | ✅ | ⭐⭐⭐ | 喜欢 ORM 风格 |

---

## 🎯 我的最终建议

### 短期（立即）：直接用 DatabaseManager ✅

**理由**：
1. 已经提供了所有需要的功能
2. 无额外依赖
3. 性能最好
4. 最灵活

**实施**：
```python
# 所有 Loader 直接使用 db.select(), db.insert() 等
class KlineLoader:
    def load_kline(self, stock_id, start_date, end_date):
        return self.db.select(
            'stock_kline',
            where='id = %s AND date BETWEEN %s AND %s',
            params=[stock_id, start_date, end_date],
            order_by='date ASC'
        )
```

---

### 中期（1-2月）：可选添加 PyPika ✅

如果你发现有很多复杂查询，可以引入 PyPika：

```bash
pip install pypika
```

```python
# 复杂查询场景
from pypika import Query, Table

stock_kline = Table('stock_kline')
query = Query.from_(stock_kline).select('*') \
    .where(stock_kline.id == stock_id) \
    .where(stock_kline.date.between(start_date, end_date)) \
    .orderby(stock_kline.date)

records = db.fetch_all(str(query))
```

---

### 长期（3-6月）：考虑 Pydantic ✅

如果项目变大，团队人多，可以考虑引入类型安全：

```python
from pydantic import BaseModel
from datetime import date

class KlineSchema(BaseModel):
    id: str
    date: str
    open: float
    close: float
    # 自动类型验证和转换
```

---

## 🚀 实施建议

### 立即行动
1. ✅ 继续使用 DatabaseManager 的 CRUD 方法
2. ✅ 逐步迁移 Loader 中的 model 调用
3. ✅ 删除 BaseTableModel 和 tables/*/model.py

### 不要做的事
- ❌ 不要引入重型 ORM（SQLAlchemy ORM）
- ❌ 不要过度设计（YAGNI 原则）
- ❌ 不要重复造轮子（DatabaseManager 已够用）

---

## 💡 关键洞察

**BaseTableModel 其实只是 DatabaseManager 的简单封装**

```python
# BaseTableModel.load() 本质是：
def load(self, condition, params):
    return self.db.execute_sync_query(
        f"SELECT * FROM {self.table_name} WHERE {condition}",
        params
    )

# 这和直接调用 DatabaseManager 没有本质区别：
db.select(table_name, where=condition, params=params)
```

**结论**：不需要额外的库，你的 `DatabaseManager` 完全够用！

---

## 🎉 最终推荐

**我的建议是：不使用任何额外的库**

理由：
1. ✅ DatabaseManager 功能完整
2. ✅ 保持简洁
3. ✅ 性能最优
4. ✅ 无学习成本
5. ✅ 易于维护

如果未来确实需要（比如查询变得非常复杂），再考虑引入 **PyPika** 作为查询构建器。

