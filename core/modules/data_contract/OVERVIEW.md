# Data Contract 使用概览

**版本：** `0.6.0`

## 快速开始

```python
from core.modules.data_contract import ContractIssuer
from core.modules.data_contract.contracts import DATA_KEY

contract = ContractIssuer.issue(DATA_KEY.STOCK_LIST, fill_in_data=True)
stock_list = contract.get_data()
```

## 导入约定

| 用途 | import |
|------|--------|
| 签发契约 | `from core.modules.data_contract import ContractIssuer` |
| 键值与基类 | `from core.modules.data_contract.contracts import DATA_KEY, BaseDataContract` |

## 文档

- [API.md](./API.md)
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
- [docs/DESIGN.md](./docs/DESIGN.md)
