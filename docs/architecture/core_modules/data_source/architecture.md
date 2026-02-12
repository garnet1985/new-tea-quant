# Data Source 架构文档

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

为整个app提供一个从第三方数据供应商获取数据的框架：

1. **统一的数据格式**：数据可以来源于多个供应商，但我们系统内使用的数据源需要一个定义好的统一标准格式
2. **多数据源支持**：有时候我们需要的数据可能需要多个供应商的不同API一起提供，我们的模块需要按照统一标准数据源合并整理得到统一的output
3. **数据源依赖**：有的时候我们通过某个数据供应商得到的API只是为了获取关键数据的依赖，模块需要提供自动解决依赖的方式（拓扑排序）
4. **获取数据的多样性**：有的时候我们的数据供应商不可用或发生了API数据返回结构变化导致我们的数据获取不可用，模块需要提供一种快速切换数据获取方式的模式（DataSource与handler的mapping声明）
5. **第三方API限流**：第三方API都有自己的API请求限制，当用户配置过后模块能根据用户声明的流量限制和拓扑排序自动对数据获取的API请求提供流量限制和等待。
6. **钩子函数提供的方法重写**：用户随时对执行的介入方式：模块的执行器需要提供足够友好的钩子函数让用户在不更改核心代码的情况下能重新定义某些默认步骤的实现方法
7. **提高效率**：数据源获取支持多线程

### 设计目标

基于上述业务目标，我们制定了以下技术设计目标：

1. **统一数据格式**：获取的数据会被整理成统一格式（由 Schema 定义），确保数据一致性
2. **多源数据融合**：支持一个标准数据（DataSource）来源于多个数据源（如 K 线来自 Tushare，复权因子来自 AKShare）
3. **灵活实现方式**：一个 DataSource 支持定义多种获取方法（Handler），可轻松扩展或更改实现
4. **配置驱动**：通过 `mapping.json` 配置 handler 的启用、依赖和参数，无需修改代码
5. **统一依赖管理**：在 `renew_data` 开始时统一解析和获取所有需要的全局依赖
6. **按需获取**：只获取真正需要的依赖，避免不必要的开销
7. **易于扩展**：预留接口，方便未来添加新的全局依赖和数据源
8. **职责清晰**：每层各司其职，Provider 负责 API 封装，Handler 负责业务逻辑，Manager 负责协调管理

---

## 设计理念

### 核心原则

1. **框架定义准则，用户控制实现**：框架定义 Schema，用户根据 Provider 自由实现 Handler
2. **配置驱动，灵活切换**：通过 `mapping.json` 配置 handler 的启用、依赖和参数，运行时切换无需修改代码
3. **一个 dataSource，多个 handler（但运行时只选一个）**：可以有多个 handler 实现，但运行时只能选择一个，避免数据互相覆盖
4. **职责分离**：Provider 负责 API 封装，Handler 负责业务逻辑，Manager 负责协调管理
5. **声明式限流**：Provider 只声明限流信息，由执行层（如 ApiJobExecutor）负责执行限流

### 分层架构

为了实现上述业务目标，我们设计了分层的数据获取架构：

- **Manager（协调层）**：加载配置和注册，全局依赖注入，运行所有启用的 handler
- **Handler（业务层）**：数据获取逻辑，数据标准化，多 Provider 组合，依赖处理
- **Provider（基础层）**：纯 API 封装，认证配置，API 元数据声明，错误转换

---

## 核心组件详解

Data Source 采用三层架构，每层负责不同的职责：

### Provider 层（基础层）

**职责**：

- ✅ **负责**：
  - **纯 API 封装**：封装第三方 API 调用（如 Tushare、AKShare、EastMoney）
  - **认证配置**：管理 token、api_key 等认证信息
  - **API 限流信息声明**：声明每个 API 的限流规则（如每分钟 200 次），但不执行限流
  - **错误转换**：统一错误格式，将第三方 API 的错误转换为框架统一的错误格式
  - **Provider 元数据**：声明 Provider 的基本信息（名称、认证类型等）
- ❌ **不负责**：
  - 不包含业务逻辑（业务逻辑由 Handler 负责）
  - 不负责数据标准化（数据标准化由 Handler 负责）
  - 不执行限流逻辑（限流执行由 ApiJobExecutor 等执行层负责）
  - 不负责多线程调度（多线程调度由 Manager/执行层负责）

