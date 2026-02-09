# Tag 模块 API 文档

> 本文档描述 Tag 模块的**公共 API**（类、方法、参数与返回值）。  
> 架构与设计决策见同目录下的 `architecture.md` 与 `decisions.md`，快速上手见 `overview.md`。

---

## 1. 运行入口与调度层

### 1.1 TagManager

**模块路径**：`core.modules.tag.core.tag_manager.TagManager`

标签计算管理器：负责**发现业务场景、构建 jobs、调度多进程执行**。

#### 构造函数

```python
TagManager(is_verbose: bool = False)
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `is_verbose` | bool | 是否输出详细日志 |

#### 主要方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `execute` | `execute(scenario_name: str \| None = None)` | 执行场景：`None` 表示执行所有启用的场景，传入场景名仅执行单个 |

**典型用法**：

```python
from core.modules.tag.core.tag_manager import TagManager

tag_manager = TagManager(is_verbose=True)

# 执行所有启用的场景
tag_manager.execute()

# 或仅执行单个场景
tag_manager.execute(scenario_name="momentum_mid_term")
```

> 实际生产场景中，一般通过 `start-cli.py tag --scenario <name>` 间接调用 TagManager。

---

## 2. 场景与标签模型

### 2.1 ScenarioModel

**模块路径**：`core.modules.tag.core.models.scenario_model.ScenarioModel`

封装单个业务场景（Scenario）的配置、元信息与更新模式决策。

#### 创建与配置

```python
from core.modules.tag.core.models.scenario_model import ScenarioModel

scenario = ScenarioModel.create_from_settings(settings_dict)
```

| 方法 | 签名 | 说明 |
|------|------|------|
| `create_from_settings` | `create_from_settings(settings: Dict[str, Any]) -> ScenarioModel \| None` | 从 `settings.py` 的字典创建场景模型，若配置无效返回 `None` |
| `is_setting_valid` | `is_setting_valid(settings: Dict[str, Any]) -> bool` | 静态方法，校验 settings 是否满足最小要求 |

#### 常用实例方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `is_enabled()` | bool | 场景是否启用 |
| `get_name()` / `get_identifier()` | str | 场景名称（settings.name） |
| `get_target_entity()` | str | 目标实体类型（如 `"stock_kline_daily"`） |
| `get_tag_models()` | `List[TagModel]` | 场景下的标签定义模型列表 |
| `get_tags_dict()` | `Dict[str, Dict]` | 标签名到标签配置的映射（序列化形式） |
| `get_settings()` | `Dict[str, Any]` | 完整 settings 字典（含默认值填充） |
| `calculate_update_mode()` | `TagUpdateMode` | 计算本次执行的更新模式（`INCREMENTAL` / `REFRESH`） |
| `ensure_metadata(tag_data_mgr)` | `None` | 使用 `TagDataService` 确保 scenario / tag definitions 在 DB 中存在且元信息正确 |

> 一般无需在业务代码中直接操作 `ScenarioModel`，而是通过 TagManager 自动使用。

### 2.2 TagModel（简要）

**模块路径**：`core.modules.tag.core.models.tag_model.TagModel`

场景内单个标签（Tag Definition）的模型。TagWorker 在计算时会收到 `TagModel` 实例。

常见属性（只读）：

- `id`: 标签定义 ID（DB 主键）
- `name`: 标签唯一代码
- `display_name`: 显示名称
- `description`: 描述

常见方法：

| 方法 | 说明 |
|------|------|
| `get_name()` | 返回标签代码 |
| `to_dict()` | 序列化为字典（用于日志/调试） |
| `ensure_metadata(tag_data_mgr, scenario_id, recompute: bool)` | 在 DB 中创建/更新对应的 `sys_tag_definition` 记录 |

---

## 3. 标签计算 Worker 层

### 3.1 BaseTagWorker

**模块路径**：`core.modules.tag.core.base_tag_worker.BaseTagWorker`

标签计算的基类，所有自定义 TagWorker 必须继承该类并实现 `calculate_tag()`。

#### 子类实现示例

```python
from typing import Dict, Any, Optional
from core.modules.tag.core.base_tag_worker import BaseTagWorker
from core.modules.tag.core.models.tag_model import TagModel


