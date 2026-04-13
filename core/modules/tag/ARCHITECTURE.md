# Tag 系统架构文档

**版本：** 3.0  
**最后更新**: 2026-01-17  
**状态：** 生产环境

---

## 📋 目录

1. [设计背景](#设计背景)
2. [核心概念](#核心概念)
3. [系统架构](#系统架构)
4. [数据模型设计](#数据模型设计)
5. [核心组件](#核心组件)
6. [运行时 Workflow](#运行时-workflow)
7. [数据流设计](#数据流设计)
8. [重要决策记录 (Decisions)](#重要决策记录-decisions)
9. [配置设计](#配置设计)
10. [多进程执行设计](#多进程执行设计)
11. [职责边界](#职责边界)
12. [设计原则](#设计原则)
13. [文件组织](#文件组织)
14. [版本历史](#版本历史)

---

## 设计背景

### 问题背景

Tag 系统旨在解决以下问题：

1. **预计算需求**：策略分析需要大量预计算的标签（如市值分类、动量因子等）
2. **计算效率**：需要支持大规模并行计算，充分利用多核 CPU
3. **内存控制**：需要控制内存使用，避免大数据量场景下的内存溢出
4. **增量更新**：支持增量计算，避免重复计算已有数据
5. **配置驱动**：通过配置声明业务场景，无需修改代码

### 设计目标

1. **配置驱动**：通过 Python 配置文件定义业务场景，无需修改框架代码
2. **多进程并行**：充分利用多核 CPU，提高计算效率
3. **内存可控**：通过 Chunk 模式和单 entity 单进程控制内存使用
4. **增量计算**：支持 INCREMENTAL 和 REFRESH 两种更新模式
5. **易于扩展**：提供钩子函数和扩展点，方便用户扩展功能

---

## 核心概念

### 业务场景（Scenario）

一个业务逻辑单元，对应一个 TagWorker 和一个 Settings 配置。

- **示例**：市值分类（`market_value`）、动量因子（`momentum`）
- **特点**：一个 Scenario 可以产生多个 Tags
- **位置**：`userspace/tags/<scenario_name>/`

### 标签定义（Tag Definition）

Scenario 产生的具体标签。

- **示例**：大市值股票（`large_market_value`）、小市值股票（`small_market_value`）
- **特点**：属于某个 Scenario，在数据库的 `tag_definition` 表中存储

### 标签值（Tag Value）

标签的实际计算结果。

- **存储**：实体在某个日期的标签值
- **引用**：引用 Tag Definition
- **格式**：JSON 格式，支持结构化数据

---

## 系统架构

### 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    Tag 系统架构                          │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐      ┌──────────────┐                  │
│  │ TagManager   │─────▶│  TagWorker   │                  │
│  │ (发现/管理)   │      │ (子进程执行)   │                  │
│  └──────────────┘      └──────────────┘                  │
│         │                    │                            │
│         │                    │                            │
│         ▼                    ▼                            │
│  ┌──────────────┐      ┌──────────────┐                  │
│  │   Settings    │      │ BaseTagWorker│                  │
│  │  (配置文件)   │      │  (框架基类)   │                  │
│  └──────────────┘      └──────────────┘                  │
│                                                           │
│         │                    │                            │
│         └────────────────────┘                            │
│                    │                                      │
│                    ▼                                      │
│         ┌──────────────────────┐                          │
│         │   Database Tables    │                          │
│         │  - tag_scenario      │                          │
│         │  - tag_definition    │                          │
│         │  - tag_value         │                          │
│         └──────────────────────┘                          │
└─────────────────────────────────────────────────────────┘
```

### 组件关系

- **TagManager**：发现和管理所有业务场景，负责多进程调度
- **TagWorker**：实现业务计算逻辑，在子进程中执行
- **BaseTagWorker**：框架基类，提供执行流程和钩子函数
- **TagDataManager**：子进程数据管理器，负责 contract 签发/加载与游标切片
- **Settings**：配置文件，定义业务场景和标签配置

---

## 数据模型设计

### 三层表结构

系统采用三层表结构，清晰分离业务场景、标签定义和标签值：

```
tag_scenario (业务场景层)
    │
    ├─▶ tag_definition (标签定义层)
            │
            └─▶ tag_value (标签值层)
```

### 1. tag_scenario 表

**用途**：存储业务场景的元信息

**表结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGINT | 自增主键 |
| `name` | VARCHAR(64) | 业务场景唯一代码（如 `market_value`） |
| `display_name` | VARCHAR(128) | 业务场景显示名称 |
| `description` | TEXT | 业务场景描述 |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

**索引**：
- `UNIQUE KEY uk_name (name)`：场景名唯一
- `INDEX idx_name (name)`：按场景名查询

### 2. tag_definition 表

**用途**：存储标签定义，属于某个 Scenario

**表结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGINT | 自增主键 |
| `scenario_id` | BIGINT | 外键 → `tag_scenario.id` |
| `name` | VARCHAR(64) | 标签唯一代码（如 `large_market_value`） |
| `display_name` | VARCHAR(128) | 标签显示名称 |
| `description` | TEXT | 标签描述 |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

**索引**：
- `UNIQUE KEY uk_scenario_name (scenario_id, name)`：同一 Scenario 下标签名唯一
- `INDEX idx_scenario_id (scenario_id)`：按 Scenario 查询

### 3. tag_value 表

**用途**：存储标签的实际计算结果

**表结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `entity_type` | VARCHAR(32) | 实体类型（如 `stock`，默认 `stock`） |
| `entity_id` | VARCHAR(64) | 实体ID（如股票代码 `000001.SZ`） |
| `tag_definition_id` | BIGINT | 外键 → `tag_definition.id` |
| `as_of_date` | DATE | 业务日期（标签计算时间点） |
| `start_date` | DATE | 起始日期（时间切片标签用） |
| `end_date` | DATE | 结束日期（时间切片标签用） |
| `json_value` | JSON | 标签值（JSON 格式，支持键值对等结构化数据） |
| `calculated_at` | DATETIME | 计算时间 |

**主键**：
- `PRIMARY KEY (entity_id, tag_definition_id, as_of_date)`

**索引**：
- `INDEX idx_entity_date (entity_id, as_of_date)`：核心查询
- `INDEX idx_tag_date (tag_definition_id, as_of_date)`：辅助查询
- `INDEX idx_entity_tag_date (entity_id, tag_definition_id, as_of_date)`：增量计算

---

## 核心组件

### 1. TagManager (`tag_manager.py`)

**职责**：统一管理所有业务场景（按业务场景名管理）

**核心功能**：
1. **发现和注册**：自动发现所有业务场景，加载 settings 和 worker 类
2. **管理接口**：执行所有或单个 scenario
3. **多进程调度**：构建 jobs、决定进程数、执行多进程计算
4. **进度监控**：实时显示执行进度和统计信息

### 2. BaseTagWorker (`base_tag_worker.py`)

**职责**：框架基类，提供 TagWorker 的基础功能和框架支持

**核心功能**：
1. **执行流程**：`process_entity()` 方法处理单个 entity
2. **数据归类**：提供 entity、scenario、job、config 等只读数据
3. **钩子函数**：提供多个钩子函数供用户扩展
4. **批量保存**：管理 tag values 的批量保存

### 3. TagDataManager (`tag_data_manager.py`)

**职责**：子进程数据管理器，负责 DataContract + DataCursor 一体化数据流

**核心功能**：
1. **契约签发**：解析 `settings.data` 并调用 `issue_contracts`
2. **数据装填**：对 `needs_load` 的 contract 执行 `load`
3. **游标切片**：通过 `DataCursor.until(as_of_date)` 输出前缀视图
4. **统一结构**：对外统一使用 `historical_data[data_id]` 结构

### 4. Settings (`settings.py`)

**职责**：定义业务场景和标签的配置信息

**配置结构**：
- 顶层配置：`is_enabled`, `name`, `recompute` 等
- 类型配置：`tag_target_type`（`entity_based` / `general`）
- 目标实体配置：`target_entity`（`entity_based` 推荐；`general` 可省略）
- 数据配置：`data.required` + `data.tag_time_axis_based_on`
- 更新模式配置：`update_mode`, `incremental_required_records_before_as_of_date`
- 性能配置：`performance.max_workers`
- Tag 配置：`tags`（必须，至少一个）

### 5. TagWorker (`tag_worker.py`)

**职责**：实现业务场景的计算逻辑（子进程 worker）

**实现要求**：
- 继承 `BaseTagWorker`
- 实现 `calculate_tag()` 方法
- 一个 TagWorker 可以为多个 Tags 提供计算

---

## 运行时 Workflow

### 完整执行流程

```
1. 用户创建 TagManager 并调用 execute()
   │
   ├─▶ 2. TagManager 自动发现所有 scenarios
   │      - 遍历 scenarios 目录
   │      - 加载 settings 和 worker 类
   │      - 验证配置有效性
   │      - 缓存启用的 scenarios
   │
   └─▶ 3. 循环执行每个 scenario（同步执行）
          │
          ├─▶ a. 确保元信息存在（ensure_metadata）
          │      - 创建或更新 scenario 元信息
          │      - 创建或更新 tag definitions
          │
          ├─▶ b. 确定计算日期范围
          │      - REFRESH 模式：从默认开始日期到最新交易日
          │      - INCREMENTAL 模式：从最后更新日期的下一个交易日开始
          │
          ├─▶ c. 获取实体列表
          │      - entity_based：通过 PER_ENTITY 合约的 entity_list_data_id 推导
          │      - general：固定使用 "__general__" 占位 owner
          │
          ├─▶ d. 构建 jobs（每个 entity 一个 job）
          │      - 包含 entity_id、scenario_name、tag_definitions 等
          │
          ├─▶ e. 决定进程数
          │      - 根据 job 数量动态决定（最多 CPU 核心数）
          │
          └─▶ f. 执行多进程计算（ProcessWorker QUEUE 模式）
                 │
                 └─▶ 子进程执行流程：
                        │
                        ├─▶ 1. 初始化 TagWorker
                        │      - 从 payload 提取信息
                        │      - 初始化 TagDataManager
                        │
                        ├─▶ 2. 预处理（_preprocess）
                        │      - 获取交易日列表
                        │      - INCREMENTAL 模式下初始化数据加载
                        │
                        ├─▶ 3. 执行标签计算（_execute_tagging）
                        │      - 遍历每个交易日
                        │      - 对每个日期：获取历史数据并过滤到 as_of_date
                        │      - 对每个 tag：调用 calculate_tag()
                        │      - 收集结果
                        │
                        └─▶ 4. 后处理（_postprocess）
                               - 批量保存 tag values
                               - 返回统计信息
```

### TagManager 执行流程

**主要步骤**：

1. **发现和注册 Scenarios**
   - `_discover_scenarios_from_folder()`: 遍历 scenarios 目录
   - 加载 settings 和 worker 类
   - 验证配置有效性
   - 缓存启用的 scenarios

2. **执行每个 Scenario**
   - 确保元信息存在（`ensure_metadata`）
   - 确定计算日期范围（`JobHelper.calculate_start_and_end_date`）
   - 获取实体列表（`_get_entity_list`）
   - 构建 jobs（`_build_entity_jobs`）
   - 决定进程数（`JobHelper.decide_worker_amount`）
   - 执行多进程计算（`ProcessWorker.run_jobs`）
   - 监控进度并收集统计信息

### TagWorker 执行流程（子进程）

**主要步骤**：

1. **初始化阶段**
   - 从 payload 提取 entity、scenario、job 等信息
   - 初始化 TagDataManager
   - 调用 `on_init()` 钩子

2. **预处理阶段**（`_preprocess`）
   - 获取交易日列表（`get_trading_dates`）
   - 根据 settings.data 签发并加载 contracts，构建 DataCursor
   - 调用 `on_before_execute_tagging()` 钩子

3. **执行标签计算阶段**（`_execute_tagging`）
   - 遍历每个交易日
   - 对每个日期：
     - 获取前缀历史数据（`get_data_until`）
     - 对每个 tag 调用 `calculate_tag()`
     - 调用 `on_tag_created()` 钩子
   - 调用 `on_as_of_date_calculate_complete()` 钩子

4. **后处理阶段**（`_postprocess`）
   - 批量保存 tag values
   - 调用 `on_after_execute_tagging()` 钩子
   - 返回统计信息

---

## 数据流设计

### 数据流向图

```
┌─────────────────────────────────────────────────────────────┐
│                      Tag 系统数据流                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Settings (配置文件)                                         │
│       │                                                      │
│       ▼                                                      │
│  ScenarioModel (场景模型)                                    │
│       │                                                      │
│       ├─▶ ensure_metadata()                                 │
│       │      │                                               │
│       │      ▼                                               │
│       │   Database (tag_scenario, tag_definition)           │
│       │                                                      │
│       ├─▶ calculate_start_and_end_date()                    │
│       │      │                                               │
│       │      ▼                                               │
│       │   Date Range (start_date, end_date)                 │
│       │                                                      │
│       └─▶ _get_entity_list()                                │
│              │                                               │
│              ▼                                               │
│           Entity List (entity_ids)                          │
│              │                                               │
│              ▼                                               │
│  ┌──────────────────────────────────────────┐               │
│  │  Job Building (每个 entity 一个 job)      │               │
│  └──────────────────────────────────────────┘               │
│              │                                               │
│              ▼                                               │
│  ┌──────────────────────────────────────────┐               │
│  │  ProcessWorker (多进程执行)                │               │
│  └──────────────────────────────────────────┘               │
│              │                                               │
│              ▼                                               │
│  ┌──────────────────────────────────────────┐               │
│  │  子进程：TagWorker.process_entity()       │               │
│  └──────────────────────────────────────────┘               │
│              │                                               │
│              ├─▶ TagDataManager                             │
│              │      │                                        │
│              │      ├─▶ 加载 Base Data (Kline)              │
│              │      │      │                                 │
│              │      │      ▼                                 │
│              │      │   DataManager.stock.kline             │
│              │      │                                        │
│              │      ├─▶ 加载 Required Data                  │
│              │      │      │                                 │
│              │      │      ▼                                 │
│              │      │   DataManager (各种数据源)            │
│              │      │                                        │
│              │      └─▶ DataCursor.until(as_of_date)        │
│              │             │                                 │
│              │             ▼                                 │
│              │          Historical Data (过滤到 as_of_date) │
│              │                                               │
│              ├─▶ calculate_tag()                             │
│              │      │                                        │
│              │      ▼                                        │
│              │   Tag Value (JSON)                            │
│              │                                               │
│              └─▶ 批量保存                                    │
│                     │                                        │
│                     ▼                                        │
│                  Database (tag_value)                        │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 数据加载流程

**DataContract + DataCursor 模式**：
1. 根据 `settings.data.required` 签发 contracts（`issue_contracts`）
2. 对 `needs_load` 的 contract 执行 `load`
3. 构建 `DataCursor`（按 contract meta 的时间字段解析）
4. 每个 `as_of_date` 调用 `cursor.until(as_of_date)` 输出前缀视图

### 数据过滤流程

**目的**：避免"上帝模式"问题（计算时看到未来数据）

**流程**：
1. `TagDataManager.get_data_until(as_of_date)` 被调用
2. `DataCursor` 对每个时序源推进到 `as_of_date`（含）
3. 非时序源保持全量输出
4. 返回前缀历史数据给 `calculate_tag()` 方法

---

## 重要决策记录 (Decisions)

### 决策 1：三层表结构设计

**问题**：如何组织 tag_scenario、tag_definition、tag_value 的关系？

**决策**：采用三层表结构，清晰分离业务场景、标签定义和标签值。

**理由**：
- **清晰的数据模型**：Scenario → Definition → Value 三层结构清晰
- **查询更方便**：可以按 Scenario 查询所有 Tags
- **数据一致性更好**：一个 Scenario 的所有 Tags 共享相同的配置
- **扩展性强**：可以轻松添加新的 Scenario 或 Tag

**影响**：
- 查询时需要 JOIN 操作
- 删除 Scenario 时需要级联删除（通过应用层控制）

---

### 决策 2：多进程 vs 多线程

**问题**：使用多进程还是多线程执行 Tag 计算？

**决策**：使用多进程（ProcessWorker）。

**理由**：
- **CPU 密集型任务**：Tag 计算是 CPU 密集型，多进程绕过 Python GIL 限制
- **内存隔离**：每个进程独立内存空间，提高稳定性
- **真正并行**：充分利用多核 CPU，提高计算效率
- **进程结束自动释放**：进程结束自动释放内存，无需手动管理

**影响**：
- 需要序列化 job payload（通过 pickle）
- 子进程需要重新初始化 DataManager
- 进程间通信开销（但 Tag 计算是独立任务，不需要通信）

---

### 决策 3：以 Entity 为单位分割 Jobs

**问题**：如何分割 Jobs？按日期、按 Tag、还是按 Entity？

**决策**：以 Entity 为单位分割 Jobs（每个 entity 一个 job）。

**理由**：
- **内存可控**：每个进程只处理一个 entity，内存使用可控
- **数据加载简单**：每个 job 只需要加载一个 entity 的数据
- **失败隔离**：单个 entity 失败不影响其他 entity
- **批量保存方便**：一个 entity 的所有 tag values 可以批量保存

**影响**：
- Job 数量等于 entity 数量（可能很多）
- 需要动态决定进程数（根据 job 数量）

---

### 决策 4：DataContract + DataCursor 一体化

**问题**：Tag 数据加载与按日期切片应该如何实现？

**决策**：统一采用 DataContract 加载 + DataCursor 前缀切片。

**理由**：
- 与 strategy 模块对齐，降低维护成本
- 时间轴规则集中在 cursor，减少手写日期比较分支
- 契约可复用缓存与 loader 能力

**影响**：
- 旧 `use_chunk/data_chunk_size` 配置下线
- 数据声明统一收口到 `data.required`

---

### 决策 5：INCREMENTAL 模式历史窗口

**问题**：INCREMENTAL 模式下如何保证历史窗口充足？

**决策**：保留 `incremental_required_records_before_as_of_date` 语义，由 data contract 范围加载 + cursor 前缀视图共同保障。

**理由**：
- 保留历史窗口参数语义（不再依赖 chunk 推导）
- 避免把窗口逻辑绑死在 chunk 策略

**影响**：
- 配置仍需声明历史窗口需求
- 不再依赖 chunk 数量推导

---

### 决策 6：数据过滤策略

**问题**：如何避免"上帝模式"问题（计算时看到未来数据）？

**决策**：框架层面强制过滤到 `as_of_date`。

**理由**：
- **保证计算一致性**：框架层面过滤，保证所有 TagWorker 都遵循相同规则
- **简化用户代码**：用户无需关心数据过滤，只需关注业务逻辑
- **减少出错可能**：避免用户忘记过滤数据

**影响**：
- 每次调用 `calculate_tag()` 前都需要过滤数据（性能开销可接受）
- 用户无法访问未来数据（这是期望的行为）

---

### 决策 7：一个 TagWorker 打多个 Tag

**问题**：一个 TagWorker 是否可以产生多个 Tags？

**决策**：支持一个 TagWorker 产生多个 Tags。

**理由**：
- **业务逻辑复用**：如市值分类，可以同时产生大市值、小市值等多个 Tags
- **减少重复代码**：多个 Tags 可以共享相同的计算逻辑
- **配置更灵活**：共享 worker 配置，独立 tag 配置

**影响**：
- TagWorker 需要根据 `tag_definition` 参数决定计算哪个 Tag
- 一个 TagWorker 需要支持多个 Tags 的计算逻辑

---

### 决策 8：Settings 和 TagWorker 分离

**问题**：Settings 和 TagWorker 是否应该分离？

**决策**：Settings 和 TagWorker 分离，配置与代码分离。

**理由**：
- **配置与代码分离**：便于维护和版本控制
- **支持配置热更新**：未来可能支持配置的热更新
- **一个 TagWorker 可以打多个 Tag**：配置需要独立管理

**影响**：
- 需要维护两个文件（`settings.py` 和 `tag_worker.py`）
- 配置验证需要在运行时进行

---

### 决策 9：使用 JSON 类型存储标签值

**问题**：标签值使用什么类型存储？

**决策**：使用 JSON 类型存储标签值。

**理由**：
- **支持结构化数据**：可以存储键值对、数组等结构化数据
- **灵活性强**：可以存储各种类型的数据，无需修改表结构
- **便于扩展**：未来可以轻松添加新的字段

**影响**：
- 需要序列化和反序列化 JSON（性能开销可接受）
- 查询时需要解析 JSON（但大多数查询不需要）

---

### 决策 10：QUEUE 模式 vs BATCH 模式

**问题**：ProcessWorker 使用 QUEUE 模式还是 BATCH 模式？

**决策**：使用 QUEUE 模式。

**理由**：
- **持续填充进程池**：完成一个 job 立即启动下一个，充分利用资源
- **适合 CPU 密集型任务**：Tag 计算是 CPU 密集型任务
- **单 entity 单进程已经控制内存**：不需要 BATCH 模式的内存控制

**影响**：
- 需要持续监控进程池状态
- 需要处理进程池的动态填充

---

## 配置设计

### 配置结构

> **详细配置结构请参考** `userspace/tags/example_settings.py`，该文件包含完整的配置示例和每个属性的详细解释。

配置采用扁平化结构，主要包含：
- **顶层配置**：`is_enabled`, `name`, `recompute` 等
- **类型配置**：`tag_target_type`（`entity_based` / `general`）
- **目标实体配置**：`target_entity`（`entity_based` 推荐；`general` 可省略）
- **数据配置**：`data.required`（非空）+ `data.tag_time_axis_based_on`
- **更新模式配置**：`update_mode`, `incremental_required_records_before_as_of_date`（INCREMENTAL 模式必须）
- **业务配置**：`core`, `performance`（可选）
- **Tag 配置**：`tags`（必须，至少一个）

两类 Tag 的时间轴规则：
- **entity_based**：`data.tag_time_axis_based_on` 可选；默认使用 `target_entity` 对应主轴
- **general**：`data.tag_time_axis_based_on` 必填

校验约束：
- `data.required` 必须非空
- `data.required` 内 `data_id` 不可重复
- `data.tag_time_axis_based_on`（若配置）必须命中 `data.required[*].data_id`
- `data.tag_time_axis_based_on` 必须指向时序数据

### 性能配置说明

**`max_workers`**：
- 默认值：`auto`
- 说明：并行 worker 数量上限

**`incremental_required_records_before_as_of_date`**：
- INCREMENTAL 模式必须配置
- 说明：在增量模式下，保证 `as_of_date` 之前有足够历史窗口

---

## 多进程执行设计

### 设计目标

Tag 系统采用多进程并行执行，以提高计算效率，同时保证内存使用可控。

### 核心设计原则

1. **以 Entity 为单位分割 Jobs**：每个 entity（股票）一个 job，完成完整的 tag 计算后存储
2. **根据 Job 数量决定进程数**：动态决定进程数，最多 CPU 核心数
3. **主进程负责监控和管理**：主进程只负责任务分发和进度监控
4. **子进程初始化后才读取数据**：保证内存使用可控，进程结束自动释放
5. **实时进度展示**：显示完成数、百分比、成功/失败数、预计剩余时间

### Job 分割策略

**Job 结构**：

```python
job = {
    'id': f"{entity_id}_{scenario_name}",
    'payload': {
        'entity_id': entity_id,
        'entity_type': 'stock',
        'scenario_name': self.scenario_name,
        'tag_definitions': tag_defs,  # 该scenario的所有tag definitions
        'start_date': start_date,
        'end_date': end_date,
        'settings': self.settings,  # 完整的settings配置
        'update_mode': self.update_mode,
        'worker_module_path': worker_module_path,
        'worker_class_name': worker_class_name,
    }
}
```

**分割逻辑**：
- 每个 entity 一个 job
- Job 包含该 entity 的所有计算信息（tag definitions、配置、日期范围等）
- Job ID 格式：`{entity_id}_{scenario_name}`

### 进程数决定策略

**策略**（`JobHelper.decide_worker_amount`）：

```python
- 100个job及以下：1个worker
- 500个job及以下，100个以上：2个worker
- 1000个job及以下，500个以上：4个worker
- 2000个job及以下，1000个以上：8个worker
- 2000个job以上：最大worker（max_workers，默认 CPU 核心数）
```

**配置优先级**：
1. 如果 `settings.performance.max_workers` 已配置，优先使用（但不超过最大限制）
2. 否则根据 job 数量自动决定

### 执行模式

**使用 QUEUE 模式**：
- 持续填充进程池，完成一个立即启动下一个
- 适合 CPU 密集型任务
- 充分利用进程池，提高效率

### 错误处理

**单个 Entity 失败不影响其他 Entity**：
- 每个 job 独立执行，互不影响
- 失败时记录错误日志，继续执行其他 jobs
- 返回统计信息（成功数、失败数）

---

## 职责边界

### 组件职责矩阵

| 功能 | Settings | TagWorker | BaseTagWorker | TagManager | TagDataManager |
|------|----------|-----------|---------------|------------|---------------------|
| 定义配置 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 检查启用状态 | ❌ | ❌ | ❌ | ✅ | ❌ |
| 实现计算逻辑 | ❌ | ✅ | ❌ | ❌ | ❌ |
| 加载数据 | ❌ | ❌ | ❌ | ❌ | ✅ |
| 发现业务场景 | ❌ | ❌ | ❌ | ✅ | ❌ |
| 管理实例 | ❌ | ❌ | ❌ | ✅ | ❌ |
| 执行流程（子进程） | ❌ | ❌ | ✅ | ❌ | ❌ |
| 多进程调度 | ❌ | ❌ | ❌ | ✅ | ❌ |
| Job 构建 | ❌ | ❌ | ❌ | ✅ | ❌ |
| 进程数决定 | ❌ | ❌ | ❌ | ✅ | ❌ |

---

## 设计原则

### 1. 职责单一

每个组件只负责自己的职责：
- Settings 只定义配置
- TagWorker 只实现计算
- Manager 只管理
- BaseTagWorker 只提供框架
- TagDataManager 只管理数据

### 2. 配置驱动

通过配置声明行为，而不是硬编码：
- 配置与代码分离
- 声明式配置，便于维护

### 3. 可扩展性

提供钩子函数和扩展点：
- 用户可以在不修改框架代码的情况下扩展功能
- 支持自定义数据加载和计算逻辑

### 4. 早期验证

在创建实例前就验证配置和启用状态：
- 避免不必要的初始化开销
- 提前发现问题

### 5. 统一接口

所有 TagWorkers 遵循相同的接口：
- 便于统一管理和执行
- 降低学习成本

---

## 文件组织

### 目录结构

```
core/
└── modules/
    └── tag/
        ├── core/
        │   ├── base_tag_worker.py          # 框架基类
        │   ├── tag_manager.py              # 业务场景管理器
        │   ├── enums.py                    # 枚举定义
        │   ├── config.py                   # 全局配置
        │   ├── models/
        │   │   ├── scenario_model.py
        │   │   └── tag_model.py
        │   └── components/
        │       ├── helper/
        │       │   ├── job_helper.py
        │       │   └── tag_helper.py
        │       └── data_management/
        │           └── tag_data_manager.py
        ├── docs/
        │   └── DESIGN.md                   # 旧设计文档（已废弃）
        ├── ARCHITECTURE.md                 # 架构文档（本文档）
        └── README.md                       # 使用指南
└── userspace/
    └── tags/
        ├── example/                        # 示例场景
        │   ├── settings.py
        │   └── tag_worker.py
        ├── momentum/                       # 动量因子场景
        │   ├── settings.py
        │   └── tag_worker.py
        └── ...
```

---

## 版本历史

### 版本 3.0 (2026-01-17)

**主要变更**：
- 重命名 DESIGN.md 为 ARCHITECTURE.md
- 添加"重要决策记录 (Decisions)"章节
- 添加"运行时 Workflow"章节，详细描述执行流程
- 添加"数据流设计"章节，详细描述数据流向
- 更新版本号和最后更新日期

### 版本 2.0 (2025-12-19)

**主要变更**：
- 重构多进程执行设计
- 添加 Chunk 模式和全量模式支持
- 添加 INCREMENTAL 模式初始化
- 添加数据过滤策略

### 版本 1.0 (初始版本)

**主要功能**：
- 基础 Tag 系统实现
- 三层表结构设计
- 多进程执行支持

---

**文档结束**
