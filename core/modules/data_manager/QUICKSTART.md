# Data Manager — 快速开始

**模块：** `modules.data_manager` · **版本：** `0.2.1`

```python
from core.modules.data_manager import DataManager

dm = DataManager()
rows = dm.stock.list.load()
klines = dm.stock.kline.load("000001.SZ", term="daily")
# 顶层 close 为前复权；行内 raw / hfq / adj_factor
```

```bash
python -m pytest core/modules/data_manager/__test__/test_api.py -q
```
