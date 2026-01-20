# DataManager 架构文档

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

### 解决的问题

为整个框架提供一套底层基础数据支持模块，包括连接数据库，表管理，数据IO，多数据库支持等等。

1. **声明式数据库结构**：通过编写一个schema.json文件轻松完成建表，可以随时查看定义，技术门槛较低
2. **自动创建和管理表**：完整的表结构声明可以在app启动时自动检查并创建表，无需底层操作
3. **多数据库的支持**：底层解析SQL语句，自动抹除不同数据库之间的语法差异
4. **性能加强**：提供单例模式和可复用链接池，支持批量插入防止链接池耗尽或者IO瓶颈
5. **清晰的分层结构**：Manager负责高层调度，Service负责跨表提供业务数据，Model负责单表操作

---

## 设计理念

### 核心原则

1. **Facade 模式**：`DataManager` 作为薄门面层，仅负责单例管理、数据库初始化和服务入口暴露，不包含业务逻辑
2. **职责分离**：每个服务专注于特定领域，严格遵循单一职责原则，不提供跨服务的便捷委托方法
3. **明确性优先**：遵循 Python "Explicit is better than implicit" 原则，通过嵌套属性访问明确指定服务路径
4. **封装性保证**：底层 Model 类完全私有化，外部代码只能通过 DataService 层访问数据
5. **性能优化**：优先使用 SQL JOIN 查询减少数据库访问次数，在数据库层面完成过滤和关联

### 分层架构

为了解决上述问题，我们设计了分层的数据访问架构：

- **Manager（Facade）层**：提供统一入口，管理生命周期
- **Service（Coordinator） 层**：协调跨服务请求
- **Model 层**：底层数据表操作，完全封装

---

## 核心组件详解

### 1. 底层：Schema + Model 声明

**职责**：

**Schema（schema.json）**：
- ✅ **负责**：
  - 声明式定义表结构（字段、类型、主键、索引）
  - 提供表结构的可读性定义（JSON 格式，技术门槛低）
  - 支持自动建表（系统启动时根据 Schema 创建表）
- ❌ **不负责**：
  - 不包含业务逻辑
  - 不处理数据验证（仅定义结构）
  - 不处理数据转换

**Model（如 StockKlineModel）**：
- ✅ **负责**：
  - 封装单表的 CRUD 操作（`load()`, `save()`, `delete()`, `update()`, `replace()`）
  - 封装表特定的业务查询方法（如 `load_by_date_range()`, `load_latest()`）
  - 继承自 `DbBaseModel` 获得通用能力（批量操作、分页查询、时序数据优化等）
  - 自动加载对应的 Schema 定义
- ❌ **不负责**：
  - 不负责跨表查询（跨表查询由 Service 层负责）
  - 不包含业务逻辑（只提供数据访问能力）
  - 不处理数据格式转换（日期格式转换等由 Service 层负责）
  - 不对外暴露（Model 是私有实现，外部代码通过 Service 层访问）

**类关系**：
```
DbBaseModel (基础设施层)
    ↑ 继承
StockKlineModel, StockListModel, GdpModel, ... (业务层)
```

**为什么 Model 需要继承 DbBaseModel？**

1. **通用 CRUD 能力**：`DbBaseModel` 提供了所有表通用的操作
   - 基础 CRUD（增删改查）
   - 批量操作
   - 分页查询
   - 时序数据查询优化

2. **Schema 自动加载**：`DbBaseModel` 自动加载对应的 `schema.json`
   - 在 `__init__` 中调用 `load_schema()`
   - 使用 `SchemaManager` 统一加载逻辑
   - 支持表结构验证

3. **数据库适配**：`DbBaseModel` 通过 `DatabaseManager` 适配不同数据库
   - 自动处理占位符差异（PostgreSQL/MySQL 使用 `%s`，SQLite 使用 `?`）
   - 统一的结果格式（字典列表）
   - 连接池管理

4. **性能优化**：`DbBaseModel` 提供了性能优化功能
   - 批量写入队列
   - 查询结果缓存（可选）
   - 参数化查询（防 SQL 注入）

**使用方式**：

**创建一个新表（冷启动）**：
1. 创建表目录（如 `base_tables/new_table/`）
2. 创建 `schema.json` 文件，定义表结构
3. 创建 `model.py` 文件，定义 Model 类（继承 `DbBaseModel`）
4. 系统启动时自动发现并注册（无需手动配置）

**创建一个新表（热启动）**：
```python
# 使用 register_table() 方法动态注册
data_mgr.register_table('path/to/table/directory')
```

