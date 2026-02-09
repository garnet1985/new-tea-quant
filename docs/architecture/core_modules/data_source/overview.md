# Data Source 模块概览

<<<<<<< HEAD
> **提示**：本文档提供快速上手指南。如需了解详细的设计理念、架构设计和决策记录，请参考 [architecture.md](./architecture.md) 和 [decisions.md](./decisions.md)。
=======
> **提示**：本文档提供快速上手指南。如需了解详细的设计理念、架构设计和决策记录，请参考 [architecture.md](./architecture.md) 和 [decisions.md](./decisions.md)。**API 级说明（类、方法、参数）**见 [api.md](./api.md)。
>>>>>>> write-doc

## 📋 模块简介

Data Source 模块是一个灵活、简单、强大的数据获取框架，用于统一管理从多个第三方数据源（如 Tushare、AKShare、EastMoney）获取数据的过程。

**核心能力**：
- ✅ **统一数据格式**：获取的数据会被整理成统一格式（由 Schema 定义）
- ✅ **多源数据融合**：一个标准数据可以来源于多个数据源（如 K 线来自 Tushare，复权因子来自 AKShare）
- ✅ **灵活实现方式**：一个 DataSource 支持定义多种获取方法，可轻松扩展或更改实现

**核心特性**：
- **配置驱动**：通过 `mapping.json` 配置 handler 的启用、依赖和参数
- **框架定义准则，用户控制实现**：框架定义 Schema，用户实现 Handler
- **多实现共存**：一个 data source 可以有多个 handler 实现，但运行时只能选择一个
- **运行时切换**：通过配置文件切换 handler，无需修改代码
- **三层架构**：Manager（协调层）→ Handler（业务层）→ Provider（基础层）

## 🎯 核心概念

### 业务名词

| 名词 | 定义 | 说明 |
|------|------|------|
| **DataSource** | 标准数据源 | 框架需要的一种数据类型（如 K 线、财务数据） |
| **Schema** | 标准数据源格式 | 定义数据字段、类型、验证规则 |
| **Handler** | 执行器 | 实现数据获取逻辑，将多个 Provider 的数据合并成 Schema 格式 |
| **Provider** | 第三方数据供应商 | 封装第三方 API（如 Tushare、AKShare），提供 token、API 调用、限流信息 |
| **mapping.json** | 映射配置 | 声明标准数据源（DataSource）与执行器（Handler）的对应关系 |

### 业务链路

**完整流程**：
```
DataSource（标准数据源）
    ↓ 对应唯一
Schema（标准数据格式定义）
    ↓ 通过映射配置
mapping.json（指定使用哪个 Handler）
    ↓ 运行时选择
Handler（执行器，运行时只能选择一个）
    ↓ 调用多个
Provider（第三方数据供应商 API）
    ↓ 合并数据
Schema 格式的标准输出
    ↓ 可选
Data Manager（数据库存储）
```

**关键设计**：
1. **Provider 层**：用户自定义，包含三个要素：
   - Token/认证信息（如需要）
   - 数据获取 API 方法
   - 限流信息声明

2. **Handler 层**：通过自定义逻辑合并多个 Provider 的数据，输出符合 Schema 格式的标准数据
   - 提供丰富的生命周期钩子函数
   - 可在 `after_normalize()` 钩子中使用 Data Manager 进行数据库存储

3. **映射关系**：
   - 一个 DataSource 对应一个 Schema（1:1）
   - 一个 DataSource 可以有多个 Handler 实现，但运行时只能选择一个（通过 `mapping.json` 声明）
   - 一个 Schema 的字段可以来源于多个 Provider API（Handler 负责合并）

> 详细的设计理念和架构说明请参考 [architecture.md](./architecture.md)

## 📦 模块的组件

```
DataSourceManager (协调层)
    │
<<<<<<< HEAD
    ├── BaseDataSourceHandler (业务层)
    │       │
    │       ├── DataSourceTask (业务任务)
    │       │       └── ApiJob (API 调用任务)
    │       │
    │       └── TaskExecutor (任务执行器)
=======
    ├── BaseHandler (业务层)
    │       │
    │       ├── ApiJob / ApiJobBundle (API 任务与批次)
    │       │
    │       └── ApiJobExecutor (API 任务执行器，含限流/并发)
>>>>>>> write-doc
    │
    └── BaseProvider (基础层)
```