**组件**：
- **BaseProvider**：Provider 基类，定义 Provider 的标准接口
- **Provider 实现**：用户自定义的 Provider（如 `TushareProvider`、`AKShareProvider`）

**特点**：
- 纯 API 封装，不包含业务逻辑
- 声明式元数据（限流、认证信息作为类属性）
- 简单可测试

### Handler 层（业务层）

**职责**：

- ✅ **负责**：
  - **数据获取逻辑**：决定调用哪些 Provider 的哪些 API
  - **数据标准化**：将原始数据转换为符合 Schema 的格式（字段映射、类型转换、数据清洗）
  - **多 Provider 组合和协调**：处理需要多个 API 协作的场景
  - **依赖数据处理**：处理 API 之间的依赖关系（通过 `depends_on` 配置）
  - **批量处理逻辑**：决定如何批量处理数据（如按股票、按日期等）
  - **Handler 元信息**：声明 Handler 的依赖需求（`dependencies`）
- ❌ **不负责**：
  - 不负责多线程调度（多线程调度由 Manager 负责）
  - 不负责全局限流管理（全局限流管理由 ApiJobExecutor 等执行层负责）

**组件**：
- **BaseHandler**：Handler 基类，定义 Handler 的生命周期钩子和模板方法
- **Handler 实现**：用户自定义的 Handler（如 `KlineHandler`、`CorporateFinanceHandler`）

**特点**：
- 业务逻辑集中，完全可控
- 灵活扩展，可以处理复杂的多 API 协作场景
- 生命周期钩子丰富，支持在数据获取的不同阶段执行自定义逻辑

### Manager 层（协调层）

**职责**：

- ✅ **负责**：
  - **配置加载和 Handler 注册**：加载 Schema 定义、Handler 映射配置，动态加载 Handler 类
  - **全局依赖解析和注入**：在 `renew_data` 开始时统一解析和获取所有需要的全局依赖
  - **运行所有启用的 handler**：遍历所有 `is_enabled=true` 的 handler，执行数据获取
  - **进度跟踪**：跟踪数据获取的进度
  - **错误汇总**：汇总所有 handler 的错误信息
- ❌ **不负责**：
  - 不包含具体的数据获取逻辑（数据获取逻辑由 Handler 负责）
  - 不包含数据标准化逻辑（数据标准化逻辑由 Handler 负责）
  - 不处理依赖关系（Handler 自己解决依赖）
  - 不执行限流（限流执行由 ApiJobExecutor 等执行层负责）

**组件**：
- **DataSourceManager**：数据源管理器，负责协调所有 Handler 的执行

**特点**：
- 配置驱动，通过 `mapping.json` 控制 handler 的启用和配置
- 统一依赖管理，确保所有 handler 使用一致的全局依赖
- 支持测试单个 Handler（`fetch()` 方法）

### 其他核心组件

**ApiJob（API 调用任务）**：
- 封装单个 API 调用所需的所有信息（Provider、方法、参数）
- 定义依赖关系（`depends_on`）

**ApiJobBundle（API 任务批次）**：
- 表示一批需要一起执行的 ApiJobs（例如某一实体的一组 API 调用）

**ApiJobExecutor（API 任务执行器）**：
- 执行 `ApiJob` / `ApiJobBundle` 列表
- 拓扑排序（根据 `depends_on`）
- 限流控制（通过 `RateLimiter`）
- 并发管理（多线程执行）
- 错误处理和重试

**DataSourceSchema（数据格式规范）**：
- 定义数据结构、字段、类型
- 验证数据是否符合要求（`validate()`）
- 保证数据一致性

### 业务链路和映射关系

**完整业务链路**：
```
DataSource（标准数据源）
    ↓ 对应唯一（1:1）
Schema（标准数据格式定义）
    ↓ 通过映射配置
mapping.json（指定使用哪个 Handler）
    ↓ 运行时选择（多对一）
Handler（执行器，运行时只能选择一个）
    ↓ 调用多个（一对多）
Provider（第三方数据供应商 API）
    ↓ 合并数据
Schema 格式的标准输出
    ↓ 可选
Data Manager（数据库存储）
```

