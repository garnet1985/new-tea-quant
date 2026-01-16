# Database 模块设计文档

## 📋 概述

Database 模块是项目的数据库基础设施层，提供统一的数据库访问接口。设计目标是支持多种数据库后端，同时保持 API 的简洁性和一致性。

## 🎯 设计目标

1. **多数据库支持**：通过适配器模式支持 PostgreSQL、MySQL、SQLite
2. **性能优先**：使用连接池、批量操作、直接 SQL（无 ORM 开销）
3. **多进程安全**：支持多进程场景下的自动初始化和只读模式
4. **使用简单**：90% 的场景不需要显式传递数据库实例
5. **类型安全**：参数化查询，防止 SQL 注入

## 🏗️ 架构设计

### 三层架构

DatabaseManager 采用三层架构，职责清晰分离：

#### 1. ConnectionManager（连接管理）

**职责**：
- 数据库适配器创建和初始化
- 连接获取和释放
- 事务管理
- 游标管理
- 查询执行

**位置**：`connection_management/connection_manager.py`

#### 2. SchemaManager（Schema 管理）

**职责**：
- 从文件系统加载 schema.json
- 根据 schema 生成 CREATE TABLE SQL
- 创建表和索引
- 管理策略自定义表的注册
- Schema 查询和缓存

**位置**：`schema_management/schema_manager.py`

#### 3. TableManager（表管理）

**职责**：
- 查询执行（委托给 ConnectionManager）
- 批量写入队列管理
- 直接写入（兜底方案）

**位置**：`table_management/table_manager.py`

### 核心组件

#### DatabaseManager（数据库管理器）

**职责**：
- 协调三个管理器
- 提供统一的外部 API
- 管理默认实例（多进程支持）

**设计原则**：
- 单一职责：只负责协调，具体功能由三个管理器实现
- 适配器模式：通过适配器抽象不同数据库的差异
- 默认实例：支持全局单例，简化使用

**关键特性**：
- 默认实例机制：支持多进程场景下的自动初始化
- 批量写入队列：解决并发写入问题
- 事务支持：提供上下文管理器接口

#### 适配器系统

**设计模式**：适配器模式（Adapter Pattern）

**目的**：抹平不同数据库之间的差异，提供统一的接口

**核心适配点**：
- 占位符转换：PostgreSQL/MySQL 使用 `%s`，SQLite 使用 `?`
- 连接管理：PostgreSQL/MySQL 使用连接池，SQLite 使用单连接
- 结果格式：统一转换为字典列表
- 事务处理：统一接口，隐藏实现差异

**适配器层次**：
```
BaseDatabaseAdapter（抽象基类）
├── PostgreSQLAdapter（PostgreSQL 适配器）
├── MySQLAdapter（MySQL 适配器）
└── SQLiteAdapter（SQLite 适配器）
```

**工厂模式**：`DatabaseAdapterFactory` 根据配置自动创建对应的适配器

#### DbBaseModel（表操作基类）

**职责**：
- 单表 CRUD 封装
- 时序数据查询优化（通过 TimeSeriesHelper）
- DataFrame 支持（通过 DataFrameHelper）
- 批量操作

**设计原则**：
- 纯工具类：不涉及业务逻辑
- 自动获取 db：支持默认实例机制
- 性能优先：直接 SQL，无 ORM 开销

**使用场景**：
- 所有基础表的 Model 类都继承自此类
- 由 DataManager 和 DataService 内部使用
- 外部代码应通过 DataManager 访问数据

#### Schema 管理器

**职责**：
- 从 JSON Schema 文件加载表定义
- 根据数据库类型生成对应的 SQL
- 创建表和索引

**设计原则**：
- 声明式：使用 JSON Schema 定义表结构
- 多数据库适配：根据数据库类型生成对应的 SQL
- 缓存机制：已加载的 Schema 会被缓存

#### 批量写入队列

**设计目的**：解决数据库并发写入问题

**工作原理**：
- 收集多线程的写入请求
- 达到阈值（batch_size）或超时（flush_interval）后批量写入
- 单线程执行写入，避免锁冲突

**适用场景**：
- 多线程并发写入
- 大量数据批量插入
- 需要控制写入频率的场景

## 🔄 数据流

### 查询流程

```
业务代码
  ↓
DatabaseManager.execute_sync_query()
  ↓
ConnectionManager.execute_sync_query()
  ↓
Adapter.execute_query()
  ↓
数据库连接（连接池/单连接）
  ↓
执行 SQL
  ↓
结果格式转换（统一为字典列表）
  ↓
返回结果
```

### 写入流程

```
业务代码
  ↓
DatabaseManager.queue_write()
  ↓
TableManager.queue_write()
  ↓
BatchWriteQueue（收集请求）
  ↓
达到阈值/超时
  ↓
BatchOperation.execute_batch_insert()
  ↓
Adapter.execute_batch()
  ↓
数据库连接
  ↓
执行批量插入/更新
```

