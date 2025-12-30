# Tag 系统设计文档

**版本**: v2.1  
**最后更新**: 2025-12-19  
**设计者**: System Architecture Team

**重要更新**：
- v2.1: 重构多进程执行架构，明确职责划分（TagManager 负责调度，BaseTagWorker 负责执行）
  - 重命名 `BaseTagCalculator` → `BaseTagWorker`，`base_tag_calculator.py` → `base_tag_worker.py`
  - 重命名用户自定义 `Calculator` → `TagWorker`，`calculator.py` → `tag_worker.py`
  - 使用类实例作为 worker，而非静态方法
- v2.0: 初始设计，包含多进程执行设计

---

## 📋 目录

1. [概述](#概述)
2. [数据模型设计](#数据模型设计)
3. [核心组件](#核心组件)
4. [配置设计](#配置设计)
5. [执行流程](#执行流程)
6. [多进程执行设计](#多进程执行设计)
7. [版本管理](#版本管理)
8. [职责边界](#职责边界)
9. [设计原则](#设计原则)
10. [关键设计决策](#关键设计决策)
11. [文件组织](#文件组织)

---

## 概述

Tag 系统是一个用于预计算和存储实体属性/状态的框架。系统采用配置驱动的方式，允许用户通过 Python 配置文件定义业务场景（Scenario），每个场景可以产生多个标签（Tag）。

### 核心概念

- **业务场景（Scenario）**：一个业务逻辑单元，对应一个 TagWorker 和一个 Settings 配置
  - 例如：市值分类（`market_value`）
  - 一个 Scenario 可以产生多个 Tags
  - **版本（Version）**在 Scenario 级别管理

- **标签定义（Tag Definition）**：Scenario 产生的具体标签
  - 例如：大市值股票（`large_market_value`）、小市值股票（`small_market_value`）
  - 属于某个 Scenario，共享 Scenario 的版本

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

**用途**：存储业务场景的元信息和版本管理

**表结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGINT | 自增主键 |
| `name` | VARCHAR(64) | 业务场景唯一代码（如 `market_value`） |
| `display_name` | VARCHAR(128) | 业务场景显示名称 |
| `version` | VARCHAR(32) | **版本号**（如 `1.0`, `2.0`），代表算法版本 |
| `description` | TEXT | 业务场景描述 |
| `is_legacy` | TINYINT(1) | 是否已废弃（0=active, 1=legacy） |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

**索引**：
- `UNIQUE KEY uk_name_version (name, version)`：同一场景的不同版本
- `INDEX idx_name (name)`：按场景名查询
- `INDEX idx_is_legacy (is_legacy)`：查询 active/legacy 版本

**设计要点**：
- **Version 在 Scenario 级别**：代表整个业务场景的算法版本
- 一个 Scenario 可以有多个版本（历史版本保留为 legacy）
- `is_legacy` 用于标记旧版本（0=active, 1=legacy）

### 2. tag_definition 表

**用途**：存储标签定义，属于某个 Scenario

**表结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGINT | 自增主键 |
| `scenario_id` | BIGINT | 外键 → `tag_scenario.id` |
| `scenario_version` | VARCHAR(32) | **冗余字段**：Scenario 版本（用于查询优化） |
| `name` | VARCHAR(64) | 标签唯一代码（如 `large_market_value`） |
| `display_name` | VARCHAR(128) | 标签显示名称 |
| `description` | TEXT | 标签描述 |
| `is_legacy` | TINYINT(1) | **冗余字段**：是否已废弃（用于查询优化） |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

**索引**：
- `UNIQUE KEY uk_scenario_name (scenario_id, name)`：同一 Scenario 下标签名唯一
- `INDEX idx_scenario_id (scenario_id)`：按 Scenario 查询
- `INDEX idx_scenario_version (scenario_version, is_legacy)`：查询优化

**设计要点**：
- 一个 Scenario 可以产生多个 Tag Definitions
- Tag Definition 共享 Scenario 的版本
- 标签名在同一 Scenario 内唯一
- `scenario_version` 和 `is_legacy` 是冗余字段，用于查询优化

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
├─ version: "1.0"
├─ is_legacy: 0
└─ ...

tag_definition
├─ id: 10, scenario_id: 1, name: "large_market_value", scenario_version: "1.0"
├─ id: 11, scenario_id: 1, name: "small_market_value", scenario_version: "1.0"
└─ ...

tag_value
├─ entity_id: "000001.SZ", tag_definition_id: 10, as_of_date: "2025-12-19", value: "1"
├─ entity_id: "000002.SZ", tag_definition_id: 10, as_of_date: "2025-12-19", value: "1"
└─ ...
```

---

## 核心组件

### 1. Settings (`settings.py`)

**位置**：`app/tag/scenarios/<scenario_name>/settings.py`

**职责**：定义业务场景和标签的配置信息

**配置结构**：

```python
from app.tag.enums import KlineTerm, UpdateMode, VersionChangeAction

Settings = {
    # 顶层配置
    "is_enabled": True,  # 是否启用该 Scenario
    
    # Scenario 级别配置（对应 tag_scenario 表）
    "scenario": {
        "name": "market_value",  # 业务场景唯一代码
        "display_name": "市值分类",  # 显示名称
        "description": "按市值阈值给股票打大小市值标签",
        "version": "1.0",  # 版本号
        "on_version_change": VersionChangeAction.REFRESH_SCENARIO.value,  # 版本变更处理
    },
    
    # Worker 级别配置（计算逻辑相关，不存储到数据库）
    "calculator": {  # 注意：配置键名保持 "calculator" 不变，只是类名改为 Worker
        "base_term": KlineTerm.DAILY.value,  # 基础周期
        "required_terms": [],  # 需要的其他周期
        "required_data": [],  # 需要的数据源
        "start_date": "",  # 计算开始日期（可选）
        "end_date": "",  # 计算结束日期（可选）
        "core": {
            "mkv_threshold": 1e10,  # 市值阈值
        },
        "performance": {
            "max_workers": 8,  # 最大并发数
            "update_mode": UpdateMode.INCREMENTAL.value,  # 更新模式
        },
    },
    
    # Tag 级别配置（对应 tag_definition 表，一个 Scenario 下多个 tags）
    "tags": [
        {
            "name": "large_market_value",
            "display_name": "大市值股票",
            "description": "市值大于阈值的股票",
        },
        {
            "name": "small_market_value",
            "display_name": "小市值股票",
            "description": "市值小于等于阈值的股票",
        },
    ],
}
```

**责任边界**：
- ✅ 定义配置结构
- ✅ 声明 Scenario 和 Tag 的元信息
- ✅ 声明计算参数和性能配置
- ❌ 不负责验证配置（由 SettingsValidator 负责）
- ❌ 不负责执行计算（由 TagWorker 负责）

### 2. TagWorker (`tag_worker.py`)

**位置**：`app/tag/scenarios/<scenario_name>/tag_worker.py`

**职责**：实现业务场景的计算逻辑（子进程 worker）

**命名说明**：
- **文件名**：`tag_worker.py`（明确表示这是子进程 worker，会在子进程中实例化）
- **类名**：`XxxTagWorker`（例如：`MomentumTagWorker`，明确表示这是 tag worker）

**实现示例**：

```python
from app.tag.base_tag_worker import BaseTagWorker
from typing import Dict, Any, Optional

class MomentumTagWorker(BaseTagWorker):
    """动量因子 TagWorker（在子进程中实例化）"""
    
    def calculate_tag(
        self, 
        entity_id: str,
        entity_type: str,
        as_of_date: str, 
        historical_data: Dict[str, Any],
        tag_config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        计算 tag
        
        这个 TagWorker 可以为多个 tag 提供计算：
        - momentum_60_days: 60天动量
        """
        # 获取配置参数（所有 tags 共享 worker 的 core 配置）
        mkv_threshold = tag_config["core"]["mkv_threshold"]
        tag_name = tag_config["tag_meta"]["name"]
        
        # 实现计算逻辑
        market_value = historical_data.get("market_value", {}).get("current", 0)
        
        if tag_name == "large_market_value":
            if market_value > mkv_threshold:
                return {"value": "1"}
        elif tag_name == "small_market_value":
            if market_value <= mkv_threshold:
                return {"value": "1"}
        
        return None
```

**责任边界**：
- ✅ 实现 `calculate_tag()` 方法（必需）
- ✅ 实现业务场景的计算逻辑
- ✅ 一个 TagWorker 可以为多个 Tags 提供计算
- ✅ 在子进程中实例化，可以使用 `self.tracker` 等实例变量
- ✅ 可选：重写 `load_entity_data()` 支持自定义数据源
- ❌ 不负责配置验证（由 SettingsValidator 负责）
- ❌ 不负责文件管理（由 TagManager 负责）

### 3. BaseTagWorker (`base_tag_worker.py`)

**位置**：`app/tag/base_tag_worker.py`

**职责**：框架基类，提供 TagWorker 的基础功能和框架支持

**核心功能**：

1. **执行流程**
   - `run()`: TagWorker 入口函数（确保元信息存在）
   - `process_entity()`: 子进程 worker 方法（处理单个 entity）
   - `ensure_metadata()`: 确保元信息存在
   - `renew_or_create_values()`: 处理版本变更和更新模式

2. **元信息管理**
   - `ensure_scenario()`: 确保 scenario 存在
   - `ensure_tags()`: 确保 tag definitions 存在

3. **版本变更处理**
   - `handle_version_change()`: 处理版本变更
   - `handle_update_mode()`: 根据版本变更结果和 update_mode 计算（只返回日期范围，不执行多进程）
   - `cleanup_legacy_versions()`: 清理旧的 legacy versions

4. **数据加载**
   - `load_entity_data()`: 加载实体历史数据（默认支持股票，可扩展）

5. **钩子函数**
   - `on_init()`: 初始化钩子
   - `on_tag_created()`: Tag 创建后钩子
   - `on_calculate_error()`: 计算错误钩子
   - `should_continue_on_error()`: 错误时是否继续
   - `on_finish()`: 完成钩子

**责任边界**：
- ✅ 执行流程管理（子进程）
- ✅ 元信息管理
- ✅ 版本变更处理
- ✅ 数据加载（默认实现）
- ✅ 钩子函数框架支持
- ✅ 提供 `process_entity()` 方法作为子进程 worker
- ✅ 包含 tracker 等子进程状态管理
- ❌ 不负责业务计算逻辑（由 TagWorker 实现）
- ❌ 不负责文件发现和管理（由 TagManager 负责）
- ❌ 不负责多进程调度（由 TagManager 负责）

### 4. TagManager (`tag_manager.py`)

**位置**：`app/tag/tag_manager.py`

**职责**：统一管理所有业务场景（按业务场景名管理）

**核心功能**：

1. **发现和注册**
   - `_discover_and_register_workers()`: 发现所有业务场景（重命名自 _discover_and_register_calculators）
   - `register_scenario()`: 注册 scenario（统一入口）
   - `_validate_all_settings_and_remove_invalid()`: 验证所有 settings

2. **管理接口**
   - `run(scenario_name=None)`: 执行所有或单个 scenario
   - `get_worker(scenario_name)`: 获取指定 scenario 的 worker 类（重命名自 get_calculator）
   - `get_worker_instance(scenario_name)`: 获取 worker 实例（自动创建并缓存，重命名自 get_calculator_instance）
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
- ❌ 不负责配置验证（由 SettingsValidator 负责）
- ❌ 不负责业务计算逻辑（由 TagWorker 负责）

**重要说明**：
- TagManager 管理的是**业务场景**（文件夹名），不是 tag
- 一个业务场景可以产生多个 tags（在 settings.py 的 `tags` 列表中定义）

### 5. SettingsValidator (`settings_validator.py`)

**位置**：`app/tag/settings_validator.py`

**职责**：提供静态方法用于验证 Tag Worker 的 settings 配置

**核心方法**：
- `validate_scenario_fields()`: 验证 scenario 字段
- `validate_calculator_fields()`: 验证 calculator 字段
- `validate_tags_fields()`: 验证 tags 字段
- `validate_enums()`: 验证枚举值
- `validate_all()`: 完整验证流程

### 6. SettingsProcessor (`settings_processor.py`)

**位置**：`app/tag/settings_processor.py`

**职责**：提供静态方法用于读取、处理和合并 Tag Worker 的 settings 配置

**核心方法**：
- `read_settings_file()`: 读取 settings 文件
- `apply_defaults()`: 应用默认值
- `load_and_process_settings()`: 完整加载和处理流程
- `merge_tag_config()`: 合并 calculator 和 tag 配置
- `process_tags_config()`: 处理 tags 配置列表
- `extract_calculator_config()`: 提取配置到字典

---

## 配置设计

### 配置结构

配置采用三层结构：Scenario 级别、Worker 级别和 Tag 级别。

```python
Settings = {
    "is_enabled": True,  # 顶层：是否启用
    "scenario": {
        # Scenario 级别配置（对应 tag_scenario 表）
    },
    "calculator": {
        # Worker 级别配置（计算逻辑相关，注意：配置键名保持 "calculator" 不变）
    },
    "tags": [
        # Tag 级别配置（对应 tag_definition 表，多个 tags）
    ],
}
```

### Scenario 级别配置

| 配置项 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| `name` | str | ✅ | 业务场景唯一代码 |
| `version` | str | ✅ | 版本号（如 `1.0`） |
| `display_name` | str | ❌ | 显示名称（默认同 name） |
| `description` | str | ❌ | 描述（默认 `""`） |
| `on_version_change` | str | ❌ | 版本变更处理（默认 `REFRESH_SCENARIO`） |

### Worker 级别配置（配置键名：calculator）

| 配置项 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| `base_term` | str | ✅ | 基础周期（枚举：`daily`, `weekly`, `monthly`） |
| `required_terms` | list | ❌ | 需要的其他周期（默认 `[]`） |
| `required_data` | list | ❌ | 需要的数据源（默认 `[]`） |
| `start_date` | str | ❌ | 计算开始日期（YYYYMMDD，默认系统默认值） |
| `end_date` | str | ❌ | 计算结束日期（YYYYMMDD，默认最新交易日） |
| `core` | dict | ❌ | 共享的计算参数（默认 `{}`） |
| `performance.max_workers` | int | ❌ | 最大并发数（默认自动分配） |
| `performance.update_mode` | str | ❌ | 更新模式（`incremental` 或 `refresh`，默认 `incremental`） |

### Tag 级别配置

| 配置项 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| `name` | str | ✅ | 标签唯一代码 |
| `display_name` | str | ✅ | 标签显示名称 |
| `description` | str | ❌ | 标签描述（默认 `""`） |

**注意**：
- Tag 级别**不支持** `core` 和 `performance`，只在 Worker 级别配置
- 所有 Tags 共享 Worker 的 `core` 和 `performance` 配置
- 简化设计：避免配置复杂性，所有 tags 使用相同的计算参数和性能配置

### 配置验证

**顶层验证**：
- `is_enabled`: 必需（在 TagManager 中检查）

**Scenario 级别验证**：
- `scenario.name`: 必需
- `scenario.version`: 必需
- `scenario.on_version_change`: 可选，必须在枚举中

**Worker 级别验证**（配置键名：calculator）：
- `calculator.base_term`: 必需，必须在枚举中
- `calculator.performance.update_mode`: 可选，必须在枚举中

**Tag 级别验证**：
- `tags`: 必需，至少一个 tag
- 每个 tag: `name`, `display_name` 必需
- Tag name 在同一 Scenario 内唯一

---

## 执行流程

### 整体流程

```
1. 用户创建 TagManager 并调用 run()
2. TagManager 自动检查所有 scenarios，读取类和 settings
3. Validation 后，每个 enable 的 worker 缓存在 manager 里
4. 循环执行每个 worker 的入口函数（scenario 之间同步操作）
5. 每个 worker 的入口函数：
   a. 确保元信息存在（ensure_metadata）
   b. 处理版本变更和更新模式（renew_or_create_values）
6. 版本变更处理：
   a. 对比 version
   b. 如果 version 不同，进入 on_version_change 流程
   c. 如果 version 相同，按 update_mode 计算
7. 计算流程：
   a. 确定计算日期范围
   b. 获取实体列表
   c. 对每个实体和每个日期计算 tags
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
   - `_validate_all_settings_and_remove_invalid()`: 验证枚举值等，移除验证失败的 scenarios

3. **执行每个 TagWorker**
   - 对每个 enable 的 scenario（同步执行）：
     - 获取 executor 实例（自动创建并缓存）
     - 调用 `executor.run()`（确保元信息存在）
     - 执行多进程计算（TagManager 负责调度）
     - 如果出错，记录日志但继续执行其他 scenarios

### TagWorker 执行流程

```python
def run(self):
    # 1. 确保元信息存在
    scenario, tag_defs = self.ensure_metadata()
    
    # 2. 处理版本变更和更新模式
    self.renew_or_create_values()
```

#### ensure_metadata()

```python
def ensure_metadata(self):
    # 1. 确保 scenario 存在
    scenario = self.ensure_scenario()
    
    # 2. 确保 tag definitions 存在
    tag_defs = self.ensure_tags(scenario)
    
    return scenario, tag_defs
```

**ensure_scenario()**：
- 查询数据库中该 scenario name 的所有版本
- 如果 settings.version 已存在：返回该 scenario
- 如果 settings.version 不存在：创建新的 scenario

**ensure_tags()**：
- 检查该 scenario 下的 tag definitions 是否存在
- 如果不存在，创建新的 tag definitions

#### renew_or_create_values()

```python
def renew_or_create_values(self):
    # 1. 处理版本变更
    version_action = self.handle_version_change()
    
    # 2. 根据版本变更结果和 update_mode 计算
    self.handle_update_mode(version_action)
```

**handle_version_change()**：
- 查询数据库中该 scenario name 的所有版本
- 如果 settings.version 在数据库中已存在且 is_legacy=0（active）：`version_action = "NO_CHANGE"`
- 如果 settings.version 在数据库中已存在但 is_legacy=1（legacy）：处理版本回退（见[版本管理](#版本管理)）
- 如果 settings.version 不在数据库中：
  - `version_action = on_version_change`（REFRESH_SCENARIO 或 NEW_SCENARIO）
  - 如果是 NEW_SCENARIO：创建新 scenario，标记旧的为 legacy，清理旧版本
  - 如果是 REFRESH_SCENARIO：更新 scenario，删除旧的 tag definitions 和 tag values，创建新的

**handle_update_mode(version_action)**：
- 如果 `version_action == "NO_CHANGE"`：按 `update_mode` 计算（INCREMENTAL 或 REFRESH）
- 如果 `version_action == "ROLLBACK"`：按照该版本的 update_mode 继续
- 如果 `version_action == "NEW_SCENARIO"` 或 `"REFRESH_SCENARIO"`：重新计算所有 tags

### 计算流程

```python
def handle_update_mode(self, version_action: str):
    # 1. 确定计算日期范围（根据 version_action 和 update_mode）
    # 2. 获取实体列表
    # 3. 对每个实体：
    #    a. 加载历史数据（调用 self.load_entity_data）
    #    b. 对每个 tag：
    #        * 对每个日期（从 start_date 到 end_date）：
    #            - 调用 self.calculate_tag()
    #            - 如果返回结果，保存 tag 值（调用 self.save_tag_value）
    #    c. 如果出错，调用 self.on_calculate_error()
    #    d. 调用 self.on_finish()
```

---

## 多进程执行设计

### 设计目标

Tag 系统采用多进程并行执行，以提高计算效率，同时保证内存使用可控。设计参考了 Simulator 的成熟实现。

### 架构演进

**v2.0（旧架构）**：
- BaseTagCalculator 负责多进程调度和执行
- 使用静态方法作为 executor
- 职责混乱，主进程和子进程逻辑混在一起

**v2.1（新架构）**：
- TagManager 负责多进程调度（主进程逻辑）
- BaseTagWorker 负责执行（子进程逻辑）
- 使用类实例作为 worker，更符合面向对象设计
- 职责清晰，易于维护和扩展

**重构原因**：
1. 职责划分不清晰：BaseTagCalculator 承担了过多职责
2. 不符合面向对象设计：使用静态方法而非类实例
3. 扩展性差：tracker 等状态管理不够自然
4. 不符合 ProcessWorker 的设计理念：应该传入可实例化的类
5. 命名不够直接：Calculator 不能明确表示这是子进程 worker

### 核心设计原则

1. **以 Entity 为单位分割 Jobs**：每个 entity（股票）一个 job，完成完整的 tag 计算后存储
2. **根据 Job 数量决定进程数**：动态决定进程数，最多 10 个进程
3. **主进程负责监控和管理**：主进程只负责任务分发和进度监控
4. **子进程初始化后才读取数据**：保证内存使用可控，进程结束自动释放
5. **最大 Worker 限制**：最多 10 个进程，适合个人电脑环境

### 整体架构

**新架构（重构后）**：

```
TagManager.run()
    │
    ├─▶ 1. 发现和验证所有 scenarios
    │
    └─▶ 2. 对每个 scenario：
           │
           ├─▶ a. 获取 worker 实例
           │
           ├─▶ b. 调用 worker.run()
           │      │
           │      └─▶ ensure_metadata() + renew_or_create_values()
           │
           └─▶ c. 执行多进程计算（TagManager 负责）
                  │
                  ├─▶ 确定计算日期范围（调用 worker.handle_update_mode()）
                  │
                  ├─▶ 获取实体列表
                  │
                  ├─▶ 分割jobs（每个entity一个job）
                  │
                  ├─▶ 决定进程数（根据job数量，最多10个）
                  │
                  ├─▶ 创建ProcessWorker（使用QUEUE模式）
                  │
                  └─▶ 执行jobs（子进程中实例化TagWorker，调用process_entity()）
```

**旧架构（当前实现，需要重构）**：

```
BaseTagWorker.handle_update_mode()  # 注意：旧架构中这个方法包含多进程调度，需要移除
    │
    ├─▶ 1. 确定计算日期范围
    │
    ├─▶ 2. 获取实体列表
    │
    ├─▶ 3. 分割jobs（每个entity一个job）
    │
    ├─▶ 4. 决定进程数（根据job数量，最多10个）
    │
    ├─▶ 5. 创建ProcessWorker（使用QUEUE模式）
    │
    └─▶ 6. 执行jobs（子进程中加载数据、计算、存储）
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
        'scenario_version': self.scenario_version,
        'tag_definitions': tag_defs,  # 该scenario的所有tag definitions
        'tag_configs': self.tags_config,  # 所有tag的配置
        'start_date': start_date,
        'end_date': end_date,
        'base_term': self.base_term,
        'required_terms': self.required_terms,
        'required_data': self.required_data,
        'core': self.core,
        'worker_class': self.__class__,  # 用于子进程实例化（重命名自 calculator_class/executor_class）
        'settings_path': self.settings_path,  # 用于子进程加载配置
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
1. 如果 `settings.calculator.performance.max_workers` 已配置，优先使用（但不超过 10）
   - 注意：配置键名保持 `calculator` 不变，只是类名改为 Worker
2. 否则根据 job 数量自动决定

### 主进程职责（TagManager）

**主进程（TagManager）**：
1. 发现和验证所有 scenarios
2. 对每个 scenario：
   - 获取 worker 实例
   - 调用 `worker.run()`（确保元信息存在）
   - 确定计算日期范围（调用 `worker.handle_update_mode()` 获取日期范围，但不执行多进程）
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

**子进程执行方式（类实例作为 worker）**：

```python
class BaseTagWorker:
    def process_entity(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单个 entity 的 tag 计算（子进程 worker）
        
        流程：
        1. 从 payload 提取信息
        2. 加载 entity 的全量数据（到 end_date）
        3. 获取交易日列表
        4. 遍历每个日期：
           a. 过滤数据到 as_of_date（保证一致性，不包含未来数据）
           b. 对每个 tag 调用 calculate_tag()
           c. 收集结果
        5. 批量存储结果
        6. 返回统计信息
        
        注意：
        - 在子进程中实例化 TagWorker（ProcessWorker 负责）
        - 数据加载在子进程中进行，保证内存可控
        - 数据过滤到 as_of_date，保证计算一致性（避免"上帝模式"问题）
        - 批量存储，提高性能
        - tracker 等实例变量在子进程中自然存在
        - 进程结束自动释放内存
        """
```

**ProcessWorker Executor Wrapper**：

```python
def tag_executor_wrapper(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    ProcessWorker 的 executor wrapper
    
    在子进程中实例化 Executor 并执行
    
    注意：文件名从 calculator.py 改为 executor.py，明确表示这是子进程 executor
    """
    executor_class = payload['executor_class']  # 重命名自 calculator_class
    settings_path = payload['settings_path']
    
    # 初始化 DataManager 和 TagService（子进程中）
    from app.data_manager import DataManager
    data_mgr = DataManager(is_verbose=False)
    tag_service = data_mgr.get_tag_service()
    
    # 实例化 Executor（在子进程中）
    executor = executor_class(
        settings_path=settings_path,
        data_mgr=data_mgr,
        tag_service=tag_service
    )
    
    # 调用 process_entity 方法
    return executor.process_entity(payload)
```

**关键点**：
1. **数据加载时机**：子进程初始化后才加载数据
2. **数据加载范围**：加载到 `end_date` 的全量数据（性能优化）
3. **数据过滤**：框架层面自动过滤到 `as_of_date`（保证一致性）
4. **批量存储**：收集所有结果后批量写入数据库
5. **内存管理**：进程结束自动释放内存

### 数据加载和过滤策略

#### 数据加载策略

**全量加载**：
- 在子进程中一次性加载 entity 到 `end_date` 的全量数据
- 避免重复 I/O，提高性能

**内存控制**：
- 每个进程只加载一个 entity 的数据
- 最大 10 个进程，最多 10 个 entity 的数据在内存中
- 进程结束自动释放内存

#### 数据过滤策略

**问题**：全量加载可能导致"上帝模式"问题（计算时看到未来数据）

**解决方案**：框架层面强制过滤到 `as_of_date`

```python
def _filter_data_to_date(historical_data: Dict, as_of_date: str) -> Dict:
    """
    过滤数据到指定日期（不包含未来数据）
    
    过滤规则：
    - K线数据：只保留 date <= as_of_date 的记录
    - 财务数据：只保留 quarter/date <= as_of_date 的记录
    - 其他时间序列数据：同样过滤
    """
```

**调用时机**：
- 在 `calculate_tag` 调用前，框架自动过滤数据
- 用户无需关心数据过滤，保证计算一致性

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
- 计算失败：调用 `on_calculate_error` 钩子，根据 `should_continue_on_error` 决定是否继续
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

**新架构的优势**：

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

## 版本管理

### 版本变更处理

版本变更在 `handle_version_change()` 中处理，支持以下场景：

1. **NO_CHANGE**：版本未变，继续使用
2. **NEW_SCENARIO**：创建新 scenario，保留旧的
3. **REFRESH_SCENARIO**：删除之前结果，重新计算
4. **ROLLBACK**：版本回退（需要配置允许）

### 版本回退（Version Rollback）

**场景**：用户把 version 从 "2.0" 改回 "1.0"（版本1已经存在且是 legacy）

**处理逻辑**：

1. **检查全局配置 `ALLOW_VERSION_ROLLBACK`**（默认 False）
   - 如果 `ALLOW_VERSION_ROLLBACK = False`：
     - 记录严重警告日志，明确告知风险
     - 抛出 ValueError，阻止继续执行
     - 用户需要明确配置 `ALLOW_VERSION_ROLLBACK = True` 才能继续
   - 如果 `ALLOW_VERSION_ROLLBACK = True`：
     - 记录警告日志，明确告知风险
     - 查找当前的 active 版本（is_legacy=0）
     - 如果存在 active 版本：标记之前的 active 版本为 legacy
     - 把当前版本（settings.version）设置为 legacy=0（active）
     - 注意：不删除旧的 tag definitions 和 tag values
     - 确保 tag definitions 存在
     - 按照该版本的 update_mode 继续（incremental 或 refresh）
     - `version_action = "ROLLBACK"`

2. **关键点**：
   - **不删除旧数据**：保留历史数据，让用户可以查看
   - **按照该版本的 update_mode 继续**：如果该版本之前是 incremental，继续 incremental；如果是 refresh，就 refresh
   - **用户需要对自己的行为负责**：如果版本1之前是 incremental 跑的，现在继续 incremental 跑，可能会和之前的 tag 结果不一致

3. **全局配置**（`app/tag/config.py`）：
   ```python
   ALLOW_VERSION_ROLLBACK = False  # 默认 False，需要用户明确配置为 True
   ```

### Legacy Version 清理

**策略**：保留 active version + 最多 N 个 legacy versions（默认 N=3）

**逻辑**：
- 当创建新 scenario 时（NEW_SCENARIO），如果 legacy version 数量 >= keep_n，删除最老的
- 所有 version 变化都统一处理，无论是手动还是自动创建

**实现**：
```python
def cleanup_legacy_versions(self, scenario_name: str, keep_n: int = 3):
    # 1. 查询所有 legacy scenarios（按 created_at 排序，最老的在前）
    # 2. 如果数量 >= keep_n：
    #    - 删除最老的 scenarios（调用 tag_service.delete_scenario）
```

---

## 职责边界

### 组件职责矩阵

| 功能 | Settings | TagWorker | BaseTagWorker | TagManager | SettingsValidator | SettingsProcessor |
|------|----------|------------|-------------------|------------|-------------------|-------------------|
| 定义配置 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 验证配置 | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| 读取配置 | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 检查启用状态 | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| 实现计算逻辑 | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 加载数据 | ❌ | 可选 | ✅ (默认) | ❌ | ❌ | ❌ |
| 发现业务场景 | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| 管理实例 | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| 执行流程（子进程） | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| 版本管理 | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **多进程调度** | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Job 构建** | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **进程数决定** | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |

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
- ✅ 只提供框架支持（子进程执行流程、版本管理、数据加载）
- ✅ 提供 `process_entity()` 方法作为子进程 worker
- ✅ 包含 tracker 等子进程状态管理
- ❌ 不实现业务逻辑
- ❌ 不负责多进程调度（由 TagManager 负责）

**TagManager**：
- ✅ 只管理业务场景（发现、验证、注册）
- ✅ 负责多进程调度（job 构建、进程数决定、ProcessWorker 调用）
- ✅ 监控执行进度，收集统计信息
- ❌ 不计算（由 TagWorker 负责）
- ❌ 不验证配置结构（由 SettingsValidator 负责）

**SettingsValidator**：
- ✅ 只验证配置
- ❌ 不处理配置
- ❌ 不执行计算

**SettingsProcessor**：
- ✅ 只处理配置（读取、默认值、合并）
- ❌ 不验证配置
- ❌ 不执行计算

---

## 设计原则

### 1. 职责单一

每个组件只负责自己的职责：
- Settings 只定义配置
- TagWorker 只实现计算
- Manager 只管理
- BaseTagWorker 只提供框架
- SettingsValidator 只验证
- SettingsProcessor 只处理

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
- **版本管理合理**：Version 在 Scenario 级别，代表算法版本
- **查询更方便**：可以按 Scenario 和 Version 查询
- **数据一致性更好**：一个 Scenario 的所有 Tags 共享同一个版本

### 2. 为什么 Version 在 Scenario 级别？

**原因**：
- Version 代表算法版本，属于整个业务场景
- 算法改变时，整个 Scenario 的版本升级
- 一个 Scenario 的所有 Tags 应该共享同一个版本
- 便于版本管理和历史追溯

### 3. 为什么 is_enabled 在顶层？

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

### 5. 为什么 on_version_change 是 Scenario 级别的？

**原因**：
- 算法改变影响的是整个业务场景，不是单个 Tag
- `REFRESH_SCENARIO`：刷新该 Scenario 下所有 Tags 的值
- `NEW_SCENARIO`：创建新的 Scenario（保留旧 Scenario 的数据）
- 更符合业务逻辑和版本管理

### 6. 为什么 Settings 和 TagWorker 分离？

**原因**：
- 配置与代码分离，便于维护和版本控制
- 支持配置的热更新（未来可能支持）
- 一个 TagWorker 可以打多个 Tag，配置需要独立管理

### 7. 为什么在 TagManager 中检查 is_enabled？

**原因**：
- 早期过滤，避免不必要的 Calculator 初始化
- Manager 负责管理，应该知道哪些 Calculator 可用
- 职责清晰：Manager 管理，Executor 计算

### 8. 为什么配置验证和处理分离？

**原因**：
- 职责单一：验证和处理是不同的职责
- 代码复用：TagManager 和 BaseTagWorker 可以共享验证逻辑
- 易于测试：静态方法易于单元测试
- 易于维护：配置相关逻辑集中管理

### 9. 为什么版本回退需要全局配置？

**原因**：
- 版本回退可能导致数据不一致
- 只有 worker 逻辑和 version 都回退，才能保证结果一致
- 用户需要明确知晓风险并主动配置
- 默认不允许，确保安全性

---

## 文件组织

### 目录结构

```
app/tag/
├── base_tag_worker.py          # 框架基类（重命名自 base_tag_calculator.py）
├── tag_manager.py               # 业务场景管理器
├── settings_validator.py        # 配置验证器（静态方法）
├── settings_processor.py        # 配置处理器（静态方法）
├── scenario_identifier.py       # Scenario 标识符类
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

## 版本历史

### v2.0 (2025-12-19)

**重大变更**：
- 采用三层表结构：`tag_scenario`, `tag_definition`, `tag_value`
- Version 移到 Scenario 级别
- `on_version_change` 改为 Scenario 级别（`REFRESH_SCENARIO` / `NEW_SCENARIO`）
- `is_enabled` 移到顶层
- 配置验证和处理分离（SettingsValidator 和 SettingsProcessor）
- 支持版本回退（需要全局配置允许）

**设计改进**：
- 数据模型更清晰
- 版本管理更合理
- 职责边界更明确
- 代码结构更简洁

### v1.0 (之前版本)

- 两层表结构：`tag`, `tag_value`
- Version 在 Tag 级别
- `on_version_change` 在 Tag 级别

---

## 附录

### 枚举定义

**KlineTerm**：
- `DAILY`: 日线
- `WEEKLY`: 周线
- `MONTHLY`: 月线

**UpdateMode**：
- `INCREMENTAL`: 增量更新
- `REFRESH`: 全量刷新

**VersionChangeAction**：
- `REFRESH_SCENARIO`: 刷新该 Scenario 下所有 Tags 的值
- `NEW_SCENARIO`: 创建新的 Scenario（保留旧 Scenario 的数据）

**VersionAction**（内部使用）：
- `NO_CHANGE`: 版本未变
- `NEW_SCENARIO`: 创建新 scenario
- `REFRESH_SCENARIO`: 刷新 scenario
- `ROLLBACK`: 版本回退

### 全局配置

**app/tag/config.py**：
```python
# Scenarios 根目录配置
DEFAULT_SCENARIOS_ROOT = "app/tag/scenarios"

# 版本回退配置
ALLOW_VERSION_ROLLBACK = False  # 是否允许版本回退（默认 False）
```

---

**文档结束**
