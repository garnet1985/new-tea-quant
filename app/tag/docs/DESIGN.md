# Tag 系统设计文档

**版本**: v2.0  
**最后更新**: 2025-12-26  
**设计者**: System Architecture Team

---

## 📋 目录

1. [概述](#概述)
2. [数据模型设计](#数据模型设计)
3. [核心组件](#核心组件)
4. [配置设计](#配置设计)
5. [职责边界](#职责边界)
6. [设计原则](#设计原则)
7. [关键设计决策](#关键设计决策)

---

## 概述

Tag 系统是一个用于预计算和存储实体属性/状态的框架。系统采用配置驱动的方式，允许用户通过 Python 配置文件定义业务场景（Scenario），每个场景可以产生多个标签（Tag）。

### 核心概念

- **业务场景（Scenario）**：一个业务逻辑单元，对应一个 Calculator 和一个 Settings 配置
  - 例如：市值分类（`market_value_bucket`）
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
│  │ TagManager   │─────▶│  Calculator  │                  │
│  │ (发现/管理)   │      │  (业务逻辑)   │                  │
│  └──────────────┘      └──────────────┘                  │
│         │                    │                            │
│         │                    │                            │
│         ▼                    ▼                            │
│  ┌──────────────┐      ┌──────────────┐                  │
│  │   Settings    │      │ BaseTagCalc  │                  │
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
| `name` | VARCHAR(64) | 业务场景唯一代码（如 `market_value_bucket`） |
| `display_name` | VARCHAR(128) | 业务场景显示名称 |
| `version` | VARCHAR(32) | **版本号**（如 `1.0`, `2.0`），代表算法版本 |
| `description` | TEXT | 业务场景描述 |
| `calculator_path` | VARCHAR(255) | Calculator 文件路径 |
| `settings_path` | VARCHAR(255) | Settings 文件路径 |
| `is_enabled` | TINYINT(1) | 是否启用（默认 1） |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

**索引**：
- `UNIQUE KEY uk_name_version (name, version)`：同一场景的不同版本
- `INDEX idx_name (name)`：按场景名查询

**设计要点**：
- **Version 在 Scenario 级别**：代表整个业务场景的算法版本
- 一个 Scenario 可以有多个版本（历史版本保留）
- `is_enabled` 控制整个 Scenario 是否启用

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
- Tag Definition 共享 Scenario 的版本
- 标签名在同一 Scenario 内唯一

### 3. tag_value 表

**用途**：存储标签的实际计算结果

**表结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `entity_type` | VARCHAR(32) | 实体类型（如 `stock`, `kline_daily`，默认 `stock`） |
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
├─ name: "market_value_bucket"
├─ version: "1.0"
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

**位置**：`app/tag/tags/<business_scenario>/settings.py`

**职责**：定义业务场景和标签的配置信息

**设计初衷**：
- 配置与代码分离，便于版本控制
- 声明式配置，用户通过配置声明行为
- 支持多 Tag：一个 Calculator 可以产生多个 Tags

**配置结构**：

```python
from app.tag.enums import KlineTerm, UpdateMode, VersionChangeAction

Settings = {
    # Calculator 级别配置（共享逻辑）
    "calculator": {
        "meta": {
            "name": "MARKET_VALUE_BUCKET",  # 业务场景名
            "description": "按市值阈值给股票打大小市值标签",
            "is_enabled": True,  # 控制整个 Scenario 是否启用
        },
        "base_term": KlineTerm.DAILY.value,
        "required_terms": [],
        "required_data": [],
        "core": {
            "mkv_threshold": 1e10,
        },
        "performance": {
            "max_workers": 8,
            "update_mode": UpdateMode.INCREMENTAL.value,
            "on_version_change": VersionChangeAction.REFRESH_SCENARIO.value,
        },
    },
    
    # Tag 级别配置（多个 tag）
    "tags": [
        {
            "name": "large_market_value",
            "display_name": "大市值股票",
            "description": "市值大于阈值的股票",
            "version": "1.0",  # 注意：这个 version 会被 scenario 的 version 覆盖
            "core": {
                "label": "large",
            },
        },
        {
            "name": "small_market_value",
            "display_name": "小市值股票",
            "description": "市值小于等于阈值的股票",
            "version": "1.0",
            "core": {
                "label": "small",
            },
        },
    ],
}
```

**责任边界**：
- ✅ 定义配置结构
- ✅ 声明 Scenario 和 Tag 的元信息
- ✅ 声明计算参数和性能配置
- ❌ 不负责验证配置（由 BaseTagCalculator 负责）
- ❌ 不负责执行计算（由 Calculator 负责）

### 2. Calculator (`calculator.py`)

**位置**：`app/tag/tags/<business_scenario>/calculator.py`

**职责**：实现业务场景的计算逻辑

**设计初衷**：
- 业务逻辑封装：每个 Calculator 封装一个业务场景
- 用户自定义：用户继承 `BaseTagCalculator` 实现自己的逻辑
- 可扩展性：支持扩展数据加载和自定义钩子函数

**实现示例**：

```python
from app.tag.base_tag_calculator import BaseTagCalculator
from typing import Dict, Any, Optional

class MarketValueCalculator(BaseTagCalculator):
    """市值分类 Calculator（业务场景：market_value_bucket）"""
    
    def calculate_tag(
        self, 
        entity_id: str,
        entity_type: str,
        as_of_date: str, 
        historical_data: Dict[str, Any],
        tag_config: Dict[str, Any]  # 已合并的配置
    ) -> Optional[Any]:
        """
        计算 tag
        
        这个 Calculator 可以为多个 tag 提供计算：
        - large_market_value: 大市值股票
        - small_market_value: 小市值股票
        """
        # 获取配置参数（所有 tags 共享 calculator 的 core 配置）
        mkv_threshold = tag_config["core"]["mkv_threshold"]
        tag_name = tag_config["tag_meta"]["name"]
        
        # 实现计算逻辑
        market_value = historical_data.get("market_value", {}).get("current", 0)
        
        if tag_name == "large_market_value":
            if market_value > mkv_threshold:
                return {"value": "1", "as_of_date": as_of_date}
        elif tag_name == "small_market_value":
            if market_value <= mkv_threshold:
                return {"value": "1", "as_of_date": as_of_date}
        
        return None
```

**责任边界**：
- ✅ 实现 `calculate_tag()` 方法（必需）
- ✅ 实现业务场景的计算逻辑
- ✅ 一个 Calculator 可以为多个 Tags 提供计算
- ✅ 可选：重写 `load_entity_data()` 支持自定义数据源
- ❌ 不负责配置验证（由 BaseTagCalculator 负责）
- ❌ 不负责文件管理（由 TagManager 负责）

### 3. BaseTagCalculator (`base_tag_calculator.py`)

**位置**：`app/tag/base_tag_calculator.py`

**职责**：框架基类，提供 Calculator 的基础功能和框架支持

**设计初衷**：
- 统一接口：定义标准的 Calculator 接口
- 框架功能：配置管理、数据加载、钩子函数支持
- 减少重复代码：通用功能在基类中实现

**核心功能**：

1. **配置管理**
   - `_load_and_process_settings()`: 加载并处理 settings
   - `_validate_calculator_fields()`: 验证 calculator 配置
   - `_validate_tags_fields()`: 验证 tags 配置
   - `_apply_calculator_defaults()`: 应用默认值
   - `_validate_calculator_enums()`: 验证枚举值
   - `_merge_tag_config()`: 合并 calculator 和 tag 配置

2. **数据加载**
   - `load_entity_data()`: 加载实体历史数据（默认支持股票，可扩展）

3. **钩子函数**
   - `on_init()`: 初始化钩子
   - `on_tag_created()`: Tag 创建后钩子
   - `on_calculate_error()`: 计算错误钩子
   - `should_continue_on_error()`: 错误时是否继续
   - `on_finish()`: 完成钩子

**责任边界**：
- ✅ 配置读取和验证
- ✅ 配置默认值处理
- ✅ 配置合并（calculator + tag）
- ✅ 数据加载（默认实现）
- ✅ 钩子函数框架支持
- ❌ 不负责业务计算逻辑（由 Calculator 实现）
- ❌ 不负责文件发现和管理（由 TagManager 负责）

### 4. TagManager (`tag_manager.py`)

**位置**：`app/tag/tag_manager.py`

**职责**：统一管理所有业务场景（按业务场景名管理）

**设计初衷**：
- 统一入口：提供统一的接口访问所有 Calculators
- 早期过滤：在创建 Calculator 实例前就过滤掉不启用的
- 生命周期管理：管理 Calculator 类的发现和加载

**核心功能**：

1. **发现和加载**
   - `_load_calculators()`: 发现所有业务场景（遍历 tags 目录）
   - `_check_calculator_enabled()`: 检查 calculator 是否启用
   - `_load_calculator()`: 加载 calculator 类

2. **管理接口**
   - `get_calculator(business_scenario)`: 获取指定业务场景的 calculator 类
   - `list_tags()`: 列出所有业务场景名称（不是 tag 名称）
   - `create_calculator(business_scenario)`: 创建指定业务场景的 calculator 实例
   - `reload()`: 重新发现所有 calculators

**责任边界**：
- ✅ 发现所有业务场景（遍历 tags 目录）
- ✅ 检查 calculator.py 文件存在性
- ✅ 检查 settings.py 文件存在性
- ✅ 检查 calculator 是否启用（早期过滤）
- ✅ 加载 calculator 类
- ✅ 管理 calculator 实例（按业务场景名）
- ❌ 不负责配置验证（由 BaseTagCalculator 负责）
- ❌ 不负责业务计算逻辑（由 Calculator 负责）

**重要说明**：
- TagManager 管理的是**业务场景**（文件夹名），不是 tag
- 一个业务场景可以产生多个 tags（在 settings.py 的 `tags` 列表中定义）
- 要获取某个业务场景产生的所有 tags，需要通过 Calculator 实例访问

---

## 配置设计

### 配置结构

配置采用两层结构：Calculator 级别和 Tag 级别。

```python
Settings = {
    "calculator": {
        # Calculator 级别配置（共享给所有 tags）
    },
    "tags": [
        # Tag 级别配置（每个 tag 独立）
    ],
}
```

### Calculator 级别配置

| 配置项 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| `meta.name` | str | ✅ | 业务场景名（如 `MARKET_VALUE_BUCKET`） |
| `meta.description` | str | ✅ | 业务场景描述 |
| `meta.is_enabled` | bool | ✅ | 是否启用（控制整个 Scenario） |
| `base_term` | str | ✅ | 基础周期（枚举：`daily`, `weekly`, `monthly`） |
| `required_terms` | list | ❌ | 需要的其他周期（默认 `[]`） |
| `required_data` | list | ❌ | 需要的数据源（默认 `[]`） |
| `core` | dict | ❌ | 共享的计算参数（默认 `{}`） |
| `performance.max_workers` | int | ❌ | 最大并发数（默认自动分配） |
| `performance.update_mode` | str | ✅ | 更新模式（`incremental` 或 `refresh`） |
| `performance.on_version_change` | str | ✅ | 版本变更处理（`refresh_scenario` 或 `new_scenario`） |

### Tag 级别配置

| 配置项 | 类型 | 必需 | 说明 |
|--------|------|------|------|
| `name` | str | ✅ | 标签唯一代码 |
| `display_name` | str | ✅ | 标签显示名称 |
| `description` | str | ❌ | 标签描述 |

**注意**：
- Tag 级别**不支持** `core` 和 `performance`，只在 Calculator 级别配置
- 所有 Tags 共享 Calculator 的 `core` 和 `performance` 配置
- 简化设计：避免配置复杂性，所有 tags 使用相同的计算参数和性能配置

### 配置验证

**Calculator 级别验证**：
- `calculator.meta.name`: 必需
- `calculator.meta.is_enabled`: 必需（在 TagManager 中检查）
- `calculator.base_term`: 必需，必须在枚举中
- `calculator.performance.update_mode`: 必需，必须在枚举中
- `calculator.performance.on_version_change`: 必需，必须在枚举中

**Tag 级别验证**：
- `tags`: 必需，至少一个 tag
- 每个 tag: `name`, `display_name` 必需
- Tag name 在同一 Scenario 内唯一
- Tag 级别不支持 `core` 和 `performance`（只在 calculator 级别配置）

---

## 职责边界

### 组件职责矩阵

| 功能 | Settings | Calculator | BaseTagCalculator | TagManager |
|------|----------|------------|-------------------|------------|
| 定义配置 | ✅ | ❌ | ❌ | ❌ |
| 验证配置 | ❌ | ❌ | ✅ | ❌ |
| 读取配置 | ❌ | ❌ | ✅ | ❌ |
| 检查启用状态 | ❌ | ❌ | ❌ | ✅ |
| 实现计算逻辑 | ❌ | ✅ | ❌ | ❌ |
| 加载数据 | ❌ | 可选 | ✅ (默认) | ❌ |
| 发现业务场景 | ❌ | ❌ | ❌ | ✅ |
| 管理实例 | ❌ | ❌ | ❌ | ✅ |

### 责任边界总结

**Settings**：
- ✅ 只定义配置
- ❌ 不验证配置
- ❌ 不执行计算

**Calculator**：
- ✅ 只实现计算逻辑
- ❌ 不管理文件
- ❌ 不验证配置结构

**BaseTagCalculator**：
- ✅ 只提供框架支持
- ❌ 不实现业务逻辑

**TagManager**：
- ✅ 只管理业务场景
- ❌ 不计算
- ❌ 不验证配置结构

---

## 设计原则

### 1. 职责单一

每个组件只负责自己的职责：
- Settings 只定义配置
- Calculator 只实现计算
- Manager 只管理
- BaseTagCalculator 只提供框架

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

所有 Calculators 遵循相同的接口：
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

### 3. 为什么 is_enabled 只在 Calculator 级别？

**原因**：
- `is_enabled` 控制整个业务场景是否启用
- 如果 Calculator 启用，所有 Tags 都会被计算
- 不能只启用一个 Tag 而舍弃另一个（因为 Tag 是业务场景的产物）
- 符合业务逻辑：业务场景是一个整体

### 4. 为什么支持一个 Calculator 打多个 Tag？

**原因**：
- 业务逻辑复用（如市值分类：大市值、小市值）
- 减少重复代码
- 配置更灵活（共享 calculator 配置，独立 tag 配置）

### 5. 为什么 on_version_change 是 Scenario 级别的？

**原因**：
- 算法改变影响的是整个业务场景，不是单个 Tag
- `refresh_scenario`：刷新该 Scenario 下所有 Tags 的值
- `new_scenario`：创建新的 Scenario（保留旧 Scenario 的数据）
- 更符合业务逻辑和版本管理

### 6. 为什么 Settings 和 Calculator 分离？

**原因**：
- 配置与代码分离，便于维护和版本控制
- 支持配置的热更新（未来可能支持）
- 一个 Calculator 可以打多个 Tag，配置需要独立管理

### 7. 为什么在 TagManager 中检查 is_enabled？

**原因**：
- 早期过滤，避免不必要的 Calculator 初始化
- Manager 负责管理，应该知道哪些 Calculator 可用
- 职责清晰：Manager 管理，Calculator 计算

### 8. 为什么 BaseTagCalculator 负责配置验证？

**原因**：
- 配置验证是 Calculator 初始化的必要步骤
- 验证逻辑与 Calculator 紧密相关
- 用户创建 Calculator 实例时自动验证，确保配置正确

---

## 文件组织

### 目录结构

```
app/tag/
├── base_tag_calculator.py      # 框架基类
├── tag_manager.py               # 业务场景管理器
├── enums.py                     # 枚举定义
├── docs/
│   └── DESIGN.md               # 本文档
└── tags/
    ├── market_value_bucket/     # 业务场景名（不是 tag name）
    │   ├── settings.py         # 定义 calculator 和多个 tags 配置
    │   └── calculator.py       # 实现市值分类计算逻辑
    │
    ├── momentum_classifier/     # 另一个业务场景
    │   ├── settings.py
    │   └── calculator.py
    │
    └── ...
```

### 重要概念

**业务场景 vs Tag**：
- **业务场景**（文件夹名）：如 `market_value_bucket`（市值分类）
- **Tag**（settings 中定义）：如 `large_market_value`, `small_market_value`
- 一个业务场景可以产生多个 tags
- TagManager 管理的是业务场景，不是 tag

---

## 版本历史

### v2.0 (2025-12-19)

**重大变更**：
- 采用三层表结构：`tag_scenario`, `tag_definition`, `tag_value`
- Version 移到 Scenario 级别
- `on_version_change` 改为 Scenario 级别（`refresh_scenario` / `new_scenario`）
- `is_enabled` 只在 Calculator 级别，不在 Tag 级别

**设计改进**：
- 数据模型更清晰
- 版本管理更合理
- 职责边界更明确

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

**SupportedDataSource**：
- `KLINE`: K线数据
- `CORPORATE_FINANCE`: 财务数据

---

**文档结束**


顶层：TagManager 启动整体流程
[用户代码]
    |
    v
+----------------------+
| TagManager.run()     |
+----------------------+
    |
    v
+-------------------------------------+
| _discover_and_register_calculators()|
+-------------------------------------+
    |
    v
+-----------------------------+
| _validate_all_settings()    |
+-----------------------------+
    |
    v
+-----------------------------+
| for calc in self.calculators|
|     calc.run()              |
+-----------------------------+

核心函数（TagManager）
TagManager.run()
TagManager.register_scenario(settings_dict) ← 支持“无 settings 文件”的入口
TagManager._discover_and_register_calculators() ← 扫描静态 settings / modules
TagManager._validate_all_settings() ← 统一做 schema 校验，抛出早期错误


单个 Calculator 的生命周期（核心）

BaseCalculator.run()
    |
    v
+--------------------------------+
| ensure_metadata()              |
|  - ensure_scenario()           |
|  - ensure_tags()               |
+--------------------------------+
    |
    v
+--------------------------------+
| renew_or_create_values()       |
|  - handle_version_change()     |
|  - handle_update_mode()        |
+--------------------------------+


创建 / 同步元信息

BaseCalculator.run()
    |
    v
+--------------------------+
| ensure_metadata()        |
+--------------------------+
    |
    v
+-------------------------------+
| scenario = ensure_scenario()  |
+-------------------------------+
    |
    v
+--------------------------------------------+
| tag_defs = ensure_tags(scenario)           |
+--------------------------------------------+
    |
    v
(进入 renew_or_create_values)


核心函数（Calculator 内）
BaseCalculator.run()
BaseCalculator.ensure_metadata()
BaseCalculator.ensure_scenario() -> ScenarioRecord
BaseCalculator.ensure_tags(scenario: ScenarioRecord) -> List[TagDefinition]


ensure_scenario()
    |
    v
+---------------------------------------------------+
| existing = repo.get_scenarios_by_name(name)       |
+---------------------------------------------------+
    |
    v
+------------------------------------------------------+
| target = _select_or_create_scenario(existing,        |
|                                     settings.version)|
+------------------------------------------------------+
    |
    v
return target

renew_or_create_values：版本 & 更新模式控制


BaseCalculator.run()
    |
    v
+------------------------------+
| renew_or_create_values()     |
+------------------------------+
    |
    v
+-----------------------------------------+
| version_action = handle_version_change()|
+-----------------------------------------+
    |
    v
+--------------------------------------------+
| handle_update_mode(version_action)         |
+--------------------------------------------+


handle_version_change()

handle_version_change()
    |
    v
+-------------------------------------------------+
| db_versions = repo.get_scenarios_by_name(name)  |
+-------------------------------------------------+
    |
    v
+------------------------------+
| if settings.version 在 db 中?|
+------------------------------+
    | Yes                             | No
    |                                 |
    v                                 v
+-------------------+        +----------------------------+
| version_action =  |        | version_action =           |
| "NO_CHANGE"       |        | on_version_change          |
+-------------------+        |  (REFRESH_SCENARIO /      |
                             |   NEW_SCENARIO)           |
                             +----------------------------+
                                      |
                                      v
                            +-----------------------------+
                            | new_scenario =             |
                            |   create_new_scenario()    |
                            +-----------------------------+
                                      |
                                      v
                            +-----------------------------+
                            | cleanup_legacy_versions()   |
                            +-----------------------------+

return version_action
核心函数
BaseCalculator.handle_version_change() -> VersionAction
BaseCalculator.create_new_scenario() -> ScenarioRecord
BaseCalculator.cleanup_legacy_versions(name: str, keep_n: int = 3)

