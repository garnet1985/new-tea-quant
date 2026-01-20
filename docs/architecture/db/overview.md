# Database 模块概览

> **提示**：本文档提供快速上手指南。如需了解详细的设计理念、架构设计和决策记录，请参考 [architecture.md](./architecture.md) 和 [decisions.md](./decisions.md)。

## 📋 模块简介

Database 模块是项目的数据库基础设施层，提供统一的数据库访问接口，支持 PostgreSQL、MySQL 和 SQLite。

**核心特性**：
- 多数据库支持：通过适配器模式支持 PostgreSQL、MySQL、SQLite
- 性能优先：使用连接池、批量操作、直接 SQL（无 ORM 开销）
- 多进程安全：支持多进程场景下的自动初始化和只读模式
- 使用简单：90% 的场景不需要显式传递数据库实例
- 类型安全：参数化查询，防止 SQL 注入

**与 DataManager 的关系**：
- `db` 模块是基础设施层，提供底层数据库访问能力
- `data_manager` 模块是应用层，使用 `db` 模块提供业务数据访问服务
- `DataManager` 持有和管理 `DatabaseManager`（`db` 模块的核心类）

> 详细的设计理念和架构说明请参考 [architecture.md](./architecture.md)

## 📦 模块的组件

```
DatabaseManager (协调层)
    │
    ├── ConnectionManager (连接管理)
    │       └── DatabaseAdapter (数据库适配器)
    │
    ├── SchemaManager (Schema 管理)
    │       └── Field Types (字段类型定义)
    │
    └── TableManager (表管理)
            └── BatchWriteQueue (批量写入队列)
```

## 📁 模块的文件夹结构

```
core/infra/db/
├── __init__.py
├── db_manager.py                  # DatabaseManager 主类
│
├── connection_management/         # 连接管理
│   └── connection_manager.py      # ConnectionManager
│
├── schema_management/             # Schema 管理
│   ├── schema_manager.py          # SchemaManager
│   └── field/                     # Field 类型定义
│       ├── base.py
│       ├── string.py
│       ├── numeric.py
│       ├── datetime.py
│       ├── boolean.py
│       ├── json.py
│       ├── uuid.py
│       ├── blob.py
│       └── enum.py
│
├── table_management/              # 表管理
│   └── table_manager.py           # TableManager
│
├── table_queriers/                # 表查询器
│   ├── db_base_model.py          # DbBaseModel（表操作基类）
│   ├── query_helpers.py          # 查询辅助工具
│   ├── adapters/                  # 数据库适配器
│   │   ├── base_adapter.py
│   │   ├── factory.py
│   │   ├── postgresql_adapter.py
│   │   ├── mysql_adapter.py
│   │   └── sqlite_adapter.py
│   └── services/                  # 表查询服务
│       ├── batch_operation.py
│       └── batch_operation_queue.py
│
└── helpers/                       # 辅助工具
    └── db_helpers.py
```

## 🚀 模块的使用方法

### 基本使用

```python
from core.infra.db import DatabaseManager

# 初始化
db = DatabaseManager(is_verbose=True)
db.initialize()
DatabaseManager.set_default(db)

# 查询
results = db.execute_sync_query(
    "SELECT * FROM stock_list WHERE id = %s", 
    ('000001.SZ',)
)

# 写入（使用队列，支持批量）
db.queue_write(
    'stock_kline', 
    kline_data_list, 
    unique_keys=['id', 'date']
)

# 事务
with db.transaction() as cursor:
    cursor.execute("INSERT INTO ...")
    cursor.execute("UPDATE ...")
```

### 使用 DbBaseModel

```python
from core.infra.db import DbBaseModel

# 方式 1: 直接使用
model = DbBaseModel('stock_kline', db)
records = model.load("id = %s", ('000001.SZ',))

# 方式 2: 继承使用（推荐）
class StockKlineModel(DbBaseModel):
    def __init__(self, db=None):
        super().__init__('stock_kline', db)
    
    def load_by_date_range(self, stock_id, start_date, end_date):
        return self.load(
            "id = %s AND date BETWEEN %s AND %s",
            (stock_id, start_date, end_date),
            order_by="date ASC"
        )
```

### 核心概念

| 概念 | 作用 | 关键点 |
|------|------|--------|
| **DatabaseManager** | 数据库管理器 | 协调三个管理器，提供统一 API |
| **ConnectionManager** | 连接管理 | 连接池、事务管理、查询执行 |
| **SchemaManager** | Schema 管理 | 从 JSON Schema 生成 SQL，创建表和索引 |
| **TableManager** | 表管理 | 批量写入队列管理 |
| **DbBaseModel** | 表操作基类 | 单表 CRUD 封装，所有 Model 继承此类 |
| **DatabaseAdapter** | 数据库适配器 | 抹平不同数据库的差异 |

---

## 📚 模块详细文档

- **[architecture.md](./architecture.md)**：架构文档，包含详细的技术设计、核心组件、运行时 Workflow
- **[decisions.md](./decisions.md)**：重要决策记录，包含架构设计决策和理由

> **阅读建议**：先阅读本文档快速上手，然后阅读 [architecture.md](./architecture.md) 了解详细设计，最后阅读 [decisions.md](./decisions.md) 了解设计决策。

---

**文档结束**
