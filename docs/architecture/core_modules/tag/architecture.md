# Tag 架构文档

**版本：** 3.0  
**最后更新**: 2026-01-17  
**状态：** 生产环境

---

## 📋 目录

1. [设计背景](#设计背景)
2. [设计目标](#设计目标)
3. [系统架构](#系统架构)
4. [数据模型设计](#数据模型设计)
5. [核心组件](#核心组件)
6. [运行时 Workflow](#运行时-workflow)
7. [数据流设计](#数据流设计)
8. [配置设计](#配置设计)
9. [多进程执行设计](#多进程执行设计)
10. [职责边界](#职责边界)
11. [设计原则](#设计原则)
12. [文件组织](#文件组织)

---

## 设计背景

### 问题背景

Tag 系统要解决的，不只是「算得更快」，而是提供一套**统一、可复用、可追溯的标签资产层**：

1. **预计算需求**：策略分析需要大量预计算的标签（市值分类、动量因子、技术指标等），如果每个回测框架各算一遍，会造成巨大的重复计算和实现差异。
2. **跨策略复用**：同一个标签（例如 60 日动量）往往被多个策略和分析任务共享，如果每个策略都实现自己的版本，很难保证口径一致。
3. **可追溯性**：策略问题排查时，需要回答「当时这个因子/标签具体是什么值」，这要求标签值被长期、结构化地存下来，而不是每次现算。
4. **计算效率与内存控制**：在全市场 + 长历史的场景下，需要支持大规模并行计算，并控制单次任务的内存占用。
5. **配置驱动**：标签定义和业务场景需要通过配置声明，而不是散落在代码中，便于演进和审计。

### 设计目标

1. **配置驱动**：通过 Python 配置文件定义业务场景（Scenario）和标签（Tags）
2. **多进程并行**：充分利用多核 CPU，提高计算效率
3. **内存可控**：通过 Chunk 模式和单 entity 单进程控制内存使用
4. **增量计算**：支持 `incremental` 和 `refresh` 两种更新模式
5. **可复用 & 跨策略**：标签值一旦写入数据库，任意策略、分析脚本都可以直接通过 DataManager 读取
6. **可追溯**：通过 `as_of_date`、`entity_id`、`tag_definition_id` 等字段，随时还原某一时点的标签视图

---

## 系统架构

### 架构图

```text
┌─────────────────────────────────────────────────────────┐
│                    Tag 系统架构                          │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────┐      ┌──────────────┐                  │
│  │ TagManager   │─────▶│  TagWorker   │                  │
│  │ (发现/管理)   │      │ (子进程执行)   │                  │
│  └──────────────┘      └──────────────┘                  │
│         │                    │                            │
│         ▼                    ▼                            │
│  ┌──────────────┐      ┌──────────────┐                  │
│  │   Settings    │      │ BaseTagWorker│                  │
│  │  (配置文件)   │      │  (框架基类)   │                  │
│  └──────────────┘      └──────────────┘                  │
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
- **TagWorker**：用户实现的业务计算逻辑，在子进程中执行
- **BaseTagWorker**：框架基类，提供执行流程和钩子函数
- **TagWorkerDataManager**：子进程数据管理器，负责数据加载和过滤
- **Settings**：配置文件，定义业务场景和标签配置

---

## 数据模型设计

### 三层表结构

Tag 系统采用三层表结构，清晰分离业务场景、标签定义和标签值：

```text
tag_scenario (业务场景层)
    │
    ├─▶ tag_definition (标签定义层)
            │
            └─▶ tag_value (标签值层)
```

### 1. `tag_scenario` 表

- 存储业务场景的元信息
- 关键字段：`id`, `name`, `display_name`, `description`, `created_at`, `updated_at`

### 2. `tag_definition` 表

- 存储具体标签定义，属于某个 Scenario
- 关键字段：`id`, `scenario_id`, `name`, `display_name`, `description`

### 3. `tag_value` 表

- 存储标签的实际计算结果
- 关键字段：
  - `entity_type`, `entity_id`
  - `tag_definition_id`
  - `as_of_date`, `start_date`, `end_date`
  - `json_value`（JSON 格式的标签值）

---

## 核心组件

### TagManager (`tag_manager.py`)

**职责**：统一管理所有业务场景（Scenario），负责执行入口和多进程调度。

**核心功能**：

1. **发现 & 注册场景**：
   - 遍历 `userspace/tags/` 目录，加载 `settings.py` 和 `tag_worker.py`
   - 使用 `ScenarioModel` 做配置验证和封装
2. **执行接口**：
   - `execute()`：执行所有启用的场景
   - `execute(scenario_name=...)`：执行单个场景
3. **多进程调度**：
   - 构建 jobs（每个 entity 一个 job）
   - 通过 Worker 模块的 `ProcessWorker` 并行执行

### BaseTagWorker (`base_tag_worker.py`)

**职责**：定义 Tag 计算的生命周期流程，提供钩子函数供用户扩展。

**核心功能**：

1. **统一执行流程**：
   - `_preprocess()`：预处理（初始化增量模式、获取交易日等）
   - `_execute_tagging()`：按日期、按 tag 调用 `calculate_tag()`
   - `_postprocess()`：批量保存 `tag_value`
2. **上下文注入**：
   - `self.entity` / `self.scenario` / `self.job` / `self.settings` / `self.tracker`
3. **数据访问**：
   - 通过 `TagWorkerDataManager` 加载、缓存并过滤数据到 `as_of_date`

### TagWorkerDataManager (`tag_worker_data_manager.py`)

**职责**：子进程中所有数据加载与过滤逻辑。

**核心功能**：

1. 从 DataManager 加载 K 线和依赖数据（如财务数据）
2. 支持 Chunk 模式和全量模式两种加载策略
3. 提供 `filter_data_to_date(as_of_date)`，强制过滤到指定日期，避免「上帝模式」

### ScenarioModel & TagModel

- `ScenarioModel`：封装 Scenario 配置与元数据，负责：
  - 计算更新模式
  - 确定日期范围
  - 确保元信息（Scenario / TagDefinition）写入数据库
- `TagModel`：封装 TagDefinition，便于在 Worker 中使用

---

## 运行时 Workflow

### 主流程：TagManager.execute()

```text
┌─────────────────────────────────────────────────────────────┐
│                 TagManager.execute() 调用链                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────────────────────────────┐
         │ Step 1: 发现并加载所有场景 (discover_scenarios)     │
         │  - 遍历 userspace/tags/ 目录                        │
         │  - 加载每个 scenario 的 settings.py / tag_worker.py │
         │  - 构建 ScenarioModel / TagModel                    │
         └─────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────────────────────────────┐
         │ Step 2: 依次执行启用的场景 (execute_single)         │
         │  对每个 enabled 的 Scenario：                        │
         │    a) ensure_metadata() 写入/更新元信息              │
         │    b) 计算 start_date / end_date                    │
         │    c) 获取实体列表（如所有过滤后的股票）             │
         │    d) 构建 jobs（每个 entity 一个 job）              │
         │    e) 决定进程数（JobHelper.decide_worker_amount）  │
         │    f) 使用 ProcessWorker.run_jobs(jobs) 多进程执行  │
         └─────────────────────────────────────────────────────┘
```

### 子进程流程：BaseTagWorker.process_entity()

```text
┌─────────────────────────────────────────────────────────────┐
│            BaseTagWorker.process_entity() 生命周期           │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────────────────────────────┐
         │ Phase 0: 初始化 (__init__)                          │
         │  - 解析 job_payload，注入：                         │
         │    • entity: id / type                              │
         │    • scenario: name / update_mode                   │
         │    • job: start_date / end_date                     │
         │    • tag_definitions / settings                     │
         │  - 创建 DataManager & TagWorkerDataManager          │
         └─────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────────────────────────────┐
         │ Phase 1: 预处理 (_preprocess)                       │
         │  - INCREMENTAL 模式：初始化增量数据加载             │
         │  - 获取交易日列表 (start_date ~ end_date)           │
         │  - 调用 on_before_execute_tagging() 钩子            │
         └─────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────────────────────────────┐
         │ Phase 2: 标签计算 (_execute_tagging)                │
         │  对每个 as_of_date in trading_dates：               │
         │    • 调用 TagWorkerDataManager.filter_data_to_date  │
         │    • 对每个 TagDefinition 调用 calculate_tag()      │
         │    • 收集返回的 tag values                          │
         └─────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────────────────────────────┐
         │ Phase 3: 后处理 (_postprocess)                      │
         │  - 批量写入 tag_value 表                            │
         │  - 调用 on_after_execute_tagging() 钩子             │
         │  - 返回统计信息（成功/失败、处理日期数等）          │
         └─────────────────────────────────────────────────────┘
```

---

## 数据流设计

### 高层数据流

```text
Settings (userspace/tags/*/settings.py)
    ↓
ScenarioModel / TagModel
    ↓
TagManager.build_jobs()
    ↓
ProcessWorker (多进程)
    ↓
BaseTagWorker.process_entity()
    ↓
TagWorkerDataManager （加载 & 过滤数据）
    ↓
用户实现的 calculate_tag()
    ↓
Database (tag_scenario / tag_definition / tag_value)
```

### 数据加载与过滤

- **Chunk 模式**（use_chunk=True）：
  - 分块加载 K 线数据，最多同时保留 2 个 chunk 的数据
  - 滑动窗口方式在时间轴上前进，控制内存占用
- **全量模式**（use_chunk=False）：
  - 一次性加载所有历史数据到内存

过滤策略（避免「上帝模式」）：

1. TagWorker 调用 `filter_data_to_date(as_of_date)`
2. TagWorkerDataManager 从缓存数据中过滤出截止 `as_of_date` 的历史数据
3. 将过滤后的数据传给 `calculate_tag()`

---

## 配置设计

### 配置结构概览

```python
Settings = {
    "name": "my_scenario",
    "is_enabled": True,
    "recompute": False,
    "target_entity": {"type": "stock_kline_daily"},
    "update_mode": "incremental",  # or "refresh"
    "incremental_required_records_before_as_of_date": 60,
    "core": {...},         # 业务核心参数（可选）
    "performance": {...},  # 性能参数（如 use_chunk, data_chunk_size）
    "tags": [...],         # Tag 定义列表（必需）
}
```

关键点：

- `target_entity`：指定对哪类实体打标签（如日线、周线、财务等）
- `update_mode`：
  - `incremental`：从上次计算日期的下一日开始增量计算
  - `refresh`：从默认开始日期全量重算
- `performance.use_chunk` / `performance.data_chunk_size`：控制数据加载策略

---

## 多进程执行设计

### Job 分割策略

- **单 entity 单 job**：
  - 每个 job 只处理一个实体（如一只股票）的完整历史
  - 好处：内存可控、失败隔离清晰、批量写入方便

### Worker 数量决策

- 根据 job 数量和 `performance.max_workers` 决定实际进程数：
  - 小量 job：进程数小，避免进程开销浪费
  - 大量 job：进程数接近 CPU 核心数

### 执行模式

- 使用 Worker 模块的 **QUEUE 模式**：
  - 持续填充进程池，完成一个 job 立即启动下一个
  - 适合 Tag 这类 CPU 密集型任务

---

## 职责边界

### 组件职责矩阵（简要）

| 功能             | Settings | TagWorker | BaseTagWorker | TagManager | TagWorkerDataManager |
|------------------|----------|-----------|---------------|------------|----------------------|
| 定义配置         | ✅        | ❌         | ❌             | ❌          | ❌                    |
| 场景发现与管理   | ❌        | ❌         | ❌             | ✅          | ❌                    |
| 实现计算逻辑     | ❌        | ✅         | ❌             | ❌          | ❌                    |
| 执行流程（子进程）| ❌       | ❌         | ✅             | ❌          | ❌                    |
| 多进程调度       | ❌        | ❌         | ❌             | ✅          | ❌                    |
| 数据加载与过滤   | ❌        | ❌         | ❌             | ❌          | ✅                    |

---

## 设计原则

1. **职责单一**：Settings 只定义配置，TagWorker 只实现业务逻辑，Manager 只负责调度
2. **配置驱动**：行为尽量由配置决定，而非硬编码
3. **可扩展性**：通过钩子与 helper 支持复杂业务逻辑
4. **避免「上帝模式」**：框架强制数据过滤到 `as_of_date`
5. **资源可控**：以 entity 为粒度分割 job，结合 Chunk 模式控制内存

---

## 文件组织

```text
core/modules/tag/
└── core/
    ├── base_tag_worker.py          # 框架基类
    ├── tag_manager.py              # 场景管理器
    ├── enums.py                    # 枚举定义
    ├── config.py                   # 全局配置
    ├── models/
    │   ├── scenario_model.py
    │   └── tag_model.py
    └── components/
        ├── helper/
        │   ├── job_helper.py
        │   └── tag_helper.py
        └── tag_worker_helper/
            └── tag_worker_data_manager.py
```

用户空间：

```text
userspace/tags/
└── my_scenario/
    ├── settings.py
    └── tag_worker.py
```

