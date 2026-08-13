# Data Manager 模块（`modules.data_manager`）· **版本 0.4.0**

> 公开 API：[API.md](./API.md) · 快速开始：[QUICKSTART.md](./QUICKSTART.md)  
> 包根仅 `DataManager`；`BaseTableNames` → `contracts.py`；领域服务经 `DataManager.*` 属性访问

进程内 **统一数据访问门面**：持有 **`DatabaseManager`**，发现 **`core/tables`** 与 **`userspace/extensions/tables`**，装配 **`DataService`**。

## 快速开始

```python
from core.modules.data_manager import DataManager

dm = DataManager(is_verbose=True)
rows = dm.stock.kline.load("000001.SZ", term="daily", start_date="20240101", end_date="20241231")
```

## 目录结构

```text
core/modules/data_manager/
├── module_info.yaml / API.md / QUICKSTART.md / README.md
├── contracts.py
├── core/
│   ├── data_manager.py
│   ├── enums.py
│   ├── sample_universe/
│   ├── dev/sample_stock_list/
│   └── data_services/
├── __test__/
└── docs/
```

## 依赖

- **`infra.db`**
- **`infra.project_context`**

## 测试

见 [`__test__/TEST_CASES.md`](__test__/TEST_CASES.md)。

## 相关文档

- [架构](docs/ARCHITECTURE.md)
- [设计](docs/DESIGN.md)
- [API](API.md)
- [glossary](glossary.yaml)
