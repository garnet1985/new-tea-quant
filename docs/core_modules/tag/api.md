# Tag 模块 API 文档

按「描述、函数签名、参数、输出、示例」列出 Tag 模块中**用户会直接调用或需要覆盖的接口**；由框架自动调用的内部函数尽量不列入。架构与设计见 `architecture.md` / `decisions.md`，快速上手见 `overview.md`。

---

## TagManager

### TagManager（构造函数）

**描述**：创建标签计算管理器。负责发现业务场景（Scenario）、构建 jobs 并调度多进程执行。通常在脚本或 CLI 中构造一次后复用。

**函数签名**：`TagManager(is_verbose: bool = False)`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `is_verbose` | `bool` | 是否输出更详细日志，默认 `False` |

**输出**：无（构造实例）

**Example**：

```python
from core.modules.tag.core.tag_manager import TagManager

tag_manager = TagManager(is_verbose=True)
```

---

### execute

**描述**：执行标签计算。可指定单个场景名，也可不传场景名以执行所有启用的场景。内部会按实体列表构建 jobs，并通过多进程 worker 调用各自的 TagWorker。

**函数签名**：`TagManager.execute(scenario_name: str | None = None, settings: Dict[str, Any] | None = None) -> None`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `scenario_name` | `str \| None` | 场景名称；为 `None` 时执行所有已发现且 `is_enabled=True` 的场景 |
| `settings` | `Dict[str, Any] \| None` | 临时场景配置（仅用于测试/开发）；传入后会跳过缓存，直接基于该配置执行一次 |

**输出**：`None`（计算结果写入标签库 `sys_tag_value` 等表）

**Example**：

```python
from core.modules.tag.core.tag_manager import TagManager

manager = TagManager(is_verbose=True)

# 执行所有启用的场景
manager.execute()

# 仅执行单个场景
manager.execute(scenario_name="momentum_mid_term")
```

---

## BaseTagWorker（扩展用）

### BaseTagWorker.calculate_tag

**描述**：标签计算基类的方法，所有自定义 TagWorker 都需要覆盖此方法，实现单个实体在某一日期的标签计算逻辑。框架在回放历史数据时，会对每个实体、每个日期调用一次 `calculate_tag()` 并将结果写入标签表。

**函数签名**：`BaseTagWorker.calculate_tag(as_of_date: str, historical_data: Dict[str, Any], tag_definition: "TagModel") -> Optional[Dict[str, Any]]`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `as_of_date` | `str` | 计算日期（`YYYYMMDD`） |
| `historical_data` | `Dict[str, Any]` | 已预加载的历史数据（如 `klines`, `fundamental`, 其他依赖标签等） |
| `tag_definition` | `TagModel` | 当前计算的标签定义（包含 name、display_name 等元信息） |

**输出**：`Optional[Dict[str, Any]]` ——  
- `None`：表示该日期不生成标签；  
- 字典：至少包含 `"value"` 键（可以是 `str` / `dict` / `list`），可选 `"start_date"` / `"end_date"` 等字段。

**Example**（自定义 Worker）：

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
        current_kline = daily_klines[-1]
        # ... 你的信号逻辑 ...
        return {
            "value": {"signal": 1},
        }
```

**常用属性（子类可访问）**：

- `self.entity`: 当前实体信息（如 `{"id": "000001.SZ", "type": "stock"}`）  
- `self.scenario`: 当前场景信息（name 等）  
- `self.config`: 当前场景完整配置（来自 `settings.py`）  
- `self.tag_data_service`: `TagDataService` 实例，可用于读取历史标签数据  

**生命周期钩子（可选覆盖）**：

- `on_init()`：Worker 初始化完成后调用  
- `on_before_execute_tagging()`：开始对当前实体执行标签计算前调用  
- `on_after_execute_tagging(result)`：单个实体所有标签计算完成后调用  

---

## TagDataService（运行时读取）

**模块路径**：`core.modules.data_manager.data_services.stock.sub_services.tag_service.TagDataService`

**描述**：通过 `DataManager` 提供的标签数据服务，用于在策略代码或分析脚本中按场景维度读取标签值。推荐使用 `load_values_for_entity()` 作为统一的读取入口。

**获取实例**：

```python
from core.modules.data_manager import DataManager

data_mgr = DataManager()
tag_service = data_mgr.stock.tags  # TagDataService 实例
```

### load_values_for_entity

**描述**：按实体 + 场景 + 日期区间读取标签值，是**策略/分析代码推荐使用的读取接口**。对外只暴露场景名，不要求调用方关心内部 tag_definition 细节。

**函数签名**：`load_values_for_entity(entity_id: str, scenario_name: str, start_date: str, end_date: str, entity_type: str = "stock") -> List[Dict[str, Any]]`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `entity_id` | `str` | 实体 ID（如 `"000001.SZ"`） |
| `scenario_name` | `str` | 场景名称（对应 Tag 场景 settings 中的 `name`） |
| `start_date` | `str` | 起始日期（`YYYYMMDD`，含） |
| `end_date` | `str` | 截止日期（`YYYYMMDD`，含） |
| `entity_type` | `str` | 实体类型，默认 `"stock"` |

**输出**：`List[Dict[str, Any]]` —— 标签值列表；每条记录通常包含：

- `entity_id`, `tag_definition_id`, `as_of_date`, `start_date`, `end_date`, `json_value`  
- 以及对应标签定义的 `tag_name`, `tag_display_name`, `scenario_id` 等。

**Example**：

```python
from core.modules.data_manager import DataManager

data_mgr = DataManager()
tag_service = data_mgr.stock.tags

values = tag_service.load_values_for_entity(
    entity_id="000001.SZ",
    scenario_name="momentum_mid_term",
    start_date="20240101",
    end_date="20241231",
)

for v in values:
    print(v["as_of_date"], v["tag_name"], v["json_value"])
```

---

## 相关说明

- **计算入口**：通过 `TagManager.execute()` 或命令行 `start-cli.py tag --scenario <name>` 执行标签计算。  
- **运行时读取**：通过 `DataManager().stock.tags.load_values_for_entity()` 在策略或分析代码中按场景读取标签。  
- **扩展点**：新增标签时，只需在 `userspace/tags/<scenario>/settings.py` 与 `tag_worker.py` 中编写配置和逻辑，框架会自动发现并执行。  