**未来版本**：
- 发现 schema 和数据表结构不一致时提出提醒
- 创建辅助工具迁移数据表结构

### 2. 协调层：Service

**职责**：

- ✅ **负责**：
  - **业务逻辑封装**：封装领域特定的业务逻辑，组合多个 Model 完成复杂业务需求
  - **跨表查询**：处理需要查询多个表的业务场景（如 QFQ 前复权需要 K线数据 + 复权因子）
  - **数据转换**：统一处理数据格式转换（日期格式 `YYYYMMDD` ↔ `YYYY-MM-DD`、数据类型等）
  - **业务验证**：处理业务规则验证（如日期范围检查、数据完整性验证）
  - **数据组装**：合并多个 Model 的查询结果，组装成业务所需的数据结构
  - **隐藏实现细节**：对外提供简洁的 API，隐藏底层表结构和数据存储方式
  - **SQL 优化**：在 Service 层优化查询（JOIN、WHERE 条件等），减少数据库访问次数
  - **通过 Model 访问数据表**：Service 层可以通过 Model 直接访问数据表（通过 `data_manager.get_table()` 获取 Model 实例）
- ❌ **不负责**：
  - 不负责单表 CRUD（单表操作由 Model 层负责，Service 层作为协调层，专注于跨表操作和业务逻辑）
  - 不提供跨服务的便捷委托方法（每个 Service 专注于自己的领域）
  - 不管理数据库连接和连接池（由 Manager 层负责）
  - 不负责表结构创建和管理（由 Schema + Model 层负责）

**Service vs Model 的职责划分**：

| 职责 | Model | Service |
|------|-------|---------|
| 单表 CRUD | ✅ | ❌ |
| 跨表查询 | ❌ | ✅ |
| 业务逻辑 | ❌ | ✅ |
| 数据转换 | ❌ | ✅ |
| 数据验证 | ✅ 基础验证（字段类型、非空等） | ✅ 业务验证（日期范围、数据完整性等） |
| 数据组装 | ❌ | ✅ |
| SQL 优化 | ❌ | ✅ |
| 隐藏实现细节 | ❌ | ✅ |

**数据原则**：
- **明确性优先**：通过嵌套属性访问明确指定服务路径（如 `data_mgr.stock.kline.load()`）
- **职责分离**：每个 Service 专注于特定领域，不提供跨服务的便捷委托方法
- **封装实现细节**：隐藏底层表结构，外部代码不依赖实现细节

**使用方式**：

**添加新的领域服务**：
1. 在 `data_services/` 目录下创建新的服务目录
2. 实现服务类，继承 `BaseDataService`
3. 在 `DataService` 中注册新服务
4. 通过 `data_mgr.new_service` 访问

**添加新的子服务**：
1. 在现有服务的 `sub_services/` 目录下创建新服务
2. 在父服务中注册子服务
3. 通过 `data_mgr.stock.new_sub_service` 访问


### 3. 管理层：Manager

**职责**：

- ✅ **负责**：
  - **进程级单例管理**：确保整个进程中只有一个 DataManager 实例
  - **数据库初始化**：初始化 DatabaseManager，创建数据库连接池
  - **连接池管理**：管理数据库连接的创建、复用和释放
  - **Schema 自动发现**：扫描 `base_tables/` 目录，自动发现所有 Schema 定义
  - **统一建表**：根据 Schema 定义，统一创建和管理所有基础表
  - **Model 自动发现**：扫描并注册所有继承自 `DbBaseModel` 的 Model 类
  - **Service 创建和管理**：创建 DataService 及其所有子服务实例
  - **统一访问入口**：提供统一的属性访问入口（`data_mgr.stock`, `data_mgr.macro`, `data_mgr.calendar`）
  - **内部 Model 访问**：提供 `get_table()` 方法供内部 Service 使用（不对外暴露）
- ❌ **不负责**：
  - 不包含业务逻辑（所有业务逻辑委托给 Service 层）
  - 不直接操作数据库（通过 Model 层操作）
  - 不处理数据转换和验证（由 Service 层负责）
  - 不管理数据缓存
  - 不处理跨表查询（由 Service 层负责）

---