**映射关系说明**：
- **DataSource ↔ Schema**：一对一关系，一个 DataSource 对应一个 Schema
- **DataSource ↔ Handler**：一对多关系，一个 DataSource 可以有多个 Handler 实现，但运行时只能选择一个（通过 `mapping.json` 声明）
- **Schema ↔ Provider**：多对多关系，一个 Schema 的字段可以来源于多个 Provider API（Handler 负责合并）

**关键设计**：
1. **Provider 层三要素**：用户自定义 Provider 需要包含：
   - Token/认证信息（如需要）
   - 数据获取 API 方法
   - 限流信息声明

2. **Handler 层职责**：通过自定义逻辑合并多个 Provider 的数据，输出符合 Schema 格式的标准数据
   - 提供丰富的生命周期钩子函数
   - 可在 `after_normalize()` 钩子中使用 Data Manager 进行数据库存储

---

## 架构图

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│              Data Source 系统架构                         │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────────────────────────────┐          │
│  │  DataSourceManager (协调层)                │          │
│  │  - 加载配置和注册                          │          │
│  │  - 全局依赖注入                            │          │
│  │  - 运行所有启用的 handler                   │          │
│  └──────────────────────────────────────────┘          │
│           │                                              │
│           ▼                                              │
│  ┌──────────────────────────────────────────┐          │
│  │  BaseHandler (业务层)                     │          │
│  │  - 数据获取逻辑                            │          │
│  │  - 数据标准化                              │          │
│  │  - 多 Provider 组合                        │          │
│  │  - 依赖处理                                │          │
│  └──────────────────────────────────────────┘          │
│           │                                              │
│           ├─▶ ApiJob / ApiJobBundle（API 任务与批次）     │
│           │                                              │
│           ├─▶ ApiJobExecutor (任务执行器)               │
│           │   - 拓扑排序                                 │
│           │   - 限流控制                                 │
│           │   - 并发管理                                 │
│           │                                              │
│           ▼                                              │
│  ┌──────────────────────────────────────────┐          │
│  │  BaseProvider (基础层)                     │          │
│  │  - 纯 API 封装                             │          │
│  │  - 认证配置                                │          │
│  │  - API 元数据声明                          │          │
│  │  - 错误转换                                │          │
│  └──────────────────────────────────────────┘          │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### 三层架构说明

1. **Manager（协调层）**
   - 配置加载和 Handler 注册
   - 全局依赖解析和注入
   - 运行所有启用的 handler
   - 进度跟踪和错误汇总

2. **Handler（业务层）**
   - 数据获取逻辑（调用 Provider）
   - 数据标准化（转为框架 Schema）
   - 多 Provider 组合和协调
   - 依赖数据处理

3. **Provider（基础层）**
   - 纯 API 封装
   - 认证配置
   - API 元数据声明（限流信息）
   - 错误转换

---

## 运行时 Workflow

### renew_data() 完整执行流程

```
1. DataSourceManager.renew_data() 被调用
   │
   ├─▶ 2. 依赖解析 (Dependency Resolution)
   │      - 读取 mapping.json，找出所有 is_enabled=true 的 handler
   │      - 收集每个 handler 声明的依赖需求（dependencies）
   │      - 去重，得到需要获取的全局依赖列表
   │
   ├─▶ 3. 依赖注入 (Dependency Injection)
   │      - 根据依赖列表，获取所有需要的全局依赖
   │      - 构建 shared_context（包含：
   │        - latest_completed_trading_date
   │        - stock_list
   │        - test_mode, dry_run 等参数）
   │
   └─▶ 4. Handler 执行循环
          - 遍历所有启用的 handler：
          │
          └─▶ 5. Handler.execute(context)
                │
                ├─▶ Phase 1: 数据准备阶段
                │      - before_fetch(context) - 构建执行上下文
                │      - 自动处理 renew_mode（如果配置）
                │        - Renew 服务（date_range_service + renew_*_service）计算日期范围
                │      - 构建 ApiJob / ApiJobBundle 列表
                │      - after_fetch(..., context) - Jobs / Bundles 生成后
                │
                ├─▶ Phase 2: 执行阶段
                │      - ApiJobExecutor.execute(bundles)
                │        - 对每个 batch：
                │          - 执行 batch 的所有 ApiJobs：
                │            ├─ 拓扑排序（根据 depends_on）
                │            ├─ 限流控制（RateLimiter）
                │            ├─ 并发执行（多线程）
                │            └─ 返回结果
                │
                └─▶ Phase 3: 标准化阶段
                       - before_normalize(raw_data)
                       - normalize(raw_data) → Dict
                         - 字段映射、数据清洗、类型转换
                       - after_normalize(normalized_data, ...)
                         - 保存数据
                       - validate(normalized_data)
                         - Schema 验证
```


