# Data Contract — 快速开始

**模块：** `modules.data_contract` · **版本：** `0.4.0`

```python
from core.modules.data_contract import ContractIssuer
from core.modules.data_contract.contracts import DATA_KEY

contract = ContractIssuer.issue(
    DATA_KEY.STOCK_KLINE_DAILY,
    entity_ids=["600000.SH"],
    runtime={"start_time": "20200101", "end_time": "20201231", "adjust": "qfq"},
    fill_in_data=True,
)
data = contract.get_data()
```

```bash
python3 -m pytest core/modules/data_contract/__test__/test_api.py -q
```
