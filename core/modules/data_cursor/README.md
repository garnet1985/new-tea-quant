# Data Cursor 模块（`modules.data_cursor`）

在 **已物化的时序数据** 上维护 **单调游标**：对每个数据源按时间字段推进到 **`as_of`（含）**，返回 **累计前缀** 视图，避免在按日回测/打标签时把 **未来 bar** 暴露给策略或 Tag worker。**`DataCursorManager`** 按名称注册多个会话，供 **`StrategyWorkerDataManager`**、**`TagWorkerDataManager`** 等调用 **`rebuild_data_cursor`** 时使用。

## 适用场景

- 多 **`DataKey`** 对应的多路 **`DataContract.data`** 已 **`load`** 完毕，需按交易日 **`as_of`** 逐步「只看到过去」。
- Strategy **`_current_data`** 风格的 **`rows_by_source`** 字典，需 **`DataCursor.from_rows`** 快速构建。

## 快速开始

```python
from core.modules.data_cursor import DataCursor, DataCursorManager
from core.modules.data_contract.contracts import DataContract

# 假定 contracts 已为各 key 填好 .data
mgr = DataCursorManager()
cursor = mgr.create_cursor("main", contracts_by_key)
view = cursor.until("20240115")  # Dict[source, List[dict]] 前缀累计
```

## 目录结构

```text
core/modules/data_cursor/
├── module_info.yaml
├── README.md
├── __init__.py
├── data_cursor.py
├── data_cursor_manager.py
└── docs/
    ├── ARCHITECTURE.md
    ├── DESIGN.md
    ├── API.md
    └── DECISIONS.md
```

## 模块依赖（`module_info.yaml`）

- **`modules.data_contract`**：`DataContract`、`ContractType` 元信息解析时间轴字段。

## 相关文档

- [架构与边界](docs/ARCHITECTURE.md)
- [时间与前缀语义](docs/DESIGN.md)
- [公开 API](docs/API.md)
- [设计决策](docs/DECISIONS.md)
