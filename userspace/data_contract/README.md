# Data Contract（`userspace/data_contract/`）

这里是 **Data Contract 的用户扩展入口**：你可以定义一种“新的数据类型”，然后让 strategy/tag 在配置里直接引用它。

简单来说，先理解 3 个概念：

- `data_id`：这类数据的名字（必须唯一，建议长期稳定）。
- `mapping`：这个数据的说明书（范围、是否时序、用哪个 loader）。
- `loader`：真正把数据拿回来的代码实现。

这三者连起来，就是一个新的数据契约。

## 一分钟上手（用已有示例理解）

看 `mapping.py` 里注释掉的示例 `custom_map`，你会看到：

- 一个 `data_id`（比如 `user.example.daily_series`）
- 这个数据是按实体取（`scope=PER_ENTITY`）
- 这是时序数据（`type=TIME_SERIES`）
- 时间字段是什么（`time_axis_field=date`）
- 用哪个 loader 去取（`loader=user.example.daily_series`）

最小验证代码：

```python
from core.modules.data_contract import ContractCacheManager, DataContractManager

cache = ContractCacheManager()
dcm = DataContractManager(contract_cache=cache)

contract = dcm.issue(
    "user.example.daily_series",
    entity_id="000001.SZ",
    start="20240101",
    end="20241231",
)
rows = contract.load()
```

---

## 白话版：从 0 创建一个新数据契约

### Step 1）先给它一个不重复的名字

先起一个 `data_id`，例如：`user.sentiment.daily`。  
建议规则：`<domain>.<dataset>[.<variant>]`。

### Step 2）在 `mapping.py` 写清楚“这是什么数据”

在 `custom_map` 里新增一项。最少写：

- `scope`
- `type`
- `loader`

如果是时序数据，建议再补：

- `unique_keys`
- `time_axis_field`
- `time_axis_format`

例如：

```python
custom_map = {
    "user.sentiment.daily": {
        "scope": ContractScope.PER_ENTITY,
        "type": ContractType.TIME_SERIES,
        "loader": "user.sentiment.daily",
        "unique_keys": ["date", "entity_id"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMMDD",
        "defaults": {},
    }
}
```

### Step 3）在 `loaders/` 里实现 loader

新增对应 loader 文件，逻辑保持“输入参数清晰、输出字段稳定”。

```python
# userspace/data_contract/loaders/sentiment_daily_loader.py
class SentimentDailyLoader(...):
    def load(self, entity_id: str, start: str, end: str, **kwargs):
        ...
```

### Step 4）做一次最小验证

- 用 `dcm.issue(...)` 按 `data_id` 取 contract
- 调 `load()`
- 看返回字段是否符合预期（尤其时间字段和实体字段）

### Step 5）接入 Strategy / Tag

在 strategy/tag 的 `settings` 里引用这个 `data_id`，先小样本跑通。

## 目录结构

```text
userspace/data_contract/
├── __init__.py
├── mapping.py
├── loaders/
│   └── __init__.py
└── USER_GUIDE.md
```

## 更多说明

- 详细字段与排错建议见 [USER_GUIDE.md](USER_GUIDE.md)
- Core 侧接口说明见 [core/modules/data_contract/README.md](../../core/modules/data_contract/README.md)
