# 股票维度表：不是重复，是「字典 + 映射」

## 模型

| 字典表（定义） | 映射表（股票 → 字典 id） | 含义 |
|----------------|-------------------------|------|
| `sys_industries` | `sys_stock_industry_map` | 行业名 ↔ `industry_id` |
| `sys_boards` | `sys_stock_board_map` | 板块（主板/创业板等） |
| `sys_markets` | `sys_stock_market_map` | 交易所（Tushare `exchange`） |
| `sys_areas` | `sys_stock_area_map` | 地域 |

主表 **`sys_stock_list`** 只存证券主数据：`id`、`name`、`list_status`、`list_date`、`delist_date` 等，**不**再内嵌 `industry` / `board` 列。

## 代码入口

- 写入：`ListService.ensure_and_sync_*` + `stock_list` renew（Tushare `stock_basic`）
- 读取：`ListService.load(industry=…)` / `load_by_industry` → 先查 map，再 JOIN `sys_stock_list`
- 跨表展示：`StockService.load_with_latest_price` → `sys_stock_list` + `sys_stock_industry_map` + `sys_industries` + K 线

## 不要删其中一套

删掉 `sys_industries` 只留 map 会丢失行业名称；删掉 map 只留 list 会无法多股共享同一行业 id。两套都是当前设计的一部分。
