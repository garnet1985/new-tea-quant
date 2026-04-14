# Adapter 模块（`modules.adapter`）

策略 **Scanner** 完成扫描后，将 `Opportunity` 列表与上下文交给用户配置的 **adapter** 做后续处理（控制台展示、Webhook、入库等）。本模块提供 **`BaseOpportunityAdapter`** 基类、**`validate_adapter`** 校验、以及可选的 **`HistoryLoader`**（读取价格模拟结果用于展示统计）。实际加载与调用在 **`core.modules.strategy.components.scanner.AdapterDispatcher`** 中完成。

## 适用场景

- 在 **`userspace/adapters/<名称>/adapter.py`** 中实现自定义输出或对接外部系统。
- 在策略的 **scanner** 配置中列出 `adapters`（如 `["console"]`），由框架按名称加载并依次调用。
- 在设置校验阶段确认某 adapter 模块可加载且存在合法子类（`validate_adapter`）。

## 快速开始

1. 新建目录 `userspace/adapters/my_adapter/`，添加 `adapter.py`：

```python
from typing import Any, Dict, List

from core.modules.adapter import BaseOpportunityAdapter
from core.modules.strategy.models.opportunity import Opportunity


class MyAdapter(BaseOpportunityAdapter):
    def process(
        self,
        opportunities: List[Opportunity],
        context: Dict[str, Any],
    ) -> None:
        self.log_info(f"收到 {len(opportunities)} 条机会")
```

2. 可选：同目录下 `settings.py` 中定义 `settings = { ... }`，在 `process` 内用 `self.get_config("key")` 读取。

3. 在策略 scanner 配置中加入 `adapters` 列表，包含目录名 `my_adapter`。

内置示例见 `userspace/adapters/console/`、`userspace/adapters/example/`。

## 目录结构（本模块）

```text
core/modules/adapter/
├── module_info.yaml
├── __init__.py
├── base_adapter.py          # BaseOpportunityAdapter
├── adapter_validator.py     # validate_adapter
├── history_loader.py        # HistoryLoader
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN.md
    ├── API.md
    └── DECISIONS.md
```

用户扩展目录约定见 [DESIGN.md](docs/DESIGN.md)。

## 模块依赖（`module_info.yaml`）

- **`modules.strategy`**：`BaseOpportunityAdapter.process` 使用 `Opportunity` 类型；`HistoryLoader` 通过策略侧的 `VersionManager`、`ResultPathManager` 解析结果路径。

## 相关文档

- [架构与边界](docs/ARCHITECTURE.md)
- [设计与扩展约定](docs/DESIGN.md)
- [公开 API](docs/API.md)
- [设计决策](docs/DECISIONS.md)
