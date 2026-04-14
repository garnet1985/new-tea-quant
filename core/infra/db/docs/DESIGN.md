# Database 模块设计文档

**版本：** `0.2.0`

本文档描述 `infra.db` 的详细设计；[架构总览](./ARCHITECTURE.md) 负责极简总览，本文件负责子模块拆分与协作细节。

**相关文档**：[架构总览](./ARCHITECTURE.md) · [API](./API.md) · [决策记录](./DECISIONS.md)

---

## 1. 设计原则

- 分层解耦：连接、schema、表操作分开设计。
- 统一入口：外部统一通过 `DatabaseManager` 访问。
- 方言隔离：数据库差异封装在 adapter 层。
- 性能优先：写入支持队列聚合与批量操作。
- 可维护性：核心能力通过 manager 职责划分管理。

---

## 2. 模块结构与职责

### 2.1 `DatabaseManager`

文件：`db_manager.py`

职责：
- 作为模块统一入口暴露公共数据库能力。
- 初始化并编排 `ConnectionManager`、`SchemaManager`、`TableManager`。
- 维护默认实例（`set_default/get_default/reset_default`）。

不负责：
- 不直接管理底层连接池细节。
- 不直接实现 schema SQL 生成逻辑。
- 不直接实现批量队列内部调度。

---

### 2.2 `ConnectionManager`

文件：`connection_management/connection_manager.py`

职责：
- 根据配置创建数据库 adapter。
- 管理连接、事务和游标上下文。
- 提供同步查询执行入口。

不负责：
- 不处理表结构定义。
- 不处理写入队列策略。

---

### 2.3 `SchemaManager`

文件：`schema_management/schema_manager.py`

职责：
- 读取表 schema 元信息。
- 基于数据库方言生成建表与索引 SQL。
- 提供 schema 查询（字段、表定义）能力。

不负责：
- 不管理连接生命周期。
- 不处理业务查询或写入调度。

---

### 2.4 `TableManager`

文件：`table_management/table_manager.py`

职责：
- 统一承载表级读写入口。
- 管理 `BatchWriteQueue` 的延迟初始化与调度。
- 提供直写兜底路径（队列不可用时）。

不负责：
- 不管理数据库连接创建。
- 不管理 schema 解析与建表定义。

---

### 2.5 `DbBaseModel`

文件：`table_queriers/db_base_model.py`

职责：
- 为单表提供通用 CRUD 能力。
- 提供批量 insert/upsert、导入导出等工具化能力。
- 复用 `DatabaseManager` 实现跨表一致的执行方式。

不负责：
- 不承担跨模块业务语义。
- 不替代上层 service/manager 的业务编排。

---

### 2.6 Adapter 层

目录：`table_queriers/adapters/`

职责：
- 封装 PostgreSQL/MySQL 方言差异（占位符、连接、事务、批量执行等）。
- 对上层提供统一 adapter 接口。

核心文件：
- `base_adapter.py`
- `postgresql_adapter.py`
- `mysql_adapter.py`
- `factory.py`

---

### 2.7 批量写入子系统

目录：`table_queriers/services/`

职责：
- `batch_operation.py`：批量 SQL 执行策略。
- `batch_operation_queue.py`：队列聚合与异步刷盘调度。

设计意图：
- 降低高频写入对数据库的连接争用。
- 将大量小写入合并成可控批次。

---

## 3. 关键协作流程

### 3.1 初始化流程

1. `DatabaseManager` 读取配置并实例化三层 manager。
2. `ConnectionManager.initialize()` 创建并连接 adapter。
3. `DatabaseManager` 创建 `TableManager`。
4. `SchemaManager` 使用当前方言完成 schema 相关初始化。

### 3.2 查询流程

1. 调用方进入 `DatabaseManager.execute_sync_query()`。
2. 委托到 `ConnectionManager.execute_sync_query()`。
3. adapter 执行 SQL 并返回统一结构结果。

### 3.3 写入流程（队列）

1. 调用方进入 `DatabaseManager.queue_write()`。
2. 委托 `TableManager.queue_write()`。
3. 队列聚合达到阈值后批量落库。
4. 必要时通过 `flush_writes` / `wait_for_writes` 保障一致性时点。

---

## 4. 边界与扩展点

边界：
- `infra.db` 只提供数据库基础能力，不承载业务逻辑。
- 上层模块负责策略、数据语义和业务编排。

扩展点：
- 新数据库方言：新增 adapter 并更新工厂与校验。
- 写入策略：扩展批量策略与队列参数。
- schema 能力：扩展字段类型与 SQL 生成规则。

---

## 5. 与文档体系关系

- 总览：`docs/ARCHITECTURE.md`
- 接口：`docs/API.md`
- 决策：`docs/DECISIONS.md`
- 元信息：`module_info.yaml`
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
