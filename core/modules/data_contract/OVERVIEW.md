# Data Contract — 使用概览

**模块：** `modules.data_contract`

面向 **Strategy / Tag** 的声明式取数。`DATA_KEY` → **`ContractIssuer.issue`** 签发句柄；时序契约加载后用 **`contract.until(as_of)`** 做 PIT 前缀推进（`CursorState` 内置于 `BaseTimeSeriesContract`）。

---

## 快速开始

```python
from core.modules.data_contract import ContractIssuer, DATA_KEY

contract = ContractIssuer.issue(
    DATA_KEY.STOCK_KLINE_DAILY,
    entity_ids=["000001.SZ"],
    runtime={
        "start_time": "20240101",
        "end_time": "20241231",
    },
    fill_in_data=True,
)

# PIT 前缀（推进各 entity 的 cursor）
pit = contract.until("20240601")
# pit = {"000001.SZ": [截至 as_of 的累计行…]}
```

---

## 公开入口

| 入口 | 内容 |
|------|------|
| `from core.modules.data_contract import ContractIssuer, DATA_KEY` | 签发与数据键 |
| `from core.modules.data_contract.contracts import …` | 基类与类型（`BaseTimeSeriesContract`、`CursorState` 等） |

---

## 相关文档

- [架构与分层](docs/ARCHITECTURE.md)
- [设计说明](docs/DESIGN.md)
- [决策记录](docs/DECISIONS.md)
