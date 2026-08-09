# Data Manager 模块（`modules.data_manager`）· **版本 0.4.0**

> 公开 API：[API.md](./API.md) · 快速开始：[QUICKSTART.md](./QUICKSTART.md)  
> 包根仅 `DataManager`；`BaseTableNames` → `contracts.py`；领域服务经 `DataManager.*` 属性访问

进程内 **统一数据访问门面**：持有 **`DatabaseManager`**，启动时创建库表、发现 **`core/tables`** 与 **`userspace/extensions/tables`** 下的 `schema.py`/`model.py` 并注册 **`DbBaseModel`**，再装配 **`DataService`**（`stock`、`macro`、`calendar`、`index`、`db_cache`、`backup_restore`）。

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
├── API.md / QUICKSTART.md / README.md
├── contracts.py
├── data_manager.py          # Facade（后续随 core/ 下沉调整）
├── data_services/           # 领域服务
├── __test__/                # 公开 API 契约测
└── docs/
    ├── ARCHITECTURE.md
    └── DESIGN.md
```

## 依赖（`module_info.yaml`）

- **`infra.db`**
- **`infra.project_context`**

## 测试

```bash
python -m pytest core/modules/data_manager/__test__/test_api.py -q
```

用例索引见 [`__test__/TEST_CASES.md`](__test__/TEST_CASES.md)。

## 相关文档

- [架构](docs/ARCHITECTURE.md)
- [设计](docs/DESIGN.md)
- [API](API.md)
- [glossary](glossary.yaml)