## 架构图

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│              DataManager 系统架构                         │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────────────────────────────┐          │
│  │  DataManager (Facade)                     │          │
│  │  - 进程级单例管理                          │          │
│  │  - 数据库初始化                            │          │
│  │  - 表模型自动发现                          │          │
│  │  - 服务入口暴露                            │          │
│  └──────────────────────────────────────────┘          │
│           │                                              │
│           ▼                                              │
│  ┌──────────────────────────────────────────┐          │
│  │  DataService (Coordinator)                │          │
│  │  - 管理所有子服务实例                      │          │
│  │  - 跨服务协调方法                          │          │
│  │  - 统一服务访问入口                        │          │
│  └──────────────────────────────────────────┘          │
│           │                                              │
│           ├─▶ StockService                               │
│           │   ├── ListService (股票列表)                 │
│           │   ├── KlineService (K线数据)                 │
│           │   ├── TagDataService (标签系统)              │
│           │   └── CorporateFinanceService (财务数据)     │
│           │                                              │
│           ├─▶ MacroService (宏观经济)                     │
│           │                                              │
│           └─▶ CalendarService (交易日历)                 │
│                                                           │
│           │                                              │
│           ▼                                              │
│  ┌──────────────────────────────────────────┐          │
│  │  BaseTables (Models - 私有)              │          │
│  │  - stock_list, stock_kline, ...          │          │
│  │  - gdp, cpi, shibor, ...                 │          │
│  │  - tag_scenario, tag_definition, ...     │          │
│  └──────────────────────────────────────────┘          │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### 三层架构说明

1. **Manager（Facade）层**
   - 进程级单例管理
   - 数据库初始化和连接池管理
   - Schema 和 Model 自动发现
   - 服务入口暴露（`data_mgr.stock`, `data_mgr.macro`, `data_mgr.calendar`）

2. **Service（Coordinator）层**
   - 管理所有子服务实例
   - 统一服务访问入口
   - 领域服务：`StockService`、`MacroService`、`CalendarService`
   - 子服务：`ListService`、`KlineService`、`TagDataService`、`CorporateFinanceService`

3. **Model 层（私有）**
   - 单表 CRUD 操作
   - 表特定的业务查询方法
   - 完全封装，外部通过 Service 层访问

---

## 运行时 Workflow

### 初始化流程（三层协作）

```
1. 用户创建 DataManager 实例（Manager 层）
   │
   ├─▶ 2. Manager 层：检查单例（进程级）
   │      - 如果已存在，返回现有实例
   │      - 如果不存在，创建新实例
   │
   ├─▶ 3. Manager 层：初始化 DatabaseManager
   │      - 创建连接池
   │      - 初始化数据库连接
   │
   ├─▶ 4. Schema + Model 层：Schema 初始化
   │      │
   │      ├─▶ SchemaManager 扫描 base_tables/ 目录
   │      │      - 查找所有包含 schema.json 的目录
   │      │
   │      ├─▶ 对每个 schema.json：
   │      │      - 读取 JSON 文件
   │      │      - 解析字段、主键、索引定义
   │      │      - 根据数据库类型（PostgreSQL/MySQL/SQLite）生成 SQL
   │      │      - 执行 CREATE TABLE 语句
   │      │      - 创建索引（如果有定义）
   │      │
   │      └─▶ 表创建完成
   │
   ├─▶ 5. Schema + Model 层：Model 自动发现
   │      - 扫描 base_tables/ 目录
   │      - 查找所有继承自 DbBaseModel 的类
   │      - 注册到 DataManager 的内部表映射中
   │
   ├─▶ 6. Service 层：创建 DataService 实例
   │      - 创建 StockService（及其子服务）
   │      - 创建 MacroService
   │      - 创建 CalendarService
   │      - 每个 Service 内部获取对应的 Model 实例
   │
   └─▶ 7. 初始化完成，可以使用
```

**说明**：
- 如果表目录存在但没有 `schema.json`，该表不会被自动创建
- 需要手动创建表或添加 `schema.json` 文件
- 如果 Model 类存在但 Schema 不存在，Model 仍然可以工作（但无法自动创建表）

### 数据访问流程（三层协作）

