# Market Profile 模块

市场交易规则的统一查询和管理API。

## 快速开始

```python
from core.modules.market_profile import MarketRulesProxy

# 创建Proxy（默认A股）
proxy = MarketRulesProxy()

# 使用当前市场
rules = proxy.current
ratio = rules.get_limit_ratio_for_stock("688001.SH")  # 0.2 (科创板20%)

# 切换市场
proxy.mount("us_stock")
us_rules = proxy.current
qty = us_rules.floor_quantity(50)  # 50（美股1股起）

# 列出所有可用市场
markets = proxy.list_available()
# ['china_a_stock', 'hong_kong', 'us_stock', 'commodity_future', 'forex', 'crypto']
```

## 架构设计

```
market_profile/
├── market_profile.py              # MarketRulesProxy（对外暴露）
├── core/
│   ├── base/
│   │   └── market_base_rules.py   # MarketBaseRules（基类）
│   ├── markets/                   # 所有市场
│   │   ├── china_a_stock/
│   │   │   ├── rules.py           # ChinaAStockRules
│   │   │   └── settings.py        # ChinaAStockSettings
│   │   ├── hong_kong/
│   │   ├── us_stock/
│   │   ├── commodity_future/
│   │   ├── forex/
│   │   ├── crypto/
│   │   └── __init__.py            # 注册表
│   └── services/                  # 通用服务
│       ├── matching_service.py
│       ├── lot_size_service.py
│       ├── amplitude_limit_service.py
│       └── settlement_service.py
```

## 设计特点

1. **基类提供默认实现**：所有方法都有通用实现
2. **子类只需提供settings**：配置驱动，代码简洁
3. **可选覆盖**：子类可覆盖特殊方法实现特殊逻辑
4. **类型安全**：所有方法都有类型注解

## 支持的市场

| 市场 | profile_id | 特点 |
|------|-----------|------|
| 中国A股 | china_a_stock | T+1，涨跌幅限制（主板10%，科创板/创业板20%，北交所30%） |
| 港股 | hong_kong | T+0，无涨跌幅限制 |
| 美股 | us_stock | T+0，无涨跌幅限制，1股起 |
| 商品期货 | commodity_future | T+0，涨跌幅按品种不同（能源8%，金属6%，农产品4%） |
| 外汇 | forex | T+0，标准手（100,000） |
| 数字货币 | crypto | T+0，24小时，极小单位 |

## 添加新市场

1. 在 `core/markets/` 下创建新市场目录
2. 创建 `settings.py`（定义配置）
3. 创建 `rules.py`（继承 MarketBaseRules）
4. 在 `core/markets/__init__.py` 注册

## 更多文档

- [USAGE.md](./USAGE.md)：完整使用示例
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)：架构设计文档