## 📁 模块的文件夹结构

```
core/modules/data_source/
├── __init__.py
<<<<<<< HEAD
├── data_source_manager.py          # DataSourceManager 主类
├── base_data_source_handler.py     # Handler 基类
├── simple_config_handler.py        # 纯配置驱动的 Handler（零代码）
├── base_provider.py                # Provider 基类
├── task_executor.py                # Task 执行器
├── schemas.py                      # Schema 定义
│
├── data_classes/                   # 数据类
│   ├── api_job.py                  # ApiJob 和 DataSourceTask
│   ├── data_source_definition.py   # DataSourceDefinition
│   └── handler_config.py          # Handler Config
│
└── services/                       # 服务层
    ├── api_job_manager.py
    ├── base_renew_service.py
    ├── incremental_renew_service.py
    ├── refresh_renew_service.py
    ├── rolling_renew_service.py
    └── renew_mode_service.py
=======
├── data_source_manager.py          # DataSourceManager 主类（协调层）
├── execution_scheduler.py          # DataSourceExecutionScheduler：调度各 Handler 执行
├── renew_manager.py                # RenewManager：日期范围与续跑编排
├── base_class/                     # 基类
│   ├── base_handler.py             # Handler 基类 BaseHandler
│   └── base_provider.py            # Provider 基类 BaseProvider
│
├── data_class/                     # 数据类定义
│   ├── api_job.py                  # ApiJob
│   ├── api_job_bundle.py           # ApiJobBundle（批次）
│   ├── config.py                   # DataSourceConfig
│   ├── handler_mapping.py          # HandlerMapping
│   ├── schema.py                   # Schema 定义
│   ├── field.py                    # Field 定义
│   └── ...                         # 其他数据类（error、renew_config 等）
│
├── service/                        # 服务层与 Helper
│   ├── api_job_executor.py         # ApiJobExecutor：执行 ApiJob/ApiJobBundle，包含限流与并发
│   ├── normalization/              # 标准化 service + helper
│   ├── date_range/                 # 日期范围 & renew 计算 service + helper
│   ├── renew/                      # incremental/rolling/refresh renew service
│   ├── executor/                   # bundle 执行与 fetched_data 重组
│   ├── persistence/                # persistence_service：写入绑定表
│   ├── utils/                      # 通用工具（如 record_utils）
│   └── ...                         # 其他 manager/helper
│
├── reserved_dependencies.py        # 预置依赖定义
└── examples/                       # 示例脚本（极端 renew 场景等）
>>>>>>> write-doc
```

## 🚀 模块的使用方法

### 基本使用

```python
from core.modules.data_source.data_source_manager import DataSourceManager

# 初始化
manager = DataSourceManager(is_verbose=False)

# 执行数据更新（配置驱动，自动运行所有启用的 handler）
await manager.renew_data(
    latest_completed_trading_date="20251222",
    stock_list=None,  # 如果不提供，会自动从数据库读取
    test_mode=False,
    dry_run=False
)
```

### 测试单个 Handler

```python
# 测试单个 handler（需要 handler 在 mapping.json 中启用）
result = await manager.fetch(
    "kline",
    context={
        "latest_completed_trading_date": "20251222",
        "stock_list": ["000001.SZ", "000002.SZ"]
    }
)
```

### 其他概念

| 概念 | 作用 | 关键点 |
|------|------|--------|
| **ApiJob** | 单个 API 调用任务 | 包含 Provider、方法、参数、依赖 |
<<<<<<< HEAD
| **DataSourceTask** | 业务任务 | 包含多个 ApiJob |
| **TaskExecutor** | 任务执行引擎 | 依赖解析、限流、并发执行 |
=======
| **ApiJobBundle** | 一批 API 任务 | 表示一个批次（如某一实体的一组 ApiJobs） |
| **ApiJobExecutor** | API 任务执行引擎 | 依赖解析、限流、并发执行 |
>>>>>>> write-doc

---

## 📚 模块详细文档

- **[architecture.md](./architecture.md)**：架构文档，包含详细的技术设计、核心组件、运行时 Workflow
- **[decisions.md](./decisions.md)**：重要决策记录，包含架构设计决策和理由

> **阅读建议**：先阅读本文档快速上手，然后阅读 [architecture.md](./architecture.md) 了解详细设计，最后阅读 [decisions.md](./decisions.md) 了解设计决策。

---

**文档结束**
