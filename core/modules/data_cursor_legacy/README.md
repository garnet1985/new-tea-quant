# Data Cursor 模块（`modules.data_cursor`）

在 **已加载** 的 `DataContract` 上维护 **as-of 前缀累计视图**；多源编排用 `DataCursor` / `DataCursorManager`，单 contract 可直接调用 **`DataContract.until(as_of)`**（内部委托本模块）。

```python
from core.modules.data_cursor import DataCursor, DataCursorManager
from core.modules.data_contract.contracts import DataContract, DataKey

# 多源
cursor = DataCursor(contracts={DataKey.STOCK_KLINE_DAILY: contract})
rows_by_source = cursor.until("20240601")

# 单源（contract 句柄自带裁剪）
rows = contract.until("20240601")
```

见 [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)。
