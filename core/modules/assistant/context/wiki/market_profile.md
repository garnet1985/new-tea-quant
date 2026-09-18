---
title: 市场画像
aliases:
  - market profile
  - trading calendar
  - market rules
  - settlement
summary: 管理NTQ的市场交易规则和交易制度的模块。
---

# 市场档案与交易日历

## 市场档案（Market Profile）

市场档案定义特定市场的制度性规则：涨跌停限制、最小交易单位、结算周期。它不拉取行情、不持久化数据——只提供规则查询。

```python
from core.modules.market_profile import MarketRulesProxy

rules = MarketRulesProxy.for_market("china_a_stock")
```

### 架构

```
MarketRulesProxy
  → MarketBaseRules
      ├── AmplitudeLimitService   涨跌停
      ├── LotSizeService           最小交易单位
      └── SettlementService        结算
          → MatchingService
```

### 内置市场

| market key         | 说明     |
| ------------------ | ------ |
| `china_a_stock`    | 中国 A 股 |
| `hong_kong`        | 港股     |
| `us_stock`         | 美股     |
| `commodity_future` | 商品期货   |
| `forex`            | 外汇     |
| `crypto`           | 加密货币   |

### A 股规则

| 规则类型 | 板块                  | 限制            |
| ---- | ------------------- | ------------- |
| 涨跌停  | 默认                  | ±10%          |
| 涨跌停  | 科创板（688）            | ±20%          |
| 涨跌停  | 创业板（300）            | ±20%          |
| 涨跌停  | 北交所（43/83/87/88/92） | ±30%          |
| 涨跌停  | ST/\*ST             | ±5%           |
| 最小单位 | 默认                  | 100 股 / 100 步 |
| 最小单位 | 科创板                 | 200 股 / 1 步   |
| 最小单位 | 北交所                 | 100 股 / 1 步   |
| 结算   | A 股                 | T+1           |

### 规则匹配

板块通过股票代码前缀匹配：

- `688*` → 科创板

- `300*` → 创业板

- `43/83/87/88/92*` → 北交所

### 查询方法

```python
rules = MarketRulesProxy.for_market("china_a_stock")

# 涨跌停
ratio = rules.get_limit_ratio_for_stock("688001.SH")
limit_up, limit_down = rules.compute_limit_prices(pre_close, "688001.SH")
is_up = rules.is_at_limit_up(close, pre_close, "688001.SH")

# 最小交易单位
min_lot = rules.get_min_lot("688001.SH")
step = rules.get_lot_step("688001.SH")
is_valid = rules.is_valid_quantity(200, "688001.SH")

# 结算
period = rules.get_settlement_period()  # T+1
can_sell = rules.is_allowed_to_sell(buy_date, as_of_date)
```

`is_at_limit_up()` / `is_at_limit_down()` 对无效价格返回 `False`，不会阻止交易。

## 交易日历

### 数据表

交易日历存储在 `sys_trade_calendar` 表：

| 字段         | 类型         | 说明            |
| ---------- | ---------- | ------------- |
| `market`   | varchar(8) | 市场标识，默认 `SSE` |
| `cal_date` | varchar(8) | 日期 YYYYMMDD   |
| `is_open`  | tinyint    | 0=休市, 1=交易    |

特点：

- 每个自然日一行记录

- 沪深 A 股日历统一用 `market=SSE`

- 数据源为 Tushare `trade_cal`

### CalendarService

```python
from core.modules.data_manager import DataManager

dm = DataManager()
cal = dm.calendar

# 查询交易日
open_dates = cal.load_open_dates("20200101", "20201231")
latest = cal.get_latest_completed_trading_date()
```

### 最近交易日解析顺序

`get_latest_completed_trading_date()` 按优先级解析：

1. `data.json` 配置的 `as_of_latest_completed_trading_date`
2. `sys_trade_calendar` 表查询
3. 实时抓取（新浪 → 东方财富）
4. K 线最大日期回退
5. 系统猜测（排除周末，最多回退 7 天）

### 实时抓取

`real_world_trading_date.py` 依次尝试：

1. 新浪 K 线 provider
2. 东方财富 K 线 provider

### 日历辅助工具

`CalendarOpenDateHelper` 是纯工具类，不依赖 DataManager：

```python
from core.modules.strategy.core.helpers.calendar import CalendarOpenDateHelper

# 判断是否是当月首个交易日
is_first = CalendarOpenDateHelper.is_first_open_of_month(
    "20200102", open_dates
)
# 判断是否是当年最后一个交易日
is_last = CalendarOpenDateHelper.is_last_open_of_year(
    "20201231", open_dates
)
```

## 日历合约

交易日历通过数据合约暴露：

```python
from core.modules.data_contract.contracts import DATA_KEY, ContractIssuer

contract = ContractIssuer.issue(
    DATA_KEY.TRADE_CALENDAR,
    runtime={"start": "20200101", "end": "20201231"},
    fill_in_data=True,
)
calendar = contract.get_data()
# [{"date": "20200102", "is_open": True}, ...]
```

## 回测引擎中的日历

`Timeline` 是回测执行的时间轴。它的构建规则：

1. 如果显式提供 `timeline` 参数，直接使用这些日期点
2. 否则通过 `CalendarService.load_open_dates(window_start, window_end)` 构建
3. 窗口通过 `data.json` 的系统边界校验
4. 系统窗口 = `default_start_date` → `get_latest_completed_trading_date()`

```python
# 回测引擎自动处理日历
BacktestEngine.entity_based.run(
    jobs=jobs,
    start="20240102",
    end="20240103",
    # timeline 不传时，引擎自动从日历构建
)
```

## 与其他模块的关系

| 模块                   | 关系                                 |
| -------------------- | ---------------------------------- |
| **strategy**         | 策略执行前通过市场档案检查涨跌停、最小单位、结算规则         |
| **backtest\_engine** | 通过 CalendarService 构建 Timeline 时间轴 |
| **data\_contract**   | 交易日历作为 global 合约暴露                 |
| **data\_manager**    | CalendarService 提供日历查询服务           |

