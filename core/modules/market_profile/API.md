# Market Profile API 文档

**版本：** `0.2.0`  
**最低支持核心版本：** `>=0.4.1`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `MarketRulesProxy`；规则基类与类型从 [`contracts.py`](./contracts.py) 导入（`MarketBaseRules`、`LotSizeResolved`）。

---

## MarketRulesProxy

**描述：** 市场制度规则门面（挂载 / 查询 / 单市场工厂）

### for_market

`MarketRulesProxy.for_market(profile_id: str) -> MarketBaseRules`

- **类型：** `classmethod`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 创建单个市场规则实例（跨模块推荐入口；不预加载其它市场）
- **异常：** 未知 `profile_id` → `ValueError`

### available_ids

`MarketRulesProxy.available_ids() -> list[str]`

- **类型：** `classmethod`
- **状态：** `beta`
- **描述：** 注册表中全部市场 ID（不实例化）

### __init__

`MarketRulesProxy(default_market: str = "china_a_stock")`

- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 构造并挂载默认市场；其它市场按需懒加载

### set_market / get_market / current

`proxy.set_market(profile_id: str) -> None`  
`proxy.get_market(profile_id: str) -> MarketBaseRules`  
`proxy.current -> MarketBaseRules`

- **状态：** `beta`
- **描述：** 挂载当前市场 / 取指定市场（同 Proxy 内缓存）/ 当前挂载实例
- **异常：** 未知市场 → `ValueError`；未挂载读 `current` → `RuntimeError`

### list_available / is_available / get_market_id

`proxy.list_available() -> list[str]`  
`proxy.is_available(profile_id: str) -> bool`  
`proxy.get_market_id() -> str`

- **状态：** `beta`
- **描述：** 可用市场列表、是否存在、当前市场 ID

---

## MarketBaseRules（经 `current` / `for_market` / `get_market`）

**描述：** 单市场规则实例；从 `contracts` 导入类型。常用方法：

| 方法 | 说明 |
|------|------|
| `get_limit_ratio()` / `get_limit_ratio_for_stock(stock_id, status_tags=None)` | 默认 / 按票涨跌幅比例 |
| `compute_limit_prices(prev_close)` / `compute_limit_prices_for_stock(...)` | 涨跌停价 |
| `is_at_limit_up` / `is_at_limit_down` | 贴涨停 / 贴跌停 |
| `get_min_lot` / `resolve_lot_size` / `floor_quantity_for_stock` | 整手 |
| `get_settlement_period` / `is_allowed_to_sell` | T+N 交收 |

- **状态：** `beta`
