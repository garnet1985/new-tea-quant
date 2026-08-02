# Data Contract

**模块：** `modules.data_contract` · **版本：** `0.6.0`

DataKey 白名单与契约签发：meta / runtime / specific 三层结构。

## 使用

```python
from core.modules.data_contract import ContractIssuer
from core.modules.data_contract.contracts import DATA_KEY, BaseDataContract

contract = ContractIssuer.issue(DATA_KEY.STOCK_LIST, fill_in_data=True)
data = contract.get_data()
```

## 文档

- [API.md](./API.md)
- [QUICKSTART.md](./QUICKSTART.md)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)

包根仅 `ContractIssuer`；`DATA_KEY` 与基类从 `contracts.py` 导入。
