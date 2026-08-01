# Data Contract 模块（`modules.data_contract`）

用 **`DATA_KEY`** 声明数据依赖，**`ContractIssuer.issue`** 签发句柄；时序契约加载后 **`contract.until(as_of)`** 做 PIT 前缀推进。

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
pit = contract.until("20240601")
```

跨模块类型从 **`contracts.py`** 导入（基类 / 枚举）。

## 目录结构

```text
core/modules/data_contract/
├── __init__.py            # ContractIssuer / DATA_KEY
├── contracts.py           # 公开类型
├── core/
│   ├── discovery/         # ContractIssuer
│   ├── base/              # Base*Contract（含 until / CursorState）
│   └── data_contracts/    # 各 DATA_KEY 的 declaration / loader
└── docs/
```

## 测试

```bash
python3 -m pytest core/modules/data_contract/__test__/ -q
```
