# Data Manager 模块（`modules.data_manager`）

进程内 **统一数据访问门面**：持有 **`DatabaseManager`**，启动时创建库表、递归发现 **`core/tables`** 与 **`userspace/tables`** 下的 `schema.py`/`model.py` 并注册 **`DbBaseModel`**，再装配 **`DataService`**（`stock`、`macro`、`calendar`、`index`、`db_cache`）。业务代码通过 **`data_mgr.stock.kline.load(...)`** 等显式路径访问，避免直接依赖底层 Model。

子目录 **`data_services/`** 含各领域实现说明，见 [`data_services/README.md`](data_services/README.md)。

## 适用场景

- 读写股票列表、K 线、标签、财报、宏观、交易日历、指数与 DB 缓存等内置表数据。
- 扩展 **userspace 表**（目录发现后 `register_table` 自动参与）。
- 与 **`modules.data_contract`** 的 Loader 协同（Loader 内部调用 `DataManager`）。

## 快速开始

```python
from core.modules.data_manager import DataManager

dm = DataManager(is_verbose=True)
rows = dm.stock.kline.load("000001.SZ", term="daily", start_date="20240101", end_date="20241231")
```

## 目录结构（本模块）

```text
core/modules/data_manager/
├── module_info.yaml
├── README.md
├── data_manager.py
├── enums.py
├── helpers/
├── data_services/        # StockService、MacroService、…
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN.md
    ├── API.md
    └── DECISIONS.md
```

## 模块依赖（`module_info.yaml`）

- **`infra.db`**：`DatabaseManager`、`DbBaseModel`、Schema。
- **`infra.project_context`**：表路径发现、`ConfigManager`（经 DB 配置链）。

## 测试

本模块当前无独立 `__test__/` 目录；数据库与表相关单测主要在 **`core/infra/db/__test__/`**。若为本模块补充单元测试，建议新增 `core/modules/data_manager/__test__/` 并在仓库根执行 `python3 -m pytest <path> -q`。

## 相关文档

- [架构与边界](docs/ARCHITECTURE.md)
- [设计与表发现](docs/DESIGN.md)
- [公开 API（含各 Service 索引）](docs/API.md)
- [设计决策](docs/DECISIONS.md)