```
1. 用户调用 data_mgr.stock.kline.load(...)（Manager 层入口）
   │
   ├─▶ 2. Manager 层：路由到 Service 层
   │      - data_mgr.stock → StockService 实例
   │      - stock.kline → KlineService 实例
   │
   ├─▶ 3. Service 层：执行业务逻辑
   │      │
   │      ├─▶ KlineService 获取内部 Model（Schema + Model 层）
   │      │      - self._stock_kline = data_manager.get_table('stock_kline')
   │      │
   │      ├─▶ Service 层：构建查询逻辑
   │      │      - 处理参数（日期格式转换、数据验证等）
   │      │      - 决定需要查询哪些表
   │      │
   │      └─▶ Service 层：调用 Model 层（单表操作）
   │             - klines = self._stock_kline.load_by_date_range(...)
   │
   ├─▶ 4. Schema + Model 层：执行数据库查询
   │      │
   │      ├─▶ Model 调用 DbBaseModel 的 load() 方法
   │      │      - 构建 SQL 查询
   │      │      - 执行查询（通过 DatabaseManager）
   │      │
   │      └─▶ 返回原始数据
   │
   ├─▶ 5. Service 层：数据处理和转换
   │      - 日期格式转换
   │      - 数据类型转换
   │      - 数据过滤（如果需要）
   │      - 跨表数据合并（如果是跨表查询）
   │
   └─▶ 6. Manager 层：返回结果给用户
```

### 跨表查询流程（三层协作示例：QFQ 前复权）

```
1. 用户调用 data_mgr.stock.kline.load_qfq(...)（Manager 层入口）
   │
   ├─▶ 2. Manager 层：路由到 Service 层
   │      - data_mgr.stock.kline → KlineService 实例
   │
   ├─▶ 3. Service 层：组合多个 Model（跨表操作）
   │      │
   │      ├─▶ KlineService 获取多个 Model（Schema + Model 层）
   │      │      - self._stock_kline = data_manager.get_table('stock_kline')
   │      │      - self._adj_factor_event = data_manager.get_table('adj_factor_event')
   │      │
   │      ├─▶ Service 层：调用多个 Model（并行或串行）
   │      │      │
   │      │      ├─▶ Model 层：查询 K线数据
   │      │      │      - klines = self._stock_kline.load_by_date_range(...)
   │      │      │
   │      │      └─▶ Model 层：查询复权因子
   │      │             - adj_factors = self._adj_factor_event.load_by_date_range(...)
   │      │
   │      └─▶ Service 层：数据合并和计算
   │             - 合并 K线数据和复权因子
   │             - 计算前复权价格
   │             - 数据格式转换
   │
   └─▶ 4. Manager 层：返回处理后的结果给用户
```


---
## 未来扩展方向

> **说明**：以下扩展方向分为两类：
> - **待实现扩展（单机版支持）**：可以在单机版中实现的功能
> - **可扩展方向（单机版不支持）**：需要分布式架构支持的功能，当前单机版不支持

### 待实现扩展（单机版支持）

#### 1. 表迁移工具

**目标**：当 schema 发生变动且无法与表结构匹配时，提供迁移支持

**实现方向**：
- 提出警示
- 设计完成数据表扩展和迁移工具
- 引导用户使用内置工具完成迁移

**相关文档**：参考 [Road Map](../development/road-map.md)

---

### 可扩展方向（单机版不支持）

> **注意**：以下功能需要分布式架构支持，当前单机版不支持。如需实现，需要先升级架构。

### 1. 缓存层

**目标**：添加缓存层，减少数据库访问

**实现方向**：
- 在 DataService 层添加缓存装饰器
- 支持内存缓存和 Redis 缓存
- 缓存失效策略（TTL、手动失效）

**相关文档**：参考 [Road Map](../development/road-map.md)

### 2. 查询优化器

**目标**：自动优化查询性能

**实现方向**：
- 分析查询模式，自动选择最优查询策略
- 查询结果缓存
- 批量查询优化

**相关文档**：参考 [Road Map](../development/road-map.md)

### 3. 数据版本管理

**目标**：支持数据版本管理和回滚

**实现方向**：
- 为数据表添加版本字段
- 支持数据快照和恢复
- 数据变更历史追踪

**相关文档**：参考 [Road Map](../development/road-map.md)

### 4. 读写分离

**目标**：支持读写分离，提高性能

**实现方向**：
- 主从数据库配置
- 自动路由读请求到从库
- 写请求路由到主库

**相关文档**：参考 [Road Map](../development/road-map.md)

### 5. 数据访问审计

**目标**：记录数据访问日志，便于审计和调试

**实现方向**：
- 记录所有数据访问操作
- 支持访问日志查询和分析
- 性能监控和告警

**相关文档**：参考 [Road Map](../development/road-map.md)

---

## 相关文档

- **[overview.md](./overview.md)**：模块概览
- **[decisions.md](./decisions.md)**：重要决策记录

> **提示**：本文档描述了 DataManager 的架构设计。如需了解设计决策的背景和理由，请参考 [decisions.md](./decisions.md)。

---

**文档结束**
