# Tag 系统设计文档

**最后更新**: 2026-01-02  
**设计者**: System Architecture Team

---

## 📋 目录

1. [概述](#概述)
2. [数据模型设计](#数据模型设计)
3. [核心组件](#核心组件)
4. [配置设计](#配置设计)
5. [执行流程](#执行流程)
6. [多进程执行设计](#多进程执行设计)
7. [职责边界](#职责边界)
8. [设计原则](#设计原则)
9. [关键设计决策](#关键设计决策)
10. [文件组织](#文件组织)

---

## 概述

Tag 系统是一个用于预计算和存储实体属性/状态的框架。系统采用配置驱动的方式，允许用户通过 Python 配置文件定义业务场景（Scenario），每个场景可以产生多个标签（Tag）。

### 核心概念

- **业务场景（Scenario）**：一个业务逻辑单元，对应一个 TagWorker 和一个 Settings 配置
  - 例如：市值分类（`market_value`）
  - 一个 Scenario 可以产生多个 Tags

- **标签定义（Tag Definition）**：Scenario 产生的具体标签
  - 例如：大市值股票（`large_market_value`）、小市值股票（`small_market_value`）
  - 属于某个 Scenario

- **标签值（Tag Value）**：标签的实际计算结果
  - 存储实体在某个日期的标签值
  - 引用 Tag Definition

### 系统架构

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

**设计要点**：
- 一个 Scenario 可以产生多个 Tag Definitions
- 标签名在同一 Scenario 内唯一

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
| `value` | TEXT | 标签值（字符串，由策略自己解析） |
| `calculated_at` | DATETIME | 计算时间 |

**主键**：
- `PRIMARY KEY (entity_id, tag_definition_id, as_of_date)`

**索引**：
- `INDEX idx_entity_date (entity_id, as_of_date)`：核心查询
- `INDEX idx_tag_date (tag_definition_id, as_of_date)`：辅助查询
- `INDEX idx_entity_tag_date (entity_id, tag_definition_id, as_of_date)`：增量计算

**设计要点**：
- 使用复合主键，避免自增 ID
- 支持增量计算（通过 `idx_entity_tag_date` 查询最大 `as_of_date`）
- 支持时间切片标签（`start_date`, `end_date`）

### 数据模型关系图

```
tag_scenario
├─ id: 1
├─ name: "market_value"
└─ ...

tag_definition
├─ id: 10, scenario_id: 1, name: "large_market_value"
├─ id: 11, scenario_id: 1, name: "small_market_value"
└─ ...

tag_value
├─ entity_id: "000001.SZ", tag_definition_id: 10, as_of_date: "2025-12-19", value: "1"
├─ entity_id: "000002.SZ", tag_definition_id: 10, as_of_date: "2025-12-19", value: "1"
└─ ...
```

---

## 核心组件

### 1. Settings (`settings.py`)

**位置**：`app/core_modules/tag/scenarios/<scenario_name>/settings.py`

**职责**：定义业务场景和标签的配置信息

**配置结构**：

> **注意**：详细的配置结构请参考 `app/core_modules/tag/scenarios/example_settings.py`，该文件包含完整的配置示例和每个属性的详细解释。

主要配置项：
- `is_enabled`: 是否启用该 Scenario
- `name`: 业务场景唯一代码（必须）
- `recompute`: 是否重新生成所有tags（必须）
- `target_entity`: 目标实体类型配置（必须）
- `required_entities`: 需要的其他实体（可选）
- `update_mode`: 更新模式（可选，默认 INCREMENTAL）
- `core`: 业务核心参数（可选）
- `performance`: 性能配置（可选）
- `tags`: Tag 级别配置列表（必须）

**责任边界**：
- ✅ 定义配置结构
- ✅ 声明 Scenario 和 Tag 的元信息
- ✅ 声明计算参数和性能配置
- ❌ 不负责执行计算（由 TagWorker 负责）

### 2. TagWorker (`tag_worker.py`)

**位置**：`app/core_modules/tag/scenarios/<scenario_name>/tag_worker.py`

**职责**：实现业务场景的计算逻辑（子进程 worker）

**命名说明**：
- **文件名**：`tag_worker.py`（明确表示这是子进程 worker，会在子进程中实例化）
- **类名**：`XxxTagWorker`（例如：`MomentumTagWorker`，明确表示这是 tag worker）

**实现示例**：

```python
from app.core.modules.tag.core.base_tag_worker import BaseTagWorker
from app.core.modules.tag.core.models.tag_model import TagModel
from typing import Dict, Any, Optional

class MomentumTagWorker(BaseTagWorker):
    """动量因子 TagWorker（在子进程中实例化）"""
    
    def calculate_tag(
        self,
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_definition: TagModel
    ) -> Optional[Dict[str, Any]]:
        """
        计算 tag
        
        这个 TagWorker 可以为多个 tag 提供计算：
        - momentum_60_days: 60天动量
        """
        # 访问 entity 信息
        entity_id = self.entity['id']
        entity_type = self.entity['type']
        
        # 访问配置信息
        core_config = self.config['core']
        performance_config = self.config['performance']
        
        # 访问 tag 定义信息
        tag_name = tag_definition.tag_name
        tag_description = tag_definition.description  # 重要！
        tag_id = tag_definition.id
        
        # 访问历史数据（结构根据 settings 配置保持一致）
        daily_klines = historical_data['klines']['daily']
        corporate_finance = historical_data.get('corporate_finance', [])
        
        # 使用 tracker 存储临时状态
        if 'last_month' not in self.tracker:
            self.tracker['last_month'] = None
        
        # 实现计算逻辑
        # ...
        
        return {"value": "some_value"}
```

**责任边界**：
- ✅ 实现 `calculate_tag()` 方法（必需）
- ✅ 实现业务场景的计算逻辑
- ✅ 一个 TagWorker 可以为多个 Tags 提供计算
- ✅ 在子进程中实例化，可以使用 `self.tracker` 等实例变量
- ✅ 数据加载由 `TagWorkerDataManager` 自动处理，无需重写
- ❌ 不负责文件管理（由 TagManager 负责）

### 3. BaseTagWorker (`base_tag_worker.py`)

**位置**：`app/core_modules/tag/core/base_tag_worker.py`

**职责**：框架基类，提供 TagWorker 的基础功能和框架支持

**核心功能**：

1. **执行流程**
   - `process_entity()`: 子进程 worker 方法（处理单个 entity）
     - `_preprocess()`: 预处理（获取交易日列表）
     - `_execute_tagging()`: 执行标签计算（遍历日期和tags）
     - `_postprocess()`: 后处理（批量保存结果）

2. **数据归类（只读数据）**
   - `self.entity`: `{'id': str, 'type': str}` - entity信息
   - `self.scenario`: `{'name': str, 'update_mode': TagUpdateMode}` - scenario信息
   - `self.job`: `{'start_date': str, 'end_date': str}` - job信息
   - `self.config`: `{'core': dict, 'performance': dict}` - 配置信息
   - `self.tag_definitions`: `List[TagModel]` - tag定义列表

3. **可写状态**
   - `self.tracker`: `dict` - 用于存储计算过程中的临时状态

4. **钩子函数（用户可重写）**
   - `on_init()`: 初始化钩子（无参数）
   - `on_before_execute_tagging()`: 执行前钩子（无参数）
   - `calculate_tag(as_of_date, historical_data, tag_definition)`: 计算tag（必需实现）
   - `on_tag_created(as_of_date, tag_definition, tag_value)`: Tag创建后钩子
   - `on_as_of_date_calculate_complete(as_of_date)`: 每个日期计算完成钩子
   - `on_calculate_error(as_of_date, error, tag_definition)`: 计算错误钩子
   - `on_after_execute_tagging(result)`: 执行后钩子

**接口设计原则**：
- 最小化参数：只传递核心参数，其他信息通过 `self` 访问
- 统一使用对象：使用 `tag_definition` 对象而非字符串
- 数据加载细节由 `TagWorkerDataManager` 负责

**责任边界**：
- ✅ 定义 tag 计算的生命周期流程
- ✅ 提供钩子函数供用户实现业务逻辑
- ✅ 管理 tag values 的批量保存
- ✅ 包含 tracker 等子进程状态管理
- ❌ 不负责业务计算逻辑（由 TagWorker 实现）
- ❌ 不负责数据加载细节（由 TagWorkerDataManager 负责）
- ❌ 不负责文件发现和管理（由 TagManager 负责）
- ❌ 不负责多进程调度（由 TagManager 负责）

### 4. TagWorkerDataManager (`tag_worker_data_manager.py`)

**位置**：`app/core_modules/tag/core/components/tag_worker_helper/tag_worker_data_manager.py`

**职责**：子进程数据管理器，负责所有数据加载、缓存、过滤逻辑

**核心功能**：

1. **数据需求解析**
   - 从 `settings` 自动解析 `target_entity` 和 `required_entities`
   - 提取 `base_term`, `required_terms`, `required_data`
   - 提取 `data_slice_size` 配置

2. **数据加载和缓存**
   - 滑动窗口策略：保持最多 2 个 chunk 的 klines 数据
   - 按记录数切片加载（默认 500 条/切片）
   - `required_data` 全量加载到 as_of_date（不做chunk）

3. **数据过滤**
   - `filter_data_to_date(as_of_date)`: 过滤数据到指定日期（避免"上帝模式"）
   - 返回从开始到 as_of_date 的所有历史数据

4. **交易日获取**
   - `get_trading_dates(start_date, end_date)`: 获取交易日列表

**使用方式**：
```python
# 在 BaseTagWorker.__init__ 中初始化
self.tag_worker_data_manager = TagWorkerDataManager(
    entity_id=self.entity['id'],
    entity_type=self.entity['type'],
    settings=self.settings,
    data_mgr=self.data_mgr
)

# 在 process_entity 中使用
historical_data = self.tag_worker_data_manager.filter_data_to_date(as_of_date)
```

**责任边界**：
- ✅ 从 settings 解析数据需求
- ✅ 管理数据缓存（滑动窗口，最多2个chunk）
- ✅ 提供数据加载和过滤接口
- ✅ 保证数据加载的一致性（根据 settings 配置）
- ❌ 不负责业务计算逻辑

### 5. TagManager (`tag_manager.py`)

**位置**：`app/core_modules/tag/core/tag_manager.py`

**职责**：统一管理所有业务场景（按业务场景名管理）

**核心功能**：

1. **发现和注册**
   - `_discover_and_register_workers()`: 发现所有业务场景
   - `register_scenario()`: 注册 scenario（统一入口）

2. **管理接口**
   - `run(scenario_name=None)`: 执行所有或单个 scenario
   - `get_worker(scenario_name)`: 获取指定 scenario 的 worker 类
   - `get_worker_instance(scenario_name)`: 获取 worker 实例（自动创建并缓存）
   - `list_scenarios()`: 列出所有 scenario 名称
   - `reload()`: 重新发现所有 workers

3. **多进程调度**
   - `_execute_scenario()`: 执行单个 scenario 的多进程计算
   - `_build_entity_jobs()`: 为每个 entity 创建 job
   - `_decide_max_workers()`: 根据 job 数量决定进程数

**责任边界**：
- ✅ 发现所有业务场景（遍历 scenarios 目录）
- ✅ 检查 tag_worker.py 文件存在性
- ✅ 检查 settings.py 文件存在性
- ✅ 检查 worker 是否启用（早期过滤）
- ✅ 加载 worker 类
- ✅ 管理 worker 实例（按业务场景名）
- ✅ 负责多进程调度（job 构建、进程数决定、ProcessWorker 调用）
- ✅ 监控执行进度，收集统计信息
- ❌ 不负责业务计算逻辑（由 TagWorker 负责）

**重要说明**：
- TagManager 管理的是**业务场景**（文件夹名），不是 tag
- 一个业务场景可以产生多个 tags（在 settings.py 的 `tags` 列表中定义）

### 5. SettingsManager (`setting_manager.py`)

---

## 配置设计

### 配置结构

> **详细配置结构请参考** `app/core_modules/tag/scenarios/example_settings.py`，该文件包含完整的配置示例和每个属性的详细解释。

配置采用扁平化结构，主要包含：
- **顶层配置**：`is_enabled`, `name`, `recompute` 等
- **目标实体配置**：`target_entity`（必须）
- **依赖实体配置**：`required_entities`（可选）
- **业务配置**：`core`, `performance`（可选）
- **Tag 配置**：`tags`（必须，至少一个）

---

## 执行流程

### 整体流程

```
1. 用户创建 TagManager 并调用 run()
2. TagManager 自动检查所有 scenarios，读取 settings 和 worker 类
3. 每个 enable 的 scenario 缓存在 manager 里
4. 循环执行每个 scenario（scenario 之间同步操作）：
   a. 确保元信息存在（ensure_metadata）
   b. 确定计算日期范围（根据 update_mode 和已有数据）
   c. 获取实体列表
   d. 构建 jobs 并执行多进程计算
5. 计算流程（子进程中）：
   a. 遍历每个交易日
   b. 对每个日期，获取历史数据并过滤到 as_of_date
   c. 对每个 tag 调用 calculate_tag()
   d. 批量保存结果
```

### TagManager 执行流程

```python
tag_manager = TagManager()
tag_manager.run()  # 或 tag_manager.run(scenario_name="market_value")
```

**TagManager.run() 流程**：

1. **发现和注册 Scenarios**
   - `_discover_and_register_workers()`: 遍历 scenarios 目录，加载 settings 和 worker 类
   - `register_scenario()`: 统一注册入口，验证并存储

2. **验证所有 Settings**

3. **执行每个 TagWorker**
   - 对每个 enable 的 scenario（同步执行）：
     - 获取 executor 实例（自动创建并缓存）
     - 调用 `executor.run()`（确保元信息存在）
     - 执行多进程计算（TagManager 负责调度）
     - 如果出错，记录日志但继续执行其他 scenarios

### TagWorker 执行流程

TagWorker 在子进程中执行，由 TagManager 通过多进程调度。主要流程：

1. **预处理**：获取交易日列表
2. **执行标签计算**：遍历每个日期，对每个 tag 调用 `calculate_tag()`
3. **后处理**：批量保存结果

详细实现请参考 `BaseTagWorker.process_entity()` 方法。

---

## 多进程执行设计

### 设计目标

Tag 系统采用多进程并行执行，以提高计算效率，同时保证内存使用可控。设计参考了 Simulator 的成熟实现。

### 核心设计原则

1. **以 Entity 为单位分割 Jobs**：每个 entity（股票）一个 job，完成完整的 tag 计算后存储
2. **根据 Job 数量决定进程数**：动态决定进程数，最多 10 个进程
3. **主进程负责监控和管理**：主进程只负责任务分发和进度监控
4. **子进程初始化后才读取数据**：保证内存使用可控，进程结束自动释放
5. **最大 Worker 限制**：最多 10 个进程，适合个人电脑环境

### 整体架构

**架构设计**：

```
TagManager.run()
    │
    ├─▶ 1. 发现和注册所有 scenarios
    │
    └─▶ 2. 对每个 scenario：
           │
           ├─▶ a. 确保元信息存在（ensure_metadata）
           │
           ├─▶ b. 确定计算日期范围（根据 update_mode 和已有数据）
           │
           ├─▶ c. 获取实体列表
           │
           ├─▶ d. 分割jobs（每个entity一个job）
           │
           ├─▶ e. 决定进程数（根据job数量）
           │
           ├─▶ f. 创建ProcessWorker（使用QUEUE模式）
           │
           └─▶ g. 执行jobs（子进程中实例化TagWorker，调用process_entity()）
```

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
    }
}
```

**分割逻辑**：
- 每个 entity 一个 job
- Job 包含该 entity 的所有计算信息（tag definitions、配置、日期范围等）
- Job ID 格式：`{entity_id}_{scenario_name}`

### 进程数决定策略

**策略**（参考 TaskExecutor 的实现）：

```python
def _decide_max_workers(job_count: int, max_workers_config: Optional[int] = None) -> int:
    """
    根据job数量决定进程数（最多10个）
    
    策略：
    1. 如果配置了max_workers，使用配置值（但不超过10）
    2. 如果job数量 <= 1，使用1个进程
    3. 如果job数量 <= 5，使用2个进程
    4. 如果job数量 <= 10，使用3个进程
    5. 如果job数量 <= 20，使用5个进程
    6. 如果job数量 <= 50，使用8个进程
    7. 否则使用10个进程（最大）
    """
```

**配置优先级**：
1. 如果 `settings.performance.max_workers` 已配置，优先使用（但不超过最大限制）
2. 否则根据 job 数量自动决定

### 主进程职责（TagManager）

**主进程（TagManager）**：
1. 发现和注册所有 scenarios
2. 对每个 scenario：
   - 确保元信息存在（ensure_metadata）
   - 确定计算日期范围（根据 update_mode 和已有数据）
   - 获取实体列表
   - 分割 jobs（每个 entity 一个 job）
   - 决定进程数
   - 创建 ProcessWorker
   - 监控执行进度
   - 收集结果和统计信息

**不负责**：
- ❌ 不加载数据（由子进程负责）
- ❌ 不执行计算（由子进程负责）
- ❌ 不存储结果（由子进程负责）

### 子进程职责（BaseTagWorker）

**子进程执行方式**：

ProcessWorker 在子进程中实例化 TagWorker 类并调用 `process_entity()` 方法。主要流程：

1. 从 payload 提取信息并初始化 TagWorker
2. 预处理：获取交易日列表
3. 执行标签计算：遍历每个日期，对每个 tag 调用 `calculate_tag()`
4. 后处理：批量存储结果
5. 返回统计信息

详细实现请参考 `BaseTagWorker.process_entity()` 方法。

### 数据加载和过滤策略

#### 数据加载策略

**按需加载（滑动窗口）**：
- 由 `TagWorkerDataManager` 负责数据加载
- 按记录数切片加载（默认 500 条/切片）
- 滑动窗口策略：最多保持 2 个 chunk 的数据在内存中
- `required_data` 全量加载到 as_of_date（不做chunk，因为数据量小）

**内存控制**：
- 每个进程只处理一个 entity
- 数据按需加载，最多保持 2 个 chunk（约 1000 条记录）
- 进程结束自动释放内存

#### 数据过滤策略

**问题**：需要避免"上帝模式"问题（计算时看到未来数据）

**解决方案**：框架层面强制过滤到 `as_of_date`

`TagWorkerDataManager.filter_data_to_date()` 方法确保只返回从开始到 `as_of_date` 的历史数据。在 `calculate_tag` 调用前，框架自动过滤数据，用户无需关心数据过滤，保证计算一致性。

### 执行模式

**使用 QUEUE 模式**（参考 ProcessWorker 的实现）：
- 持续填充进程池，完成一个立即启动下一个
- 适合 CPU 密集型任务
- 充分利用进程池，提高效率

**不使用 BATCH 模式**：
- BATCH 模式适合内存敏感场景
- Tag 系统已经通过单 entity 单进程控制内存，不需要 BATCH 模式

### 错误处理

**单个 Entity 失败不影响其他 Entity**：
- 每个 job 独立执行，互不影响
- 失败时记录错误日志，继续执行其他 jobs
- 返回统计信息（成功数、失败数）

**错误处理策略**：
- 数据加载失败：记录错误，返回失败结果
- 计算失败：调用 `on_calculate_error` 钩子，根据返回值决定是否继续
- 存储失败：记录错误，返回失败结果

### 性能优化

1. **全量加载 + 内存过滤**：
   - 一次加载，多次使用（避免重复 I/O）
   - 内存中过滤，速度快

2. **批量存储**：
   - 收集所有结果后批量写入数据库
   - 减少数据库连接和事务开销

3. **进程池复用**：
   - 使用 ProcessPoolExecutor，进程池复用
   - 完成一个 job 立即启动下一个

4. **内存隔离**：
   - 每个进程独立内存空间
   - 进程结束自动释放，无需手动管理

### 与 Simulator 的对比

| 特性 | Simulator | Tag System |
|------|-----------|------------|
| Job 分割 | 每个 stock 一个 job | 每个 entity 一个 job |
| 进程数决定 | 使用 CPU 核心数 | 根据 job 数量，最多 10 个 |
| 数据加载 | 子进程中加载 | 子进程中加载 |
| 执行模式 | QUEUE 模式 | QUEUE 模式 |
| 最大 worker | CPU 核心数 | 10（可配置） |
| 数据过滤 | 按日期过滤（get_data_of_today） | 按 as_of_date 过滤（_filter_data_to_date） |

### 关键设计决策

#### 1. 为什么使用多进程而不是多线程？

**原因**：
- Tag 计算是 CPU 密集型任务
- 多进程绕过 Python GIL 限制，真正并行执行
- 内存隔离，提高稳定性

#### 2. 为什么最多 10 个进程？

**原因**：
- 适合个人电脑环境（内存压力可控）
- 10 个进程已经能充分利用多核 CPU
- 避免进程过多导致上下文切换开销

#### 3. 为什么在子进程中加载数据？

**原因**：
- 保证内存使用可控（每个进程只加载一个 entity 的数据）
- 进程结束自动释放内存
- 参考 Simulator 的成熟实现

#### 4. 为什么需要数据过滤？

**原因**：
- 全量加载可能导致"上帝模式"问题
- 框架层面过滤保证计算一致性
- 用户无需关心数据过滤细节

#### 5. 为什么使用 QUEUE 模式？

**原因**：
- 持续填充进程池，充分利用资源
- 适合 CPU 密集型任务
- 单 entity 单进程已经控制内存，不需要 BATCH 模式

### 实现要点

1. **复用 ProcessWorker**：直接使用现有的 `ProcessWorker` 类
2. **类实例作为 worker**：TagWorker 类在子进程中实例化，调用 `process_entity()` 方法
3. **Worker Wrapper**：实现 wrapper 函数，在子进程中实例化 TagWorker
4. **数据过滤**：实现 `_filter_data_to_date` 方法（实例方法）
5. **批量存储**：实现 `batch_save_tag_values` 方法（TagService 中或实例方法）
6. **错误处理**：单个 entity 失败不影响其他 entity
7. **Tracker 支持**：`self.tracker` 在子进程中自然存在，可以跨日期使用

### 架构优势

**架构优势**：

1. **职责清晰**：
   - TagManager：主进程逻辑（调度）
   - BaseTagWorker：子进程逻辑（执行）

2. **更自然的面向对象设计**：
   - TagWorker 作为 worker，在子进程中实例化
   - tracker 等实例变量自然存在
   - 不需要静态方法，代码更清晰

3. **更好的扩展性**：
   - 用户自定义 TagWorker 类可以直接使用 tracker
   - 可以重写方法来自定义行为
   - 符合继承和多态的设计原则

4. **更符合 ProcessWorker 的设计**：
   - ProcessWorker 支持传入可实例化的类
   - 在子进程中实例化，避免 pickle 序列化问题

5. **命名更直接**：
   - `BaseTagWorker` 和 `TagWorker` 明确表示这是 worker
   - `tag_worker.py` 文件名明确表示这是子进程 worker
   - 从命名就能看出这是多进程执行相关的类

---

---

## 职责边界

### 组件职责矩阵

| 功能 | Settings | TagWorker | BaseTagWorker | TagManager |
|------|----------|-----------|---------------|------------|
| 定义配置 | ✅ | ❌ | ❌ | ❌ |
| 检查启用状态 | ❌ | ❌ | ❌ | ✅ |
| 实现计算逻辑 | ❌ | ✅ | ❌ | ❌ |
| 加载数据 | ❌ | ❌ | ✅ (TagWorkerDataManager) | ❌ |
| 发现业务场景 | ❌ | ❌ | ❌ | ✅ |
| 管理实例 | ❌ | ❌ | ❌ | ✅ |
| 执行流程（子进程） | ❌ | ❌ | ✅ | ❌ |
| **多进程调度** | ❌ | ❌ | ❌ | ✅ |
| **Job 构建** | ❌ | ❌ | ❌ | ✅ |
| **进程数决定** | ❌ | ❌ | ❌ | ✅ |

### 责任边界总结

**Settings**：
- ✅ 只定义配置
- ❌ 不验证配置
- ❌ 不执行计算

**TagWorker**：
- ✅ 只实现计算逻辑（在子进程中执行）
- ✅ 可以使用 tracker 等实例变量
- ❌ 不管理文件
- ❌ 不验证配置结构

**BaseTagWorker**：
- ✅ 只提供框架支持（子进程执行流程、数据加载）
- ✅ 提供 `process_entity()` 方法作为子进程 worker
- ✅ 包含 tracker 等子进程状态管理
- ❌ 不实现业务逻辑
- ❌ 不负责多进程调度（由 TagManager 负责）

**TagManager**：
- ✅ 只管理业务场景（发现、验证、注册）
- ✅ 负责多进程调度（job 构建、进程数决定、ProcessWorker 调用）
- ✅ 监控执行进度，收集统计信息
- ❌ 不计算（由 TagWorker 负责）

---

## 设计原则

### 1. 职责单一

每个组件只负责自己的职责：
- Settings 只定义配置
- TagWorker 只实现计算
- Manager 只管理
- BaseTagWorker 只提供框架

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

## 关键设计决策

### 1. 为什么采用三层表结构？

**原因**：
- **清晰的数据模型**：Scenario → Definition → Value 三层结构清晰
- **查询更方便**：可以按 Scenario 查询
- **数据一致性更好**：一个 Scenario 的所有 Tags 共享相同的配置

### 2. 为什么 is_enabled 在顶层？

**原因**：
- `is_enabled` 控制整个业务场景是否启用
- 如果 TagWorker 启用，所有 Tags 都会被计算
- 不能只启用一个 Tag 而舍弃另一个（因为 Tag 是业务场景的产物）
- 符合业务逻辑：业务场景是一个整体

### 4. 为什么支持一个 TagWorker 打多个 Tag？

**原因**：
- 业务逻辑复用（如市值分类：大市值、小市值）
- 减少重复代码
- 配置更灵活（共享 worker 配置，独立 tag 配置）

### 5. 为什么 Settings 和 TagWorker 分离？

**原因**：
- 配置与代码分离，便于维护和版本控制
- 支持配置的热更新（未来可能支持）
- 一个 TagWorker 可以打多个 Tag，配置需要独立管理

### 6. 为什么在 TagManager 中检查 is_enabled？

**原因**：
- 早期过滤，避免不必要的 Worker 初始化
- Manager 负责管理，应该知道哪些 Worker 可用
- 职责清晰：Manager 管理，Worker 计算

---

## 文件组织

### 目录结构

```
app/core_modules/tag/
├── base_tag_worker.py          # 框架基类
├── tag_manager.py               # 业务场景管理器
├── enums.py                     # 枚举定义
├── config.py                    # 全局配置
├── docs/
│   └── DESIGN.md               # 本文档
└── scenarios/
    ├── example/                # 示例场景
    │   ├── settings.py
    │   └── tag_worker.py
    ├── market_value/            # 市值分类场景
    │   ├── settings.py
    │   └── tag_worker.py
    └── ...
```

### 重要概念

**业务场景 vs Tag**：
- **业务场景**（文件夹名）：如 `market_value`（市值分类）
- **Tag**（settings 中定义）：如 `large_market_value`, `small_market_value`
- 一个业务场景可以产生多个 tags
- TagManager 管理的是业务场景，不是 tag

---


## 附录

### 枚举定义

**TagUpdateMode**（`app/core_modules/tag/core/enums.py`）：
- `INCREMENTAL`: 增量更新
- `REFRESH`: 全量刷新

详细枚举定义请参考 `app/core_modules/tag/core/enums.py`。

### 全局配置

**app/core_modules/tag/core/config.py**：
```python
# Scenarios 根目录配置
DEFAULT_SCENARIOS_ROOT = "app/core_modules/tag/scenarios"
```

---

**文档结束**
