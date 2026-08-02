# Data Manager — 快速开始

**模块：** `modules.data_manager` · **版本：** `0.4.0`

```python
from core.modules.data_manager import DataManager

dm = DataManager()
rows = dm.stock.list.load()
```

```bash
NTQ_TESTS_ENABLED=1 python -m pytest core/modules/data_manager/__test__/test_api.py -q
```
