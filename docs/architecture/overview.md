# 系统架构概览

## 整体架构

Stocks-Py 采用**分层架构**和**模块化设计**，核心原则是：

- **框架与用户空间分离**：`core/` 是框架核心，`userspace/` 是用户代码
- **插件化设计**：策略、数据源、标签都是可插拔的
- **配置驱动**：通过配置文件控制行为，减少硬编码

## 目录结构

```
stocks-py/
├── core/                      # 框架核心
│   ├── modules/              # 业务模块
│   │   ├── strategy/         # 策略框架
│   │   ├── data_manager/     # 数据管理器
│   │   ├── data_source/      # 数据源系统
│   │   ├── tag/              # 标签系统
│   │   └── indicator/        # 技术指标
│   ├── infra/                # 基础设施
│   │   ├── db/               # 数据库管理
│   │   ├── worker/            # 多进程/多线程工具
│   │   └── project_context/  # 项目管理
│   └── config/               # 系统配置
├── userspace/                 # 用户空间
│   ├── strategies/           # 用户策略
│   ├── data_source/          # 用户数据源
│   ├── tags/                 # 用户标签场景
│   └── config/               # 用户配置
└── docs/                      # 文档中心
```

## 文档分层结构

当前架构文档按两类模块组织：

- **Infra（基础设施层）**：`db`、`worker`、`project_context`、`config`、`discovery`
- **Core Modules（核心业务模块）**：`strategy`、`data_manager`、`data_source`、`indicator`、`tag`、`adapter`

后续各模块的 `overview.md` / `architecture.md` / `decisions.md` 会分别归档在：

- `docs/architecture/infra/<module>/...`
- `docs/architecture/core_modules/<module>/...`

---

## 核心模块

### 1. Strategy（策略框架）

**三层回测架构**：
- **Opportunity Enumerator**：机会枚举器，扫描全市场
- **Price Factor Simulator**：价格因子模拟器，评估信号质量
- **Capital Allocation Simulator**：资金分配模拟器，真实资金约束回测

**设计特点**：
- 版本管理，支持多轮结果对比
- 多进程并行，高效处理大量股票
- 配置驱动，灵活的策略配置

详细文档：[Strategy 框架架构](strategy_architecture.md)

### 2. DataManager（数据管理器）

**Facade + Service 架构**：
- **Facade 层**：`DataManager` 提供统一入口
- **Service 层**：领域特定的数据服务（Stock、Macro、Calendar）
- **Model 层**：数据库表操作模型

**设计特点**：
- 职责分离，清晰的层次结构
- 领域驱动，按业务领域组织服务
- 统一接口，简化数据访问

详细文档：
- [DataManager 架构](data_manager_architecture.md) - 整体架构
- [Data Services 架构](data_services_architecture.md) - 数据服务层详细设计

### 3. DataSource（数据源系统）

**Handler + Provider 架构**：
- **Handler**：数据获取处理器，定义数据获取逻辑
- **Provider**：第三方数据源封装（Tushare、AKShare等）
- **配置驱动**：通过 mapping.json 配置数据源

**设计特点**：
- 易于扩展，新增数据源只需实现 Handler 和 Provider
- 多数据源支持，可切换数据源
- 异步处理，支持并发数据获取

详细文档：[DataSource 架构](data_source_architecture.md)

### 4. Tag（标签系统）

**Scenario + Tag 三层架构**：
- **Scenario**：标签场景，定义标签计算逻辑
- **Tag Definition**：标签定义，元数据
- **Tag Value**：标签值，实际计算结果

**设计特点**：
- 配置驱动，通过配置文件定义标签
- 多进程并行，高效计算大量标签
- 版本管理，支持标签值的历史追踪

详细文档：[Tag 系统架构](tag_architecture.md)

## 基础设施

### Database（数据库）

- 支持 PostgreSQL、MySQL、SQLite
- 连接池管理
- 批量写入优化
- Schema 管理

详细文档：
- [数据库架构](db_architecture.md) - 数据库管理设计
- [数据库 README](../../core/infra/db/README.md) - 使用指南

### Worker（多进程/多线程）

- 多进程执行器（ProcessWorker）
- 多线程执行器（MultiThreadWorker）
- 内存感知调度器
- 任务队列管理

详细文档：
- [Worker 系统架构](worker_architecture.md) - 多进程/多线程工具设计
- [Worker README](../../core/infra/worker/README.md) - 使用指南

### Project Context（项目管理）

- 路径管理（PathManager）
- 文件管理（FileManager）
- 配置管理（ConfigManager）

详细文档：[Project Context 架构](project_context_architecture.md) - 路径、文件、配置管理

## 数据流

### 策略回测流程

```
1. 数据更新 (DataSource)
   ↓
2. 机会枚举 (OpportunityEnumerator)
   ↓
3. 价格因子模拟 (PriceFactorSimulator)
   ↓
4. 资金分配模拟 (CapitalAllocationSimulator)
   ↓
5. 结果分析
```

### 数据获取流程

```
1. Handler.fetch() - 生成任务
   ↓
2. Provider 调用 - 获取原始数据
   ↓
3. Handler.normalize() - 标准化数据
   ↓
4. 保存到数据库 (DataManager)
```

## 设计原则

1. **关注点分离**：每个模块职责单一，边界清晰
2. **配置驱动**：通过配置控制行为，减少硬编码
3. **易于扩展**：插件化设计，易于添加新功能
4. **性能优化**：多进程并行，批量操作，连接池
5. **版本管理**：支持多轮结果对比，便于迭代优化

## 详细架构文档

深入了解各模块的详细架构设计：

- [DataManager 架构](data_manager_architecture.md) - Facade + Service 架构设计
- [Strategy 框架架构](strategy_architecture.md) - 三层回测架构设计
- [DataSource 架构](data_source_architecture.md) - Handler + Provider 架构设计
- [Tag 系统架构](tag_architecture.md) - Scenario + Tag 三层架构

## 基础设施架构

- [数据库架构](db_architecture.md) - 数据库管理设计
- [Worker 系统架构](worker_architecture.md) - 多进程/多线程工具设计
- [Project Context 架构](project_context_architecture.md) - 路径、文件、配置管理
- [配置系统架构](config_architecture.md) - 配置管理设计
- [Discovery 架构](discovery_architecture.md) - 模块和类发现机制
- [Data Services 架构](data_services_architecture.md) - 数据服务层设计

## 相关文档

- [用户指南](../../user-guide/) - 使用指南
- [API 参考](../api-reference/) - API 文档
- [开发文档](../development/) - 开发相关文档