class MyTagWorker(BaseTagWorker):
    def calculate_tag(
        self,
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_definition: TagModel,
    ) -> Optional[Dict[str, Any]]:
        daily_klines = historical_data["klines"]["daily"]
        # ... 计算逻辑 ...
        return {
            "value": {"signal": 1},
            # 可选：起止日期
            # "start_date": "20250101",
            # "end_date": "20250131",
        }
```

#### 需要实现的方法

| 方法 | 签名 | 说明 |
|------|------|------|
| `calculate_tag` | `calculate_tag(as_of_date: str, historical_data: Dict[str, Any], tag_definition: TagModel) -> Optional[Dict[str, Any]]` | 计算单个标签在 `as_of_date` 的取值。返回 `None` 表示不生成标签；返回字典时至少包含 `"value"` 字段（可以是 str/dict/list），可选 `"start_date"`, `"end_date"` |

#### 常用属性（在子类中可访问）

| 属性 | 类型 | 说明 |
|------|------|------|
| `entity` | `Dict[str, Any]` | 当前实体信息（如 `{"id": "000001.SZ", "type": "stock"}`） |
| `scenario` | `Dict[str, Any]` | 当前场景信息（name 等） |
| `config` | `Dict[str, Any]` | 当前场景的完整配置 |
| `tag_data_service` | `TagDataService` | 标签数据服务，用于查询历史标签数据等 |

#### 生命周期钩子（可选覆盖）

| 钩子 | 说明 |
|------|------|
| `on_init()` | Worker 初始化完成后调用 |
| `on_before_execute_tagging()` | 执行标签计算前调用 |
| `on_after_execute_tagging(result)` | 单个实体所有标签计算完成后调用 |

底层保存逻辑由框架负责：`BaseTagWorker` 会在内部收集 `calculate_tag()` 的返回值，并通过 `TagDataService.save_batch()` 批量写入 `sys_tag_value`。

---

## 4. 运行时数据访问：TagDataService

**模块路径**：`core.modules.data_manager.data_services.stock.sub_services.tag_service.TagDataService`

通过 `DataManager` 访问标签数据：

```python
from core.modules.data_manager import DataManager

data_mgr = DataManager()
tag_service = data_mgr.stock.tags  # TagDataService 实例
```

### 4.1 Scenario 相关 API

#### `load_scenario`

```python
load_scenario(scenario_name: str) -> Optional[Dict[str, Any]]
```

- 按 name 加载场景元信息（来自 `sys_tag_scenario`）。

#### `save_scenario`

```python
save_scenario(
    scenario_name: str,
    display_name: str | None = None,
    description: str | None = None,
) -> Dict[str, Any]
```

- 创建/更新一个场景（按 `name` 唯一 upsert），返回最新元信息。

#### `update_scenario`

```python
update_scenario(
    scenario_id: int,
    scenario_name: str | None = None,
    display_name: str | None = None,
    description: str | None = None,
    current_scenario: Dict[str, Any] | None = None,
) -> Dict[str, Any]
```

- 更新场景的可变字段（name/display_name/description）。

#### `list_scenarios`

```python
list_scenarios(scenario_name: str | None = None) -> List[Dict[str, Any]]
```

- 不传参数：返回所有场景。  
- 传 `scenario_name`：只返回该 name 的场景（或空列表）。

#### `delete_scenario`

```python
delete_scenario(scenario_id: int, cascade: bool = False) -> None
```

- 删除指定场景；`cascade=True` 时会先删除该场景下的 tag values 与 tag definitions。

---

### 4.2 Tag Definition 相关 API

#### `load`

```python
load(tag_name: str, scenario_id: int) -> Optional[Dict[str, Any]]
```

- 按 `(scenario_id, name)` 唯一键加载单个标签定义。

#### `save`

```python
save(
    tag_name: str,
    scenario_id: int,
    display_name: str,
    description: str = "",
) -> Dict[str, Any]
```

- 创建/更新标签定义（按 `(scenario_id, name)` upsert），返回最新记录。

#### `get_tag_definitions`

```python
get_tag_definitions(scenario_id: int | None = None) -> List[Dict[str, Any]]
```

- 传 `scenario_id`：只返回该场景下的标签列表；否则返回所有标签定义。

#### `update_tag_definition`

```python
update_tag_definition(
    tag_definition_id: int,
    display_name: str | None = None,
    description: str | None = None,
    current_tag: Dict[str, Any] | None = None,
) -> Dict[str, Any]
```

- 更新标签定义的非关键字段。

#### `batch_update_tag_definitions`

```python
batch_update_tag_definitions(
    updates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]
