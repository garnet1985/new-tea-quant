# Core Utils - 通用工具模块

提供各种与业务无关的辅助工具类和服务。

## 模块结构

```
core/utils/
├── __init__.py          # 统一导出
├── utils.py             # Utils 类（类型判断、DataFrame）
├── math/                # 数值 / 确定性随机
└── date/
    └── date_utils.py    # 日期工具类
```

CLI 图标请使用 ``core.infra.cmd_layout``（``CmdLayout.icon`` / ``IconService`` / ``i``）。

## 快速开始

```python
from core.utils import (
    DateUtils,
    deterministic_unit_float,
)
```

配置 dict 合并请使用 `core.infra.project_context.ConfigManager`：

```python
from core.infra.project_context import ConfigManager

ConfigManager.deep_merge_config(defaults, custom, deep_merge_fields={"params"})
ConfigManager.merge_mapping_configs(defaults_mapping, custom_mapping, deep_merge_fields={"params"})
```

## 各模块说明

### 1. 日期工具 (DateUtils)

```python
from core.utils import DateUtils

date = DateUtils.get_today_str()  # "20240116"
date_str = DateUtils.yyyymmdd_to_yyyy_mm_dd("20240116")  # "2024-01-16"
days = DateUtils.get_duration_in_days("20240101", "20240116")  # 15
quarter = DateUtils.date_to_quarter("20240116")  # "2024Q1"
```

### 2. 类型与 DataFrame 工具 (`Utils`)

`core.utils.utils.Utils` 提供类型判断与 pandas 薄封装；配置合并见 `ConfigManager`。
