# Tag 系统使用指南

**版本：** 3.0  
**最后更新**: 2026-01-17

---

## 📋 目录

1. [概述](#概述)
2. [核心概念](#核心概念)
3. [快速开始](#快速开始)
4. [使用场景](#使用场景)
5. [配置指南](#配置指南)
6. [开发指南](#开发指南)
7. [最佳实践](#最佳实践)
8. [常见问题](#常见问题)
9. [相关文档](#相关文档)

---

## 概述

Tag 系统是一个用于**预计算和存储实体属性/状态**的框架。系统采用**配置驱动**的方式，允许用户通过 Python 配置文件定义业务场景（Scenario），每个场景可以产生多个标签（Tag）。

### 为什么需要 Tag 系统？

在策略分析中，我们经常需要计算各种标签（如市值分类、动量因子、技术指标等）。这些标签：
- **计算成本高**：需要遍历大量历史数据
- **使用频率高**：多个策略可能使用相同的标签
- **需要增量更新**：新数据到来时，只需要计算增量部分

Tag 系统通过**预计算**和**存储**的方式，解决了这些问题：
- ✅ **一次计算，多次使用**：标签计算后存储在数据库中，多个策略可以共享
- ✅ **增量更新**：支持 INCREMENTAL 模式，只计算新增数据
- ✅ **多进程并行**：充分利用多核 CPU，提高计算效率
- ✅ **配置驱动**：通过配置文件定义业务场景，无需修改代码

---

## 核心概念

### 业务场景（Scenario）

一个**业务逻辑单元**，对应一个 TagWorker 和一个 Settings 配置。

**示例**：
- 市值分类（`market_value`）：根据市值大小对股票进行分类
- 动量因子（`momentum`）：计算股票的动量指标
- 技术指标（`technical`）：计算各种技术指标

**特点**：
- 一个 Scenario 可以产生**多个 Tags**
- 每个 Scenario 有独立的配置和计算逻辑
- Scenario 存储在 `userspace/tags/<scenario_name>/` 目录下

### 标签定义（Tag Definition）

Scenario 产生的**具体标签**。

**示例**（市值分类场景）：
- `large_market_value`：大市值股票
- `medium_market_value`：中市值股票
- `small_market_value`：小市值股票

**特点**：
- 属于某个 Scenario
- 在数据库的 `tag_definition` 表中存储
- 每个 Tag 有独立的元信息（名称、描述等）

### 标签值（Tag Value）

标签的**实际计算结果**。

**特点**：
- 存储实体在某个日期的标签值
- 引用 Tag Definition
- 使用 JSON 格式存储，支持结构化数据（键值对、数组等）

**示例**：
```json
{
  "entity_id": "000001.SZ",
  "tag_definition_id": 10,
  "as_of_date": "2025-12-19",
  "json_value": {
    "momentum": 0.1234,
    "year_month": "202501"
  }
}
```

### 更新模式（Update Mode）

Tag 系统支持两种更新模式：

- **INCREMENTAL（增量更新）**：只计算新增的数据，从最后更新日期的下一个交易日开始
- **REFRESH（全量刷新）**：重新计算所有数据，从默认开始日期开始

---

## 快速开始

### 1. 创建业务场景

在 `userspace/tags/` 目录下创建新的场景目录：

```bash
mkdir -p userspace/tags/my_scenario
```

### 2. 创建配置文件

创建 `userspace/tags/my_scenario/settings.py`：

```python
Settings = {
    "name": "my_scenario",
    "display_name": "我的业务场景",
    "description": "这是一个示例场景",
    "is_enabled": True,
    "target_entity": {"type": "stock_kline_daily"},
    "update_mode": "incremental",
    "incremental_required_records_before_as_of_date": 60,
    "tags": [
        {
            "name": "my_tag",
            "display_name": "我的标签",
            "description": "这是一个示例标签"
        }
    ]
}
```

### 3. 实现 TagWorker

创建 `userspace/tags/my_scenario/tag_worker.py`：

```python
from core.modules.tag.core.base_tag_worker import BaseTagWorker
from core.modules.tag.core.models.tag_model import TagModel
from typing import Dict, Any, Optional

class MyTagWorker(BaseTagWorker):
    """我的业务场景 TagWorker"""
    
    def calculate_tag(
        self,
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_definition: TagModel
    ) -> Optional[Dict[str, Any]]:
        """
        计算 tag
        
        Args:
            as_of_date: 业务日期
            historical_data: 历史数据（已过滤到 as_of_date）
            tag_definition: Tag 定义对象
            
        Returns:
            Tag 值（JSON 格式），如果返回 None 则跳过该 Tag
        """
        # 访问 entity 信息
        entity_id = self.entity['id']
        
        # 访问历史数据
        daily_klines = historical_data['klines']['daily']
        
        # 实现计算逻辑
        # ...
        
        # 返回 JSON 格式的 value
        return {
            "value": {"my_value": 123.45}
        }
```

### 4. 执行 Tag 计算

```python
from core.modules.tag.core.tag_manager import TagManager

# 创建 TagManager
tag_manager = TagManager(is_verbose=True)

# 执行所有启用的 scenarios
tag_manager.execute()

# 或执行单个 scenario
tag_manager.execute(scenario_name="my_scenario")
```

---

## 使用场景

### 场景 1：市值分类

**需求**：根据市值大小对股票进行分类（大市值、中市值、小市值）

**实现**：
1. 创建 `userspace/tags/market_value/` 目录
2. 在 `settings.py` 中定义 3 个 tags：`large_market_value`, `medium_market_value`, `small_market_value`
3. 在 `tag_worker.py` 中实现市值计算逻辑，根据市值大小返回对应的 tag

### 场景 2：动量因子

**需求**：计算股票的动量指标（60 天动量、120 天动量）

**实现**：
1. 创建 `userspace/tags/momentum/` 目录
2. 在 `settings.py` 中定义 2 个 tags：`momentum_60_days`, `momentum_120_days`
3. 在 `tag_worker.py` 中实现动量计算逻辑，根据 tag 名称返回对应的动量值

### 场景 3：技术指标

**需求**：计算各种技术指标（RSI、MACD、布林带等）

**实现**：
1. 创建 `userspace/tags/technical/` 目录
2. 在 `settings.py` 中定义多个 tags：`rsi`, `macd`, `bollinger_bands`
3. 在 `tag_worker.py` 中实现技术指标计算逻辑

---

## 配置指南

### 基本配置

**必需配置**：
- `name`：业务场景唯一代码
- `target_entity`：目标实体类型（如 `stock_kline_daily`）
- `tags`：标签列表（至少一个）

**可选配置**：
- `display_name`：显示名称（默认使用 `name`）
- `description`：描述信息
- `is_enabled`：是否启用（默认 `False`）
- `recompute`：是否强制重新计算（默认 `False`）

### 更新模式配置

**INCREMENTAL 模式**（推荐）：
```python
{
    "update_mode": "incremental",
    "incremental_required_records_before_as_of_date": 60  # 必需
}
```

**REFRESH 模式**：
```python
{
    "update_mode": "refresh"
}
```

### 性能配置

**Chunk 模式**（推荐，适合大数据量）：
```python
{
    "performance": {
        "use_chunk": True,
        "data_chunk_size": 500  # 每个 chunk 的记录数（默认 500，最小 300）
    }
}
```

**全量模式**（适合小数据量）：
```python
{
    "performance": {
        "use_chunk": False
    }
}
```

### 完整配置示例

> **详细配置结构请参考** `userspace/tags/example_settings.py`，该文件包含完整的配置示例和每个属性的详细解释。

---

## 开发指南

### 实现 TagWorker

TagWorker 需要继承 `BaseTagWorker` 并实现 `calculate_tag()` 方法：

```python
from core.modules.tag.core.base_tag_worker import BaseTagWorker
from core.modules.tag.core.models.tag_model import TagModel
from typing import Dict, Any, Optional

class MyTagWorker(BaseTagWorker):
    def calculate_tag(
        self,
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_definition: TagModel
    ) -> Optional[Dict[str, Any]]:
        """
        计算 tag
        
        Args:
            as_of_date: 业务日期（格式：YYYYMMDD）
            historical_data: 历史数据（已过滤到 as_of_date）
                - historical_data['klines']['daily']: 日线数据
                - historical_data.get('corporate_finance', []): 财务数据（如果配置了）
            tag_definition: Tag 定义对象
                - tag_definition.get_name(): Tag 名称
                - tag_definition.id: Tag ID
                
        Returns:
            Tag 值（JSON 格式），如果返回 None 则跳过该 Tag
        """
        # 实现计算逻辑
        return {
            "value": {"my_value": 123.45}
        }
```

### 访问数据

**Entity 信息**：
```python
entity_id = self.entity['id']  # 实体 ID（如 "000001.SZ"）
entity_type = self.entity['type']  # 实体类型（如 "stock"）
```

**Scenario 信息**：
```python
scenario_name = self.scenario['name']  # Scenario 名称
update_mode = self.scenario['update_mode']  # 更新模式
```

**配置信息**：
```python
core_config = self.config['core']  # 业务核心参数
performance_config = self.config['performance']  # 性能配置
```

**历史数据**：
```python
daily_klines = historical_data['klines']['daily']  # 日线数据
corporate_finance = historical_data.get('corporate_finance', [])  # 财务数据
```

### 钩子函数

TagWorker 可以重写以下钩子函数：

- `on_init()`：初始化钩子（无参数）
- `on_before_execute_tagging()`：执行前钩子（无参数）
- `on_tag_created(as_of_date, tag_definition, tag_value)`：Tag 创建后钩子
- `on_as_of_date_calculate_complete(as_of_date)`：每个日期计算完成钩子
- `on_calculate_error(as_of_date, error, tag_definition)`：计算错误钩子
- `on_after_execute_tagging(result)`：执行后钩子

### 使用 Tracker

Tracker 用于存储计算过程中的临时状态：

```python
# 初始化
if 'last_month' not in self.tracker:
    self.tracker['last_month'] = None

# 使用
self.tracker['last_month'] = current_month
```

---

## 最佳实践

### 1. 配置管理

- ✅ **使用有意义的名称**：Scenario 和 Tag 名称应该清晰表达业务含义
- ✅ **添加描述信息**：为 Scenario 和 Tag 添加 `display_name` 和 `description`
- ✅ **合理设置更新模式**：大多数场景使用 INCREMENTAL 模式，提高效率
- ✅ **配置性能参数**：根据数据量选择合适的 `use_chunk` 和 `data_chunk_size`

### 2. 计算逻辑

- ✅ **避免"上帝模式"**：框架已自动过滤数据到 `as_of_date`，无需担心
- ✅ **处理边界情况**：检查历史数据是否足够（如计算 60 天动量需要至少 60 条数据）
- ✅ **返回结构化数据**：使用 JSON 格式返回标签值，支持复杂数据结构
- ✅ **使用 Tracker**：对于需要跨日期状态的计算，使用 `self.tracker` 存储状态

### 3. 性能优化

- ✅ **使用 Chunk 模式**：大数据量场景使用 Chunk 模式，控制内存使用
- ✅ **合理设置 chunk_size**：根据内存情况调整 `data_chunk_size`（默认 500，最小 300）
- ✅ **批量保存**：框架已自动批量保存，无需手动优化

### 4. 错误处理

- ✅ **返回 None 跳过 Tag**：如果某个 Tag 无法计算，返回 `None` 跳过
- ✅ **使用错误钩子**：重写 `on_calculate_error()` 处理计算错误
- ✅ **记录日志**：在计算逻辑中记录关键信息，便于调试

---

## 常见问题

### Q1: 如何查看 Tag 计算结果？

**A**: Tag 值存储在数据库的 `tag_value` 表中，可以通过 DataManager 查询：

```python
from core.modules.data_manager import DataManager

data_mgr = DataManager()
tag_service = data_mgr.stock.tags

# 查询某个实体的所有 tags
tag_values = tag_service.load_tag_values(
    entity_id="000001.SZ",
    as_of_date="20251219"
)
```

### Q2: 如何增量更新 Tag？

**A**: 在 `settings.py` 中设置 `update_mode: "incremental"`，系统会自动从最后更新日期开始计算。

### Q3: 如何强制重新计算所有 Tag？

**A**: 在 `settings.py` 中设置 `recompute: True`，系统会删除旧的 Tag 值并重新计算。

### Q4: 一个 TagWorker 可以产生多个 Tags 吗？

**A**: 可以。一个 TagWorker 可以为多个 Tags 提供计算逻辑，在 `settings.py` 的 `tags` 列表中定义多个 Tag，在 `calculate_tag()` 中根据 `tag_definition.get_name()` 判断计算哪个 Tag。

### Q5: 如何控制内存使用？

**A**: 
- 使用 Chunk 模式（`use_chunk: True`）
- 调整 `data_chunk_size`（默认 500，最小 300）
- 系统已通过单 entity 单进程控制内存，每个进程只处理一个 entity

### Q6: 如何查看执行进度？

**A**: 创建 TagManager 时设置 `is_verbose=True`，系统会实时显示执行进度：

```python
tag_manager = TagManager(is_verbose=True)
tag_manager.execute()
```

输出示例：
```
🚀 开始执行 100 个 jobs (scenario: momentum, workers: 4)...
📊 进度: 2/100 (2.0%) | 成功: 2, 失败: 0, ETA: 98.0s
📊 进度: 4/100 (4.0%) | 成功: 4, 失败: 0, ETA: 96.0s
...
✅ 完成: 100/100 (100.0%) | 成功: 98, 失败: 2
```

---

## 相关文档

- **[ARCHITECTURE.md](./ARCHITECTURE.md)**：架构文档，包含详细的技术设计、数据流、运行时 Workflow 和重要决策记录
- **[PRIMARY_TEST_CASES.md](./__test__/PRIMARY_TEST_CASES.md)**：单元测试用例文档
- **示例配置**：`userspace/tags/example_settings.py` - 完整的配置示例

---

**文档结束**
