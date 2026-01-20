# Database 架构文档

**版本：** 3.0  
**最后更新**: 2026-01-17

---

## 📋 目录

1. [设计目标](#设计目标)
2. [设计理念](#设计理念)
3. [核心组件详解](#核心组件详解)
4. [架构图](#架构图)
5. [运行时 Workflow](#运行时-workflow)
6. [未来扩展方向](#未来扩展方向)

---

## 设计目标

### 业务目标

为整个系统提供统一的数据库基础设施层，支持多种数据库后端，同时保持 API 的简洁性和一致性。

1. **多数据库支持**：通过适配器模式支持 PostgreSQL、MySQL、SQLite
2. **性能优先**：使用连接池、批量操作、直接 SQL（无 ORM 开销）
3. **多进程安全**：支持多进程场景下的自动初始化和只读模式
4. **使用简单**：90% 的场景不需要显式传递数据库实例
5. **类型安全**：参数化查询，防止 SQL 注入

### 设计目标

基于上述业务目标，我们制定了以下技术设计目标：

1. **多数据库支持**：通过适配器模式支持 PostgreSQL、MySQL、SQLite
2. **性能优化**：连接池、批量操作、直接 SQL（无 ORM 开销）
3. **多进程安全**：默认实例机制，支持多进程场景下的自动初始化
4. **使用简单**：默认实例机制，90% 的场景不需要显式传递数据库实例
5. **类型安全**：参数化查询，防止 SQL 注入
6. **职责清晰**：三层架构，每个管理器只负责一个明确的功能

---

## 设计理念

### 核心原则

1. **适配器模式**：通过适配器抽象不同数据库的差异，提供统一的接口
2. **直接 SQL**：不使用 ORM，直接使用 SQL，减少抽象层开销
3. **默认实例机制**：提供全局默认实例，简化使用，支持多进程场景
4. **职责分离**：三层架构，ConnectionManager、SchemaManager、TableManager 各司其职
5. **性能优先**：连接池、批量操作、Schema 缓存等性能优化

### 分层架构

为了实现上述业务目标，我们设计了分层的数据获取架构：

- **DatabaseManager（协调层）**：协调三个管理器，提供统一的外部 API，管理默认实例
- **ConnectionManager（连接层）**：连接和事务管理，查询执行
- **SchemaManager（Schema 层）**：Schema 管理和表初始化
- **TableManager（表操作层）**：表操作 API，批量写入队列管理

---

## 核心组件详解

Database 模块采用三层架构，每层负责不同的职责：

### ConnectionManager 层（连接管理）

**职责**：

- ✅ **负责**：
  - **数据库适配器创建和初始化**：根据配置创建对应的数据库适配器
  - **连接获取和释放**：管理数据库连接的获取和释放（连接池或单连接）
  - **事务管理**：提供事务接口，支持自动提交和回滚
  - **游标管理**：管理数据库游标的创建和释放
  - **查询执行**：执行 SQL 查询，统一结果格式（字典列表）
- ❌ **不负责**：
  - 不负责 Schema 管理（Schema 管理由 SchemaManager 负责）
  - 不负责表操作 API（表操作由 TableManager 负责）
  - 不负责批量写入队列（批量写入队列由 TableManager 负责）

**组件**：
- **ConnectionManager**：连接管理器，管理数据库连接和事务
- **DatabaseAdapter**：数据库适配器（PostgreSQLAdapter、MySQLAdapter、SQLiteAdapter）

**特点**：
- 适配器模式，统一不同数据库的接口
- 连接池管理（PostgreSQL/MySQL）或单连接（SQLite）
- 参数化查询，防止 SQL 注入

### SchemaManager 层（Schema 管理）

**职责**：

- ✅ **负责**：
  - **从文件系统加载 schema.json**：扫描并加载表结构定义
  - **根据 schema 生成 CREATE TABLE SQL**：根据数据库类型生成对应的 SQL
  - **创建表和索引**：执行 CREATE TABLE 和 CREATE INDEX 语句
  - **Schema 查询和缓存**：提供 Schema 查询接口，缓存已加载的 Schema
- ❌ **不负责**：
  - 不负责连接管理（连接管理由 ConnectionManager 负责）
  - 不负责表操作 API（表操作由 TableManager 负责）
  - 不负责业务逻辑（业务逻辑由上层模块负责）

**组件**：
- **SchemaManager**：Schema 管理器，负责表结构的管理
- **Field Types**：字段类型定义（StringField、IntField、DateField 等）

**特点**：
- 声明式：使用 JSON Schema 定义表结构
- 多数据库适配：根据数据库类型生成对应的 SQL
- 缓存机制：已加载的 Schema 会被缓存

### TableManager 层（表操作）

**职责**：

- ✅ **负责**：
  - **查询执行**：委托给 ConnectionManager 执行查询
  - **批量写入队列管理**：收集多线程的写入请求，批量执行
  - **直接写入**：提供直接写入接口（兜底方案）
- ❌ **不负责**：
  - 不负责连接管理（连接管理由 ConnectionManager 负责）
  - 不负责 Schema 管理（Schema 管理由 SchemaManager 负责）
  - 不负责业务逻辑（业务逻辑由上层模块负责）

**组件**：
- **TableManager**：表管理器，负责表操作 API
- **BatchWriteQueue**：批量写入队列，解决并发写入问题

**特点**：
- 批量写入队列：收集请求后批量写入，避免锁冲突
- 单线程执行写入，保证线程安全

### DatabaseManager 层（协调层）

**职责**：

- ✅ **负责**：
  - **协调三个管理器**：协调 ConnectionManager、SchemaManager、TableManager
  - **提供统一的外部 API**：对外暴露统一的数据库访问接口
  - **管理默认实例**：支持全局默认实例，简化使用，支持多进程场景
  - **初始化管理**：管理数据库初始化流程
- ❌ **不负责**：
  - 不包含具体的连接管理逻辑（由 ConnectionManager 负责）
  - 不包含具体的 Schema 管理逻辑（由 SchemaManager 负责）
  - 不包含具体的表操作逻辑（由 TableManager 负责）

**组件**：
- **DatabaseManager**：数据库管理器，协调所有子管理器

**特点**：
- 单一职责：只负责协调，具体功能由三个管理器实现
- 默认实例机制：支持多进程场景下的自动初始化
- 事务支持：提供上下文管理器接口

### 其他核心组件

**DbBaseModel（表操作基类）**：
- 单表 CRUD 封装
- 时序数据查询优化（通过 TimeSeriesHelper）
- DataFrame 支持（通过 DataFrameHelper）
- 批量操作
- 所有基础表的 Model 类都继承自此类

**DatabaseAdapter（数据库适配器）**：
- 抹平不同数据库之间的差异
- 占位符转换：PostgreSQL/MySQL 使用 `%s`，SQLite 使用 `?`
- 连接管理：PostgreSQL/MySQL 使用连接池，SQLite 使用单连接
- 结果格式：统一转换为字典列表

---

## 架构图

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│              Database 系统架构                            │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────────────────────────────┐          │
│  │  DatabaseManager (协调层)                  │          │
│  │  - 协调三个管理器                           │          │
│  │  - 提供统一的外部 API                       │          │
│  │  - 管理默认实例                             │          │
│  └──────────────────────────────────────────┘          │
│           │                                              │
│           ├─▶ ConnectionManager (连接层)                  │
│           │   └── DatabaseAdapter (数据库适配器)        │
│           │       ├── PostgreSQLAdapter                  │
│           │       ├── MySQLAdapter                       │
│           │       └── SQLiteAdapter                      │
│           │                                              │
│           ├─▶ SchemaManager (Schema 层)                  │
│           │   └── Field Types (字段类型定义)             │
│           │                                              │
│           └─▶ TableManager (表操作层)                    │
│               └── BatchWriteQueue (批量写入队列)        │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### 三层架构说明

1. **DatabaseManager（协调层）**
   - 协调三个管理器
   - 提供统一的外部 API
   - 管理默认实例（多进程支持）

2. **ConnectionManager（连接层）**
   - 数据库适配器创建和初始化
   - 连接获取和释放（连接池或单连接）
   - 事务管理
   - 查询执行

3. **SchemaManager（Schema 层）**
   - 从文件系统加载 schema.json
   - 根据 schema 生成 CREATE TABLE SQL
   - 创建表和索引

4. **TableManager（表操作层）**
   - 查询执行（委托给 ConnectionManager）
   - 批量写入队列管理
   - 直接写入（兜底方案）

---

## 运行时 Workflow

### 初始化流程

```
1. DatabaseManager.__init__() 被调用
   │
   ├─▶ 2. 加载配置
   │      - 从 ConfigManager 获取数据库配置
   │      - 解析和验证配置
   │
   ├─▶ 3. 初始化 ConnectionManager
   │      - 创建数据库适配器（根据 database_type）
   │      - 初始化连接池（PostgreSQL/MySQL）或单连接（SQLite）
   │
   ├─▶ 4. 初始化 SchemaManager
   │      - 设置数据库类型
   │
   ├─▶ 5. 初始化 TableManager（延迟初始化）
   │      - 需要 adapter，延迟到 initialize() 时初始化
   │
   └─▶ 6. DatabaseManager.initialize() 被调用
          │
          ├─▶ 7. 初始化 TableManager
          │      - 创建 TableManager 实例（传入 adapter）
          │
          ├─▶ 8. SchemaManager 创建所有表
          │      - 扫描 base_tables/ 目录
          │      - 加载 schema.json
          │      - 生成 CREATE TABLE SQL
          │      - 执行创建表和索引
          │
          └─▶ 9. 初始化完成，可以使用
```

### 查询流程

```
1. 用户调用 db.execute_sync_query(sql, params)
   │
   ├─▶ 2. DatabaseManager 路由到 ConnectionManager
   │      - db.execute_sync_query() → connection_manager.execute_sync_query()
   │
   ├─▶ 3. ConnectionManager 获取连接
   │      - 从连接池获取连接（PostgreSQL/MySQL）
   │      - 或使用单连接（SQLite）
   │
   ├─▶ 4. DatabaseAdapter 执行查询
   │      - 转换占位符（PostgreSQL/MySQL: %s, SQLite: ?）
   │      - 执行 SQL 查询
   │      - 获取原始结果
   │
   ├─▶ 5. DatabaseAdapter 转换结果格式
   │      - 将原始结果转换为字典列表
   │      - 统一字段名格式
   │
   ├─▶ 6. ConnectionManager 归还连接
   │      - 归还连接到连接池（PostgreSQL/MySQL）
   │
   └─▶ 7. 返回结果给用户
```

### 写入流程（批量写入队列）

```
1. 用户调用 db.queue_write(table_name, data_list, unique_keys)
   │
   ├─▶ 2. DatabaseManager 路由到 TableManager
   │      - db.queue_write() → table_manager.queue_write()
   │
   ├─▶ 3. TableManager 添加到批量写入队列
   │      - BatchWriteQueue 收集写入请求
   │      - 检查是否达到阈值（batch_size）或超时（flush_interval）
   │
   ├─▶ 4. 达到阈值/超时，触发批量写入
   │      - BatchOperation.execute_batch_insert()
   │      - 构建批量插入 SQL
   │
   ├─▶ 5. ConnectionManager 执行批量写入
   │      - 获取连接
   │      - 执行批量插入/更新
   │      - 归还连接
   │
   └─▶ 6. 写入完成
```

---

## 未来扩展方向

> **说明**：以下扩展方向分为两类：
> - **待实现扩展（单机版支持）**：可以在单机版中实现的功能
> - **可扩展方向（单机版不支持）**：需要分布式架构支持的功能，当前单机版不支持

### 待实现扩展（单机版支持）

#### 1. 连接池优化

**目标**：优化连接池的性能和可靠性

**实现方向**：
- 动态调整连接池大小
- 连接健康检查
- 连接泄漏检测

**相关文档**：参考 [Road Map](../development/road-map.md)

#### 2. 查询缓存

**目标**：缓存常用查询结果，提高性能

**实现方向**：
- 缓存常用查询结果
- 缓存失效策略
- 缓存命中率监控

**相关文档**：参考 [Road Map](../development/road-map.md)

---

### 可扩展方向（单机版不支持）

> **注意**：以下功能需要分布式架构支持，当前单机版不支持。如需实现，需要先升级架构。

#### 1. 读写分离

**目标**：支持主从数据库，提高性能

**实现方向**：
- 支持主从数据库配置
- 自动路由读写请求
- 主从同步监控

**相关文档**：参考 [Road Map](../development/road-map.md)

#### 2. 异步支持

**目标**：支持异步查询和写入

**实现方向**：
- 异步查询接口
- 异步批量写入
- 异步事务支持

**相关文档**：参考 [Road Map](../development/road-map.md)

---

## 相关文档

- **[overview.md](./overview.md)**：模块概览
- **[decisions.md](./decisions.md)**：重要决策记录

> **提示**：本文档描述了 Database 的架构设计。如需了解设计决策的背景和理由，请参考 [decisions.md](./decisions.md)。

---

**文档结束**
