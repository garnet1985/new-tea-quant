# Core Utils - 通用工具模块

提供各种与业务无关的辅助工具类和服务。

## 📦 模块结构

```
core/utils/
├── __init__.py          # 统一导出所有工具
├── util.py              # 配置合并工具
├── date/
│   └── date_utils.py    # 日期工具类
└── icon/
    └── icon_service.py  # 图标服务
```

## 🚀 快速开始

### 统一导入（推荐）

```python
from core.utils import (
    DateUtils,           # 日期工具
    i,                  # 图标服务（简化 API）
    IconService,        # 图标服务（完整 API）
    deep_merge_config,  # 配置合并
)
```

## 📚 各模块说明

### 1. 日期工具 (DateUtils)

提供统一的日期转换和处理方法。

```python
from core.utils import DateUtils

# 获取当前日期
date = DateUtils.get_today_str()  # "20240116"

# 日期格式转换
date_str = DateUtils.yyyymmdd_to_yyyy_mm_dd("20240116")  # "2024-01-16"

# 计算日期差
days = DateUtils.get_duration_in_days("20240101", "20240116")  # 15

# 季度转换
quarter = DateUtils.date_to_quarter("20240116")  # "2024Q1"
```

### 2. 图标服务 (IconService / i)

提供 emoji 图标获取服务。

#### 简化 API（推荐）

```python
from core.utils import i

# 简洁的调用方式
icon = i("green_dot")   # 🟢
icon = i("success")     # ✅
icon = i("error")        # ❌
icon = i("info")         # ℹ️
```

#### 完整 API（向后兼容）

```python
from core.utils import IconService

icon = IconService.get("green_dot")  # 🟢
```

#### 支持的图标

- **状态图标**: `success`, `error`, `warning`, `info`
- **点状图标**: `green_dot`, `red_dot`, `blue_dot`, `yellow_dot`, `orange_dot`, `purple_dot`, `white_dot`, `black_dot`, `brown_dot`
- **功能图标**: `search`, `calendar`, `bar_chart`, `line_chart`, `money`, `rocket`, `gear`, `clock`, `target`, `ongoing`

### 3. 配置合并工具 (util)

提供配置文件的深度合并功能。

```python
from core.utils import deep_merge_config, merge_mapping_configs

# 深度合并配置
defaults = {"params": {"a": 1, "b": 2}}
custom = {"params": {"b": 3, "c": 4}}
result = deep_merge_config(
    defaults, 
    custom, 
    deep_merge_fields={"params"}
)
# result["params"] = {"a": 1, "b": 3, "c": 4}

# 合并 mapping 配置
defaults_mapping = {"kline": {"handler": "default.handler", "params": {"a": 1}}}
custom_mapping = {"kline": {"params": {"b": 2}}}
result = merge_mapping_configs(
    defaults_mapping,
    custom_mapping,
    deep_merge_fields={"params"}
)
```


## 📝 最佳实践

### 1. 使用简化 API

优先使用简化的 API，代码更简洁：

```python
# ✅ 推荐
from core.utils import i
icon = i("green_dot")

# ❌ 不推荐（除非需要向后兼容）
from core.utils import IconService
icon = IconService.get("green_dot")
```

### 2. 统一导入

从 `core.utils` 统一导入，避免分散的导入：

```python
# ✅ 推荐
from core.utils import DateUtils, i, deep_merge_config

# ❌ 不推荐
from core.utils.date.date_utils import DateUtils
from core.utils.icon.icon_service import i
```

## 🔄 迁移指南

### 从 IconService.get() 迁移到 i()

```python
# 旧代码
from core.utils.icon.icon_service import IconService
icon = IconService.get("green_dot")

# 新代码（推荐）
from core.utils import i
icon = i("green_dot")
```

原有 API 仍然可用，可以逐步迁移。
