# 标签场景（`userspace/tags/`）

这里是**标签用户空间**：你定义“要算什么标签”（`settings.py`），再定义“具体怎么算”（`tag_worker.py`），框架负责按日期和实体批量执行并落库。

简单来说，先理解 3 个概念：

- `scenario`：场景。可以理解为“这套标签在描述什么问题”。比如：当前是否处于经济衰退、哪些公司市值超过 50 亿，这些都可以是一个场景。
- `tag`：标签。是在某个场景下，对某个对象打上的分类结果。比如你把 LPR 低于 3% 定义为“低利率”，那同一场景里就可能有“低利率”“高利率”等多个标签。
- `tag_value`：标签备忘录。用于记录标签产生时的重要信息。还是利率的例子：如果 2 月 1 日 LPR 从 3.25% 降到 2.75%，当天会产生“低利率”标签，`tag_value` 可以把“从多少降到多少”这类原因和上下文一起记录下来（JSON 格式）。

Tag 诞生的目的：
- 从工程角度看，Tag 可以提高运行效率。Strategy 计算时可以直接复用 Tag 结果，不必重复算一遍因子。
- 从投资角度看，Tag 是可复用的特征。比如你做出了“全球经济是否景气”的判断并打成标签，这个结论可以被多个股票、多个策略，甚至其他 Tag 复用。

注意，Tag 有两个种类：
- 一种是针对具体实体的（`entity_based`），比如公司市值标签，它有明确的对象。
- 另一种是不绑定单一实体的（`general`），比如你用 GDP、LPR 等指标判断宏观环境，这类标签描述的是一段时间的总体状态。

这两种标签的声明方式略有不同，请在配置时注意区分。

## 一分钟上手（跑现有示例）

1. 打开某个示例场景（例如 `example/`），确认 `Settings["is_enabled"] = True`。
2. 在仓库根目录执行：

```bash
python start-cli.py tag
```

只跑单个场景：

```bash
python start-cli.py tag --scenario activity-ratio20
```

---

## 白话版：从 0 创建一个新标签场景

### Step 1）先建场景目录

```text
userspace/tags/my_tag_scenario/
├── settings.py
└── tag_worker.py
```

目录名建议与 `Settings["name"]` 保持一致，方便排查。

### Step 2）写 `settings.py`（决定“算什么、按谁算”）

最小建议包含：

- `name`
- `is_enabled`
- `tag_target_type`
- `data.required`
- `update_mode`
- `tags`

示例（`entity_based`）：

```python
from core.global_enums.enums import EntityType, UpdateMode

Settings = {
    "is_enabled": True,
    "name": "my_tag_scenario",
    "tag_target_type": "entity_based",
    "target_entity": {"type": EntityType.STOCK_KLINE_DAILY.value},
    "data": {
        "required": [{"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}}],
    },
    "update_mode": UpdateMode.INCREMENTAL.value,
    "core": {},
    "performance": {"max_workers": "auto"},
    "tags": [{"name": "my_tag", "display_name": "我的标签"}],
}
```

### Step 3）写 `tag_worker.py`（决定“怎么计算”）

核心是实现 `calculate_tag(as_of_date, historical_data, tag_definition)`：

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
        rows = historical_data.get("stock.kline", [])
        if not rows:
            return None
        latest = rows[-1]
        return {"value": {"as_of_date": as_of_date, "close": latest.get("close")}}
```

### Step 4）运行并验证

```bash
python start-cli.py tag --scenario my_tag_scenario
```

### Step 5）看示例和进阶场景

- `example/`：最小可运行示例
- `momentum/`：实体型复杂计算（历史窗口 + 月度逻辑）
- `macro_regime/`：`general` 模式示例（全局宏观标签）

## 目录结构

```text
userspace/tags/
├── README.md
├── USER_GUIDE.md
├── example/
├── momentum/
├── macro_regime/
└── <your_scenario>/
    ├── settings.py
    └── tag_worker.py
```

## 更多说明

- 完整说明见 [USER_GUIDE.md](USER_GUIDE.md)
- 模块侧设计见 [core/modules/tag/README.md](../../core/modules/tag/README.md)
