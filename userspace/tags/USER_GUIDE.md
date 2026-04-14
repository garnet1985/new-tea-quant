# 标签用户指南（userspace）

本指南给“要自己写标签场景”的用户，目标是：快速跑通一个标签场景，并知道如何从简单场景扩展到可复用资产。

---

## 1. 标签场景由什么组成？

每个标签场景目录通常就两份核心文件：

- `settings.py`：声明这个场景要算什么、需要什么数据、怎么更新
- `tag_worker.py`：实现每个业务日的标签计算逻辑

框架负责：

- 按场景发现和调度
- 按实体/日期并发执行
- 标签结果落库

你负责：

- 标签定义和业务计算逻辑

---

## 2. `entity_based` 和 `general` 怎么选？

- `entity_based`：标签属于某个实体（例如每只股票一条标签）
- `general`：标签属于全局上下文（例如宏观环境）

如果用 `general`，通常需要在 `data` 里补 `tag_time_axis_based_on` 指定时间轴来源。

---

## 3. 最小可运行模板

目录：

```text
userspace/tags/my_tag_scenario/
├── settings.py
└── tag_worker.py
```

`settings.py` 示例：

```python
from core.global_enums.enums import EntityType, UpdateMode

Settings = {
    "is_enabled": True,
    "name": "my_tag_scenario",
    "display_name": "我的标签场景",
    "description": "demo",
    "tag_target_type": "entity_based",
    "target_entity": {"type": EntityType.STOCK_KLINE_DAILY.value},
    "data": {
        "required": [
            {"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}},
        ],
    },
    "update_mode": UpdateMode.INCREMENTAL.value,
    "core": {},
    "performance": {"max_workers": "auto"},
    "tags": [
        {"name": "my_tag", "display_name": "我的标签", "description": "demo"},
    ],
}
```

`tag_worker.py` 示例：

```python
from typing import Any, Dict, Optional
from core.modules.tag.base_tag_worker import BaseTagWorker


class MyTagWorker(BaseTagWorker):
    def calculate_tag(
        self,
        as_of_date: str,
        historical_data: Dict[str, Any],
        tag_definition: Any,
    ) -> Optional[Dict[str, Any]]:
        klines = historical_data.get("stock.kline", [])
        if not klines:
            return None
        latest = klines[-1]
        return {"value": {"as_of_date": as_of_date, "close": latest.get("close")}}
```

---

## 4. 运行命令

### 跑所有已启用场景

```bash
python start-cli.py tag
```

### 跑指定场景

```bash
python start-cli.py tag --scenario my_tag_scenario
```

---

## 5. 进阶建议（实用）

- 先用 `example/` 跑通链路，再写复杂逻辑
- 标签数量多时，优先做“只在状态变化时写入”（参考 `example_activity_high` 思路）
- 保持 `name` 稳定，避免历史标签定义混乱
- `core` 只放业务参数（阈值、窗口等），便于后续调参

---

## 6. 常见问题

### Q1：场景没被执行？

- 检查 `Settings["is_enabled"]`
- 检查命令里的 `--scenario` 是否和 `Settings["name"]` 一致

### Q2：`historical_data` 里拿不到你要的数据？

- 检查 `settings.py` 的 `data.required` 是否声明了对应 `data_id`
- 检查 `data_id` 拼写是否一致（例如 `stock.kline`）

### Q3：标签写入太多、太乱？

- 优先考虑“状态变化才写入”的策略（delta）
- 给 `tags` 写清晰的 `name/display_name/description`

---

## 7. 参考

- 入口文档：`userspace/tags/README.md`
- 模块设计：`core/modules/tag/README.md`
- 示例场景：`userspace/tags/example`、`userspace/tags/momentum`、`userspace/tags/macro_regime`
