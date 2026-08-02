# Data Contract API 文档

**版本：** `0.6.0`  
**最低支持核心版本：** `>=0.4.1`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。

**公开约定：** 包根仅导出 `ContractIssuer`；基类、`DATA_KEY` 从 [`contracts.py`](./contracts.py) 导入。

---

## ContractIssuer

**描述：** 契约发现、签发与实例化

### issue（推荐）

`ContractIssuer.issue(key, *, entity_ids=None, runtime=None, fill_in_data=False, ...) -> BaseDataContract`

- **状态：** `stable`

### discover / get_contract / list_available_keys

- **状态：** `stable`

**举例：**

```python
from core.modules.data_contract import ContractIssuer
from core.modules.data_contract.contracts import DATA_KEY

contract = ContractIssuer.issue(DATA_KEY.STOCK_LIST, fill_in_data=True)
rows = contract.get_data()
```

---

## contracts

| 符号 | 说明 |
|------|------|
| `DATA_KEY` / `SYS_DATA_KEY` | 契约键值常量 |
| `BaseDataContract` | meta / runtime / specific 三层基类 |
| `BaseTimeSeriesContract` | 时序扩展（until / normalize_as_of） |
| `BaseNonTimeSeriesContract` | 非时序基类 |
| `BaseDataContractLoader` | loader 基类 |
| `ContractType` / `ContractScope` | 枚举 |

自定义 contract：继承基类并在 `userspace/data_contracts/` 提供 declaration + loader。
