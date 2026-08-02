# Market Profile API 文档

**版本：** `0.2.0`  
**最低支持核心版本：** `>=0.4.0`

> 须与 `module_info.yaml` 一致。公开入口状态最高 **`beta`**。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。

**公开约定：** 包根仅导出 `MarketRulesProxy`；规则基类从 [`contracts.py`](./contracts.py) 导入。

---

## MarketRulesProxy

**描述：** 市场规则代理（实例化后挂载默认市场）

#### __init__

`MarketRulesProxy(default_market: str = "china_a_stock")`

- **状态：** `beta`
- **引入版本：** `0.1.0`

#### set_market / get_market / current

`proxy.set_market(profile_id)`  
`proxy.get_market(profile_id) -> MarketBaseRules`  
`proxy.current -> MarketBaseRules`

- **状态：** `beta`
- **描述：** 挂载当前市场 / 取指定市场 / 当前挂载实例

#### list_available / is_available / get_market_id

- **状态：** `beta`
- **描述：** 可用市场列表、是否存在、当前市场 ID