### ApiJobExecutor 执行流程

```
1. ApiJobExecutor.execute(api_jobs 或 bundles) 被调用
   │
   ├─▶ 2. 计算限流值
   │      - 遍历所有 ApiJobs / Bundles，收集所有 ApiJobs
   │      - 从 Provider 获取每个 API 的限流声明
   │      - 计算每个 task 的最小限流值（木桶效应）
   │
   ├─▶ 3. 决定线程数
   │      - 根据 batch / job 数量决定线程数（最多10个）
   │      - 根据最小限流值调整线程数
   │
   ├─▶ 4. 并行执行 ApiJobBatch
   │      - 使用 MultiThreadWorker 并行执行
   │      - 对每个 batch：
   │        - 执行 batch 的所有 ApiJobs：
   │          ├─ 拓扑排序（根据 depends_on）
   │          ├─ 按顺序执行：
   │          │   - RateLimiter.acquire()
   │          │   - provider.method(**params)
   │          │   - 收集结果
   │
   └─▶ 5. 收集结果
          - 返回 {batch_id 或 "_single": {job_id: result}} 字典
```

### 数据流

```
[Input] 执行上下文（context）
  ├─ latest_completed_trading_date
  ├─ stock_list
  ├─ test_mode, dry_run 等参数
  └─ Handler 自定义参数
  ↓
[Handler] before_fetch(context)
  └─ 构建执行上下文
  ↓

[Handler] 构建 ApiJob / ApiJobBundle 列表
  ├─ Bundle 1: 包含多个 ApiJobs
  ├─ Bundle 2: 包含多个 ApiJobs
  └─ ...
  ↓
[Handler] after_fetch(..., context)
  └─ ApiJob / Bundle 构建完成（还未执行）
  ↓
[ApiJobExecutor] 执行 ApiJobs / Bundles
  ├─ 拓扑排序（根据 depends_on）
  ├─ 限流控制（RateLimiter）
  ├─ 并发执行（多线程）
  └─ 返回原始数据：{batch_id 或 "_single": {job_id: result}}
  ↓
[Handler] before_normalize(raw_data)
  └─ 标准化前
  ↓
[Handler] normalize(raw_data) → Dict
  ├─ 字段映射（API 字段 → Schema 字段）
  ├─ 数据清洗
  └─ 类型转换
  ↓
[Output] Schema 格式数据
  └─ {"data": [记录1, 记录2, ...]}
  ↓
[Handler] after_normalize(normalized_data)
  └─ 标准化后（保存数据）
  ↓
[DataManager] 保存到数据库
```

---

## 未来扩展方向

> **说明**：以下扩展方向分为两类：
> - **待实现扩展（单机版支持）**：可以在单机版中实现的功能
> - **可扩展方向（单机版不支持）**：需要分布式架构支持的功能，当前单机版不支持

### 待实现扩展（单机版支持）

#### 1. 数据获取监控和告警

**目标**：监控数据获取的状态和性能

**实现方向**：
- 自动计算worker数量（现有实现很粗糙，不是根据系统资源来定的）
- 数据获取成功率监控
- 数据获取性能监控
- 异常告警机制

**相关文档**：参考 [Road Map](../development/road-map.md)

---

### 可扩展方向（单机版不支持）

> **注意**：以下功能需要分布式架构支持，当前单机版不支持。如需实现，需要先升级架构。

#### 1. 分布式数据获取

**目标**：支持分布式环境下的数据获取

**实现方向**：
- 支持多机器并行获取数据
- 数据获取任务分发和调度
- 分布式限流管理

**相关文档**：参考 [Road Map](../development/road-map.md)

---

## 相关文档

- **[overview.md](./overview.md)**：模块概览
- **[decisions.md](./decisions.md)**：重要决策记录

> **提示**：本文档描述了 Data Source 的架构设计。如需了解设计决策的背景和理由，请参考 [decisions.md](./decisions.md)。

---

**文档结束**
