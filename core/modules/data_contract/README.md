# Data Contract 模块（`modules.data_contract`）

用 **`DataKey`** 声明数据依赖，**`DataContracts.issue`** 签发句柄；物化后 **`DataContract.until(as_of)`** 做 PIT 前缀裁剪（委托 **`modules.data_cursor`**，该模块仍独立存在）。

> 版本 **0.4.0**：`core/` 五层结构 + Facade。详见 [`OVERVIEW.md`](OVERVIEW.md)。

## 快速开始

```python
from core.modules.data_contract import DataContracts
from core.modules.data_contract.contracts import ContractCacheManager, DataKey

dcm = DataContracts(contract_cache=ContractCacheManager())
contract = dcm.issue(DataKey.STOCK_KLINE_DAILY, entity_id="000001.SZ", start="20240101", end="20241231").require_one()
rows = contract.until("20240601")
```

## 目录结构

```text
core/modules/data_contract/
├── data_contract.py       # Facade: DataContracts
├── contracts.py
├── core/registry|issue|contract|load|cache/
└── docs/
```

裁剪能力：`DataContract.until` → [`modules.data_cursor`](../data_cursor/README.md)

## 测试

```bash
python3 -m pytest core/modules/data_contract/__test__/ -q
```
