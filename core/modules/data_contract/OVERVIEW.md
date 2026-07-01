# Data Contract — 使用概览

**模块：** `modules.data_contract` · **版本：** 0.4.0

面向 **Strategy / Tag** 的声明式取数 Facade。settings 声明 `DataKey` → **`DataContracts.issue`** 签发句柄；物化后的 **`DataContract.until(as_of)`** 提供 PIT 前缀裁剪（委托 **`modules.data_cursor`**）。

---

## 快速开始

```python
from core.modules.data_contract import DataContracts
from core.modules.data_contract.contracts import ContractCacheManager, DataKey

cache = ContractCacheManager()
cache.enter_strategy_run()
dcm = DataContracts(contract_cache=cache)

result = dcm.issue(
    DataKey.STOCK_KLINE_DAILY,
    entity_ids=["000001.SZ"],
    start="20240101",
    end="20241231",
    adjust="qfq",
)
contract = result.require_one()

# 单 contract 裁剪（内部用 data_cursor）
pit_rows = contract.until("20240601")

# 多源编排仍用 data_cursor 模块
from core.modules.data_cursor import DataCursor

cursor = DataCursor(contracts={DataKey.STOCK_KLINE_DAILY: contract})
all_sources = cursor.until("20240601")

cache.exit_strategy_run()
```

---

## 内部分层（`core/`）

| 层级 | 目录 | 职责 |
|------|------|------|
| **L1 registry** | `core/registry/` | `DataKey`、`default_map`、userspace 合并 |
| **L2 issue** | `core/issue/` | 签发主流程 |
| **L3 contract** | `core/contract/` | `DataContract`、`IssueResult`；**`until` 委托 data_cursor** |
| **L4 load** | `core/load/` | Loader / `load_batch` |
| **L5 cache** | `core/cache/` | 进程内缓存 |

**`modules.data_cursor`** 保持独立：多源 `DataCursor` / `DataCursorManager`；单源可直接 `contract.until`。

---

## 相关文档

- [架构与分层](docs/ARCHITECTURE.md)
- [data_cursor 模块](../data_cursor/README.md)
- [API 契约](api.yaml)
