# Market Profile — 快速开始

**模块：** `modules.market_profile` · **版本：** `0.2.0`

```python
from core.modules.market_profile import MarketRulesProxy

proxy = MarketRulesProxy()
rules = proxy.current
print(rules.profile_id, rules.get_limit_ratio())
```

```bash
python3 -m pytest core/modules/market_profile/__test__/test_api.py -q
```
