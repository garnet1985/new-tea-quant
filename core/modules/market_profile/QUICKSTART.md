# Market Profile — 快速开始

**模块：** `modules.market_profile` · **版本：** `0.2.0`

```python
from core.modules.market_profile import MarketRulesProxy

# 推荐：单市场
rules = MarketRulesProxy.for_market("china_a_stock")
print(rules.profile_id, rules.get_limit_ratio())

# 或挂载式 Proxy
proxy = MarketRulesProxy()
print(proxy.current.get_settlement_period())
```

```bash
python3 -m pytest core/modules/market_profile/__test__/test_api.py -q
```

下一步：[API.md](./API.md) · [glossary.yaml](./glossary.yaml)
