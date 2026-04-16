# 输出适配器（`userspace/adapters/`）

这里是**扫描结果的“出口层”**：策略先算出机会（`Opportunity` 列表），Adapter 再决定这些机会如何展示或发送到别的地方。

您可以把 Adapter 理解成“机会结果的最后一跳”：

- Strategy 的扫描功能是负责“找机会”
- Adapter 就是负责怎么处理这些找到的机会？发个短信通知谁？收集结果进行机器学习？都取决于您怎么使用adapter

注意：目前adapter还非常初级，没有加什么特色功能，将在以后的版本中加入更多。

---

## 一分钟上手（用现有 `console`）

1. 打开您的策略配置（例如 `userspace/strategies/example/settings.py`）
2. 确认 `scanner.adapters` 里包含 `console`
3. 运行扫描：

```bash
python start-cli.py scan --strategy example
```

只要策略扫到机会，`console` adapter 就会在终端打印结果。

---

## 白话版：从 0 创建一个新 Adapter

### Step 1）创建目录

```text
userspace/adapters/my_adapter/
├── adapter.py
└── settings.py
```

目录名 `my_adapter`，就是您后面在策略里要填写的名字。

### Step 2）写 `settings.py`（可选但推荐）

```python
settings = {
    "name": "my_adapter",
    "format": "json",
}
```

### Step 3）写 `adapter.py`（核心）

```python
from typing import Any, Dict, List
from core.modules.adapter import BaseOpportunityAdapter
from core.modules.strategy.models.opportunity import Opportunity


class MyAdapter(BaseOpportunityAdapter):
    def process(self, opportunities: List[Opportunity], context: Dict[str, Any]) -> None:
        strategy = context.get("strategy_name", "unknown")
        self.log_info(f"[{strategy}] opportunities={len(opportunities)}")
        for opp in opportunities:
            print(f"{opp.stock_id} {opp.stock_name} @ {opp.trigger_date}")
```

### Step 4）在策略里启用

```python
"scanner": {
    "max_workers": "auto",
    "adapters": ["console", "my_adapter"],
}
```

### Step 5）运行验证

```bash
python start-cli.py scan --strategy example
```

---

## 当前内置示例

- `console/`：控制台打印 + 历史统计展示
- `example/`：最小示例（json/csv 输出演示）

## 更多说明

- 完整使用说明见 [USER_GUIDE.md](USER_GUIDE.md)
- 模块侧设计见 [core/modules/adapter/README.md](../../core/modules/adapter/README.md)
