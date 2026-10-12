# 股票维度表

板块、交易所、地域仍是「字典 + 映射」，由 `stock_list` renew 写入。

| 字典表 | 映射表 | 含义 |
|--------|--------|------|
| `sys_boards` | `sys_stock_board_map` | 板块（主板/创业板等） |
| `sys_markets` | `sys_stock_market_map` | 交易所（Tushare `exchange`） |
| `sys_areas` | `sys_stock_area_map` | 地域 |

行业用申万 2021，不走 `stock_basic.industry`。

| 表 | 含义 |
|----|------|
| `sys_sw_industry` | 分类树。主键是指数代码，含一、二、三级 |
| `sys_sw_stock_industry_map` | 一只股票当前的一、二、三级 |
| `sys_sw_industry_kline` | 一级行业日线，外加申万 A 指 `801003.SI` |

- 写入：数据源 `sw_industry`、`sw_stock_industry`、`sw_industry_kline`
- 按行业筛股票：`ListService.load(industry=一级名称或指数代码)`
- 展示名：申万一级。`StockService.load_with_latest_price` 和 `ListService.load_meta` 都读这一级
- 数据键：`sw.industry`（分类树）、`sw.industry.list`（一级行业加申万 A 指）、`stock.sw_industry`（一只股票当前的一、二、三级）、`sw.industry.kline.daily`（一级行业日线）
