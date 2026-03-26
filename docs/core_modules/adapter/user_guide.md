# Adapter · Userspace 使用指南

在 `userspace/adapters/` 下实现扫描结果的后续处理逻辑（通知、入库、对接第三方等）。框架在策略扫描完成后将机会列表与上下文交给你配置的 adapter，无需改 core。

---

## 目录结构

```
userspace/adapters/
└── <adapter_name>/          # 如 console、example、my_notifier
    ├── adapter.py           # 必选：继承 BaseOpportunityAdapter，实现 process
    └── settings.py          # 可选：settings 字典，供 get_config() 读取
```

**约定**：目录名即 adapter 名称，策略里通过该名称引用（如 `scanner.adapters: ["console", "my_notifier"]`）。

---

## 新增一个 Adapter

1. **建目录**：`userspace/adapters/<adapter_name>/`。

2. **adapter.py**：写一个类继承 `BaseOpportunityAdapter`，实现 `process(opportunities, context) -> None`。
   - `opportunities`：`List[Opportunity]`，本次扫描得到的机会。
   - `context`：`Dict`，含 `date`、`strategy_name`、`scan_summary` 等。
   - 配置用 `self.get_config("key", default)`；日志用 `self.log_info` / `self.log_warning` / `self.log_error`。

3. **settings.py**（可选）：定义 `settings = { ... }`，adapter 内通过 `self.get_config("key")` 读取。

4. **在策略里启用**：在该策略的 scanner 配置中增加 adapter 名称，例如：
   - 若使用 `settings.py`（策略配置）：在 scanner 段设置 `adapters: ["console", "<adapter_name>"]`。
   - 若使用 YAML：在 `scanner_settings` 或等价配置里写 `adapters: ["<adapter_name>"]`。

框架从 `userspace.adapters.<adapter_name>.adapter` 加载模块并查找继承 `BaseOpportunityAdapter` 的类。

---

## 示例

**adapter.py**：

```python
from typing import List, Dict, Any
from core.modules.adapter import BaseOpportunityAdapter
from core.modules.strategy.models.opportunity import Opportunity

class MyNotifierAdapter(BaseOpportunityAdapter):
    def process(self, opportunities: List[Opportunity], context: Dict[str, Any]) -> None:
        fmt = self.get_config("format", "json")
        self.log_info(f"处理 {len(opportunities)} 个机会，格式: {fmt}")
        # 你的逻辑：写 DB、发通知、调 API 等
```

**settings.py**：

```python
settings = {
    "name": "my_notifier",
    "format": "json",
}
```

策略 scanner 配置中：`adapters: ["console", "my_notifier"]`。

---

## 读取历史模拟结果（可选）

若需要在 adapter 或其它地方展示历史胜率等，使用 `HistoryLoader`（与 userspace 目录无关，在代码中调用即可）：

- `HistoryLoader.load_stock_history(strategy_name, stock_id)` — 单只股票历史统计。
- `HistoryLoader.load_session_summary(strategy_name)` — 最新会话汇总。

详见 [api.md](./api.md)。

---

## 相关文档

- [API 文档](./api.md)
- [概览](./overview.md)
- [架构](./architecture.md)
