# Data Contract 用户指南

本指南说明如何在 `userspace/data_contract/` 扩展自己的数据契约，并在 Strategy / Tag 中稳定复用。

---

## 1. 核心概念

- **`data_id`**：业务数据的稳定标识（建议全局唯一、长期不变）。
- **mapping**：声明 `data_id -> spec`，包含 scope、type、loader、时序轴等。
- **loader**：真正执行加载逻辑的实现，由 Data Contract 在运行时按 `loader` 字段解析。
- **contract**：`DataContractManager.issue(...)` 返回的句柄；缓存策略由 core 侧统一处理。

---

## 2. 文件职责

- `mapping.py`
  - 维护 `custom_map`。
  - 每个 key 是一个 `data_id`；value 是对应 spec。
- `loaders/`
  - 放置用户自定义 loader（建议一类数据一个文件）。
  - 实现约束以 core 侧 `BaseLoader` 与 loader 发现机制为准。
- `__init__.py`
  - 包说明与导出（可保持轻量）。

---

## 3. mapping 字段建议

以下字段按当前项目约定最常见：

- `scope`：`GLOBAL` / `PER_ENTITY`（来自 `ContractScope`）
- `type`：`TIME_SERIES` / `NON_TIME_SERIES`（来自 `ContractType`）
- `loader`：loader 标识（与 loader 实现对应）
- `display_name`：展示名（可读性）
- `defaults`：默认参数（可被 issue 时覆盖）

时序数据建议补齐：

- `unique_keys`：如 `["date", "entity_id"]`
- `time_axis_field`：如 `"date"`
- `time_axis_format`：如 `"YYYYMMDD"`

---

## 4. 推荐命名规范

- `data_id` 建议：`<domain>.<dataset>[.<variant>]`
  - 示例：`user.sentiment.daily`
- `loader` 建议与 `data_id` 对齐，降低心智负担。
- 一旦上线被策略依赖，尽量不要重命名 `data_id`，避免历史配置失效。

---

## 5. 端到端示例

### 5.1 定义 mapping

```python
from core.modules.data_contract.contract_const import ContractScope, ContractType

custom_map = {
    "user.sentiment.daily": {
        "scope": ContractScope.PER_ENTITY,
        "type": ContractType.TIME_SERIES,
        "unique_keys": ["date", "entity_id"],
        "time_axis_field": "date",
        "time_axis_format": "YYYYMMDD",
        "loader": "user.sentiment.daily",
        "display_name": "用户情绪日频",
        "defaults": {"source": "internal"},
    }
}
```

### 5.2 在业务中取数

```python
from core.modules.data_contract import ContractCacheManager, DataContractManager

cache = ContractCacheManager()
cache.enter_strategy_run()

dcm = DataContractManager(contract_cache=cache)
contract = dcm.issue(
    "user.sentiment.daily",
    entity_id="000001.SZ",
    start="20240101",
    end="20241231",
    source="internal",
)
rows = contract.load()

cache.exit_strategy_run()
```

---

## 6. 常见问题

### Q1: `data_id` 没生效？

- 检查 `mapping.py` 里是否真的加入了 `custom_map`。
- 检查 key 命名是否与业务侧 `issue(...)` 一致（大小写、点号）。

### Q2: 时序过滤不生效？

- 确认 `type=TIME_SERIES`。
- 确认 `time_axis_field` 与数据行字段一致（比如都用 `date`）。
- 确认时间格式和传参格式一致（`YYYYMMDD`）。

### Q3: 同一个 `data_id` 多处定义冲突？

- 保持 userspace 只维护一份定义。
- 推荐在 PR 中把新 `data_id` 列表写进变更说明，避免重复占名。

---

## 7. 与其它模块的关系

- Strategy/Tag 在 settings 里声明所需 `data_id`，运行时通过 Data Contract 统一签发。
- Data Contract 负责 map 合并、cache、contract 生命周期；userspace 负责业务扩展定义。

---

## 8. 参考文档

- [core/modules/data_contract/README.md](../../core/modules/data_contract/README.md)
- [core/modules/data_contract/docs/API.md](../../core/modules/data_contract/docs/API.md)
- [userspace/data_contract/README.md](README.md)