```

- 批量更新 display_name / description，内部通过单条 `UPDATE ... CASE WHEN ...` SQL 实现。

#### 删除相关

```python
delete_tag_definition(tag_definition_id: int) -> None
delete_tag_definitions_by_scenario(scenario_id: int) -> None
```

- 前者删除单个标签定义，后者删除某场景下的所有定义。

---

### 4.3 Tag Value 相关 API

#### `save_value`

```python
save_value(tag_value_data: Dict[str, Any]) -> int
```

- 保存单个标签值，按 `(entity_id, tag_definition_id, as_of_date)` upsert。  
- `tag_value_data` 应包含：`entity_id`, `tag_definition_id`, `as_of_date`, 可选 `start_date`, `end_date`, `entity_type`, `json_value` 等。

#### `save_batch`

```python
save_batch(tag_values: List[Dict[str, Any]]) -> int
```

- 批量保存标签值（同样按 `(entity_id, tag_definition_id, as_of_date)` upsert）。

#### `delete_tag_values_by_scenario`

```python
delete_tag_values_by_scenario(scenario_id: int) -> None
```

- 通过 JOIN `sys_tag_definition` 一次性删除某场景下所有标签值。

#### `get_max_as_of_date`

```python
get_max_as_of_date(tag_definition_ids: List[int]) -> Optional[str]
```

- 查询一组标签定义的最大 `as_of_date`，用于增量计算起点决策。

#### `get_tag_value_last_update_info`

```python
get_tag_value_last_update_info(scenario_name: str) -> Dict[str, Dict[str, Any]]
```

- 返回指定场景下，每个 `entity_id` 的最后标签更新时间信息：

```python
{
    "000001.SZ": {
        "max_as_of_date": "20250101",
        "tag_definition_ids": [1, 2, 3],
    },
    ...
}
```

#### `load_values_for_entity`

```python
load_values_for_entity(
    entity_id: str,
    scenario_name: str,
    start_date: str,
    end_date: str,
    entity_type: str = "stock",
) -> List[Dict[str, Any]]
```

- **推荐给策略/分析代码使用的读取接口**：  
  - 对外只暴露 **scenario 名称**，不对外暴露 tag_definition 细节；  
  - 返回某实体在指定场景、指定日期区间内的所有标签值，结果中包含：
    - `entity_id`, `tag_definition_id`, `as_of_date`, `start_date`, `end_date`, `json_value`  
    - 以及对应标签定义的 `tag_name`, `tag_display_name`, `scenario_id`。

---

### 4.4 辅助 API

#### `get_next_trading_date`

```python
get_next_trading_date(date: str) -> str
```

- 返回下一个交易日（当前为简单自然日 +1 的占位实现，将来可接入 CalendarService）。

---

## 5. 总结

- **计算入口**：通过 `TagManager.execute()` 或命令行 `start-cli.py tag --scenario <name>` 执行标签计算。  
- **运行时读取**：通过 `DataManager().stock.tags`（`TagDataService`）按 **Scenario 维度** 读取标签数据，策略侧推荐使用 `load_values_for_entity()`。  
- **扩展点**：新增标签时只需在 `userspace/tags/<scenario>/settings.py` 与 `tag_worker.py` 中编写配置与业务逻辑，无需修改框架代码。  