## 🎨 设计模式

### 1. 适配器模式（Adapter Pattern）

**目的**：统一不同数据库的接口

**实现**：
- `BaseDatabaseAdapter` 定义统一接口
- 各数据库适配器实现具体逻辑
- `DatabaseAdapterFactory` 负责创建适配器

### 2. 工厂模式（Factory Pattern）

**目的**：根据配置自动创建对应的适配器

**实现**：`DatabaseAdapterFactory.create()` 根据 `database_type` 创建适配器

### 3. 单例模式（Singleton Pattern）

**目的**：提供全局默认实例，简化使用

**实现**：
- `DatabaseManager._default_instance` 存储默认实例
- `set_default()` / `get_default()` 管理默认实例
- 支持多进程场景下的自动初始化

### 4. 策略模式（Strategy Pattern）

**目的**：根据数据库类型选择不同的 SQL 生成策略

**实现**：`SchemaManager` 根据 `database_type` 生成对应的 SQL

## 🔐 安全性设计

### 1. 参数化查询

所有查询都使用参数化查询，防止 SQL 注入：

```python
# ✅ 正确：使用参数化查询
db.execute_sync_query(
    "SELECT * FROM table WHERE id = %s",
    ('000001.SZ',)
)

# ❌ 错误：字符串拼接
db.execute_sync_query(
    f"SELECT * FROM table WHERE id = '{stock_id}'"
)
```

### 2. 连接池管理

PostgreSQL 和 MySQL 使用连接池，避免连接泄露：
- 自动获取和归还连接
- 连接超时处理
- 连接池大小限制

### 3. 事务隔离

提供事务接口，保证数据一致性：
- 自动提交和回滚
- 上下文管理器确保资源释放

## ⚡ 性能优化

### 1. 连接池

PostgreSQL 和 MySQL 使用连接池，减少连接创建开销。

### 2. 批量操作

- 批量插入：使用 `BatchOperation.execute_batch_insert()` 批量执行
- 批量写入队列：收集请求后批量写入

### 3. 直接 SQL

不使用 ORM，直接使用 SQL，减少抽象层开销。

### 4. Schema 缓存

已加载的 Schema 会被缓存，避免重复加载。

## 🔄 多进程支持

### 设计考虑

在多进程场景下，每个进程有独立的内存空间，无法共享数据库连接。

### 解决方案

1. **默认实例机制**：
   - 主进程初始化并设置默认实例
   - 子进程检测到默认实例不存在时，自动创建只读实例

2. **只读模式**：
   - 子进程自动使用只读模式（SQLite 支持）
   - 避免写锁冲突

3. **自动初始化**：
   - 子进程自动检测并重新初始化
   - 无需手动传递数据库实例

## 📦 模块职责划分

### core/infra/db（基础设施层）

- `DatabaseManager`：协调三个管理器，提供统一 API
- `ConnectionManager`：连接和事务管理
- `SchemaManager`：Schema 管理和表初始化
- `TableManager`：表操作 API
- `DbBaseModel`：表操作工具类
- `table_queryers/adapters/`：数据库适配器
- `helpers/`：辅助工具（静态方法）

### core/modules/data_manager（业务层）

- `DataManager`：数据访问总入口
- `DataService`：数据服务层（跨表查询）
- `base_tables/*/model.py`：具体表的 Model 类（继承 DbBaseModel）

**职责划分**：
- 基础设施层：提供通用工具，不涉及业务逻辑
- 业务层：封装业务逻辑，使用基础设施层提供的工具

## 🔮 未来扩展

### 1. 连接池优化

- 动态调整连接池大小
- 连接健康检查
- 连接泄漏检测

### 2. 查询缓存

- 缓存常用查询结果
- 缓存失效策略

### 3. 读写分离

- 支持主从数据库
- 自动路由读写请求

### 4. 异步支持

- 异步查询接口
- 异步批量写入

## 📝 设计决策记录

### 为什么使用适配器模式而不是 ORM？

**决策**：不使用 ORM，直接使用 SQL

**原因**：
1. 性能优先：直接 SQL 减少抽象层开销
2. 灵活性：可以优化特定查询
3. 简单性：减少学习成本和维护成本

### 为什么支持多种数据库？

**决策**：支持 PostgreSQL、MySQL、SQLite

**原因**：
1. 开发环境：SQLite 便于本地开发
2. 生产环境：PostgreSQL 支持多进程并发读
3. 兼容性：MySQL 兼容现有系统

### 为什么使用默认实例机制？

**决策**：提供全局默认实例

**原因**：
1. 简化使用：90% 的场景不需要显式传递 db
2. 多进程支持：子进程自动初始化
3. 向后兼容：保持现有代码可用

### 为什么采用三层架构？

**决策**：将 DatabaseManager 拆分为三个管理器

**原因**：
1. 职责清晰：每个管理器只负责一个明确的功能
2. 易于测试：每个管理器可以独立测试
3. 易于扩展：可以独立扩展某个管理器
