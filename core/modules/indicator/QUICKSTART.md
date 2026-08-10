# Indicator — 快速开始

**模块：** `modules.indicator` · **版本：** `0.3.0`

最短路径：对 K 线算 MA / RSI。

---

## 最小示例

```python
from core.modules.indicator import Indicator

klines = [
    {"date": "20251201", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.2, "volume": 1000},
    # ... 足够长度
]
ma = Indicator.ma(klines, length=20)
rsi = Indicator.rsi(klines, length=14)
```

---

## 下一步

- [API.md](./API.md)
- [docs/AVAILABLE_INDICATORS.md](./docs/AVAILABLE_INDICATORS.md)

```bash
python3 -m pytest core/modules/indicator/__test__/test_api.py -q
```
