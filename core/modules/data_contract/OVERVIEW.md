# Data Contract — 使用概览

**模块：** `modules.data_contract` · **版本：** 0.5.0

面向 **Strategy / Tag** 的声明式取数 Facade。settings 声明 `DataKey` → **`DataContracts.issue`** 签发句柄；加载后 **`DataContracts.until(contract, as_of)`** 提供 PIT 前缀裁剪（委托 **`modules.data_cursor`**）。

---

## 快速开始

```python
from core.modules.data_contract import DataContracts
from core.modules.data_contract.contracts import DataKey

DataContracts.shared_cache().enter_strategy_run()
dcm = DataContracts()

issued = dcm.issue(
    DataKey.STOCK_KLINE_DAILY,
    entity_ids=["000001.SZ"],
    start="20240101",
    end="20241231",
    adjust="qfq",
)
contract = issued.require_one()

# Facade 裁剪（内部用 data_cursor）
pit = dcm.until(contract, "20240601")

# 多源编排仍用 data_cursor 模块
from core.modules.data_cursor import DataCursor

cursor = DataCursor(contracts={DataKey.STOCK_KLINE_DAILY: contract})
all_sources = cursor.until("20240601")

DataContracts.shared_cache().exit_strategy_run()
```

---

## 公开入口

| 入口 | 内容 |
|------|------|
| `from core.modules.data_contract import DataContracts` | Facade（`issue` / `load` / `until` / 时间 helper） |
| `from core.modules.data_contract.contracts import …` | **仅类与枚举**（`DataKey`、`DataContract`、`IssueResult` 等） |
| [`api.yaml`](api.yaml) | 机器可读 API 契约（替代已删除的 `docs/API.md`） |

**缓存：** `DataContracts()` 默认开启 GLOBAL 进程内 cache；PER_ENTITY **永不 cache**。run 边界调用 `DataContracts.shared_cache().enter_strategy_run()` / `exit_strategy_run()`。

---

## 内部分层（`core/`）

| 层级 | 目录 | 职责 |
|------|------|------|
| **L1 registry** | `core/registry/` | `DataKey`、`default_map`、userspace 合并 |
| **L2 issue** | `core/issue/` | 签发、`load`、cache guard |
| **L3 contract** | `core/contract/` | `DataContract`、`IssueResult` |
| **L4 load** | `core/load/` | Loader / `load_batch` |
| **L5 cache** | `core/cache/` | 进程内 GLOBAL / per-strategy store |

**`modules.data_cursor`** 保持独立：多源 `DataCursor` / `DataCursorManager`。

---

## 相关文档

- [架构与分层](docs/ARCHITECTURE.md)
- [API 契约](api.yaml)
- [演进路线](docs/ROADMAP.md)
- [单元测试](__test__/README.md)
- [data_cursor 模块](../data_cursor/README.md)
