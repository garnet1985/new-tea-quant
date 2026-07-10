# Market Profile 使用示例

## 基本使用

```python
from core.modules.market_profile import MarketRulesProxy

# 创建Proxy实例（默认挂载A股）
proxy = MarketRulesProxy()

# 或指定默认市场
proxy = MarketRulesProxy(default_market="us_stock")
```

## 当前市场操作

```python
# 获取当前挂载的市场规则
current_rules = proxy.current  # ChinaAStockRules 类型

# 使用当前市场规则
ratio = current_rules.get_limit_ratio()  # 0.1 (10%)
up, down = current_rules.compute_limit_prices_for_stock(10.0, "688001.SH")
# (12.0, 8.0)  # 科创板±20%

# 判断整手规则
qty = current_rules.floor_quantity_for_stock(150, "688001.SH")  # 0（低于最小200）
qty = current_rules.floor_quantity_for_stock(250, "688001.SH")  # 250

# 交收规则
can_sell = current_rules.is_allowed_to_sell(0)  # False（A股T+1）
```

## 切换市场

```python
# 挂载港股市场
proxy.mount("hong_kong")
hk_rules = proxy.current  # HongKongRules 类型

# 使用港股规则
can_sell = hk_rules.is_allowed_to_sell(0)  # True（港股T+0）

# 挂载美股市场
proxy.mount("us_stock")
us_rules = proxy.current  # USStockRules 类型
qty = us_rules.floor_quantity(50)  # 50（美股1股起）
```

## 跨市场操作

```python
# 列出所有可用市场
markets = proxy.list_available()
# ['china_a_stock', 'hong_kong', 'us_stock', 'commodity_future', 'forex', 'crypto']

# 获取特定市场的规则（不切换当前市场）
china_rules = proxy.get_market("china_a_stock")
hk_rules = proxy.get_market("hong_kong")

# 对比不同市场
china_ratio = china_rules.get_limit_ratio()  # 0.1
hk_ratio = hk_rules.get_limit_ratio()  # 0.0（无涨跌幅限制）

# 判断市场是否可用
if proxy.is_available("japan_stock"):
    japan_rules = proxy.get_market("japan_stock")
```

## A股市场详细示例

```python
proxy = MarketRulesProxy(default_market="china_a_stock")
rules = proxy.current

# 1. 涨跌幅限制

# 主板股票
ratio = rules.get_limit_ratio_for_stock("000001.SZ")  # 0.1 (10%)
up, down = rules.compute_limit_prices_for_stock(10.0, "000001.SZ")
# (11.0, 9.0)

# 科创板股票
ratio = rules.get_limit_ratio_for_stock("688001.SH")  # 0.2 (20%)
up, down = rules.compute_limit_prices_for_stock(10.0, "688001.SH")
# (12.0, 8.0)

# 创业板股票
ratio = rules.get_limit_ratio_for_stock("300001.SZ")  # 0.2 (20%)

# 北交所股票
ratio = rules.get_limit_ratio_for_stock("430047.BJ")  # 0.3 (30%)

# ST股票（风险标签）
ratio = rules.get_limit_ratio_for_stock("000001.SZ", status_tags=["st"])  # 0.05 (5%)
up, down = rules.compute_limit_prices_for_stock(10.0, "000001.SZ", status_tags=["st"])
# (10.5, 9.5)

# 2. 整手规则

# 主板股票
qty = rules.floor_quantity_for_stock(150, "000001.SZ")  # 100
qty = rules.floor_quantity_for_stock(250, "000001.SZ")  # 200
is_valid = rules.is_valid_quantity_for_stock(150, "000001.SZ")  # False

# 科创板股票
qty = rules.floor_quantity_for_stock(150, "688001.SH")  # 0（低于最小200）
qty = rules.floor_quantity_for_stock(250, "688001.SH")  # 250（步长1）
is_valid = rules.is_valid_quantity_for_stock(250, "688001.SH")  # True

# 3. 交收规则

can_sell = rules.is_allowed_to_sell(0)  # False（当日不可卖）
can_sell = rules.is_allowed_to_sell(1)  # True（次日可卖）
period = rules.get_settlement_period()  # 1 (T+1)
```

## 其他市场示例

```python
# 美股：无涨跌幅限制，1股起
proxy.mount("us_stock")
rules = proxy.current
ratio = rules.get_limit_ratio()  # 0.0
qty = rules.floor_quantity(1)  # 1

# 港股：无涨跌幅限制，100股起
proxy.mount("hong_kong")
rules = proxy.current
qty = rules.floor_quantity(150)  # 100

# 期货：按品种涨跌幅不同
proxy.mount("commodity_future")
rules = proxy.current
ratio = rules.get_limit_ratio_for_stock("SC.F")  # 0.08（能源）

# 外汇：标准手（100,000）
proxy.mount("forex")
rules = proxy.current
qty = rules.floor_quantity(150000)  # 100000

# 数字货币：极小单位
proxy.mount("crypto")
rules = proxy.current
qty = rules.floor_quantity(100)  # 100
```

## 类型安全

```python
from core.modules.market_profile import MarketRulesProxy
from core.modules.market_profile.core.base.market_base_rules import MarketBaseRules
from core.modules.market_profile.core.markets.china_a_stock import ChinaAStockRules

proxy = MarketRulesProxy()

# 类型明确
rules: ChinaAStockRules = proxy.current  # IDE自动推断类型
ratio: float = rules.get_limit_ratio()  # IDE提示返回类型

# 获取特定类型
china_rules: ChinaAStockRules = proxy.get_market("china_a_stock")
us_rules: USStockRules = proxy.get_market("us_stock")
```

## 添加新市场

### 1. 创建配置文件

```python
# core/markets/japan_stock/settings.py
settings = {
    "key": "japan_stock",
    "meta": {
        "name": "日本股市",
        "description": "日本股票市场交易规则",
    },
    "settlement": {
        "t_plus": 0
    },
    "amplitude_limit": {
        "default_ratio": 0.0,
        "price_round_decimals": 2
    },
    "lot_size": {
        "default_min_lot": 100,
        "default_lot_step": 100
    }
}
```

### 2. 创建规则类

```python
# core/markets/japan_stock/rules.py
from typing import Any, Dict
from ..base.market_base_rules import MarketBaseRules

class JapanStockRules(MarketBaseRules):
    @property
    def profile_id(self) -> str:
        return "japan_stock"
    
    @property
    def settings(self) -> Dict[str, Any]:
        from .settings import settings
        return settings
```

### 3. 注册到注册表

```python
# core/markets/__init__.py
from .japan_stock import JapanStockRules

MARKET_RULES_REGISTRY = {
    ...
    "japan_stock": JapanStockRules,
}
```

完成！新市场自动可用。