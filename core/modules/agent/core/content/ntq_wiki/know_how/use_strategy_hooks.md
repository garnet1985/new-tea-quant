---
title: use strategy hooks 策略钩子与载荷工具
aliases:
  - StrategyHooks
  - hooks
  - Records
  - Series
  - CalendarSlice
  - Opportunities
  - is_opportunity
  - 钩子
  - 策略钩子
  - 载荷
summary: 策略钩子签名、ctx 与显式载荷分工；Series / Records / CalendarSlice / Opportunities 上可用的快捷方法。写 strategy.py 时优先读本文。
---

# 策略钩子与载荷工具

写 `strategy.py` 时：**钩子只返回决策结果；当日数据在显式载荷上，不在 `ctx`。**  
指标在 `settings.data.base.indicators` 声明后写在 K 线字段上，见 [用技术指标](use_indicators.md)。新建策略流程见 [编写策略](write_strategy.md)。

导入：

```python
from core.modules.strategy.contracts import (
    CalendarSlice,
    Opportunities,
    Records,
    StrategyContext,
    StrategyHooks,
)
```

实现类挂在模块级（模板已写好），框架按类加载，不要自己 `new` 引擎对象。

---

## 1. 原则（给用户与 AI）

1. **稳定面 vs 当次面**  
   - `ctx`：策略信息、`sample_list`、模式、有效 settings、`ctx.state`（跨日）、`ctx.capture`（本笔归因）。  
   - 当日要操作的对象是钩子**第二个参数**（`records` / `calendar_slice` / `opportunities`）。

2. **不要手建 `Opportunity`**  
   `is_opportunity` 只返回 `True`/`False`；框架用当日 bar 建机会。`select_portfolio_entries` 只返回入参里已有的 `Opportunity` 实例，不返回 id、不返回仓位。

3. **序列统计挂在 `Series`，跨键/持仓挂在 `Records`**  
   横截面与选仓载荷只做轻量导航，不做排序打分引擎。

4. **缺数据返回温和结果**  
   工具在缺字段 / 窗口不足时给 `None` / `False` / `[]`，钩子里自行判断，不要假设字段一定存在。

5. **复权**  
   K 线顶层价字段一般是前复权。goal 钩子里 `position` 同时有 `entry_price`（裸）与 `entry_price_hfq`；`unrealized_pnl_pct` 默认用裸价，要比 hfq 时显式换字段。

---

## 2. 钩子一览

| 钩子 | 必须 | 何时调用 | 返回 |
| --- | -- | --- | --- |
| `to_sample_list(ctx, stock_list)` | 否 | 回测开始前一次（指纹前） | 股票 id 序列；与入参取交后进 `ctx.sample_list` |
| `on_calendar_slice(ctx, calendar_slice)` | 否 | 仅 `slice_based`，每个日历日 | 进入 `is_opportunity` 的 id 列表 |
| `is_opportunity(ctx, records)` | **是** | 每日每股 | `bool` |
| `is_new_opportunity(ctx, *, previous, gap)` | 否 | 仅价格回放 | `bool`（是否开新段） |
| `select_portfolio_entries(ctx, opportunities)` | 否 | 组合入场、机会多于槽位时 | `Sequence[Opportunity]` |
| `is_stop_loss(ctx, records, *, custom, stage)` | 否 | goal 段声明了 `custom` | `bool` |
| `is_take_profit(ctx, records, *, custom, stage)` | 否 | 同上 | `bool` |

未覆盖的可选钩子走框架默认；`select_portfolio_entries` 未覆盖时用 settings 的 `opportunity_selection`，**不会**调用基类空实现。

### `StrategyContext`（每个钩子相同）

| 成员 | 用途 |
| --- | --- |
| `ctx.info` | 策略 key / path 等 |
| `ctx.sample_list` | 本回测股票池（只读视图） |
| `ctx.mode` | `entity_based` / `slice_based` |
| `ctx.base_data_key` | 主数据键，通常 `stock.kline.daily` |
| `ctx.effective_settings` / `effective_settings_dict()` | 有效配置 |
| `ctx.state` | **跨日**可变袋（替代旧 remember） |
| `ctx.capture(key, value)` | **本笔**写入 `signal_snapshot`（归因） |

---

## 3. `Records` — 一只股、当日 as-of

`is_opportunity` / `is_stop_loss` / `is_take_profit` 的主载荷。

### 字段

| 字段 | 内容 |
| --- | --- |
| `entity_id` | 股票 id |
| `entity_info` | 股票元信息（名称、行业等，视装载而定） |
| `items` | `{data_key: [row, …]}`，行为 dict |
| `base_data_key` | 主序列键 |
| `position` | 仅 goal 钩子：见下 |

### 取序列

```python
today = records.latest                 # base 最后一行 dict 或 None
rows = records.last(20)
weekly = records.series("stock.kline.weekly")
finance = list(records.series("stock.finance.quarterly"))
```

base 快捷：`latest` / `first` / `get_by_date` / `index_of` / `last_index_of` / `last(n)` —— 与 `series()` 上同名方法一致。

### Records 自身工具（跨键 / 实体 / 持仓）

| 方法 | 说明 |
| --- | --- |
| `has(data_key)` | 该键非空 |
| `keys()` | 非空 data key 列表 |
| `field(name, data_key="")` | 最新一行数值字段 |
| `info(key, default=None)` | 读 `entity_info` |
| `in_position` | `remaining_ratio > 0` |
| `unrealized_pnl_pct(price_field="close", *, entry_field="entry_price")` | 浮盈比例；无持仓 → `None` |
| `holding_bars()` | 入场日至 as-of 根数（需 `position.entry_date`） |
| `align(other_key, *, as_of=None)` | 把其它键对齐到 base 最新日（精确日，否则最近不晚于） |
| `both_rising(field, key_a="", key_b=...)` | 两路同时上涨 |
| `crossed_on(data_key, field_a, field_b, *, below=False)` | 指定键上的穿越 |

**序列统计不要在 Records 上再找一遍**，用：

```python
s = records.series()           # 或 series("其它键")
s.min_of("close", 20)
s.crossed_above("close", "ma20")
s.find_valleys(order=2)
```

### `position`（goal 钩子）

| 键 | 含义 |
| --- | --- |
| `entry_date` | 入场日 |
| `entry_price` | 裸价入场 |
| `entry_price_hfq` | 复权入场 |
| `basis` | hfq 收益分母 |
| `remaining_ratio` | 剩余仓位比例 |

机会盘点/扫描里的 `Records` 通常**没有** `position`。

---

## 4. `Series` — 一条 data key 的序列

行是 dict；OHLC / 指标都是同行字段（如 `close`、`rsi14`、`ma20`）。

### 取行

`latest` / `first` / `get_by_date` / `index_of` / `last_index_of` / `last(n)` / 下标与迭代。

### 窗口与穿越

| 方法 | 说明 |
| --- | --- |
| `at(field, index=-1)` | 单点数值 |
| `min_of` / `max_of` / `mean_of(field, n)` | 末尾 n 根（跳过非法点） |
| `pct_change(field="close", n=1)` | 相对 n 根前的涨跌幅 |
| `crossed_above` / `crossed_below(a, b, *, lookback=1)` | `b` 可以是字段名或常数 |
| `rising` / `falling(field, n=1)` | 近 n 段同向 |
| `streak(field="close")` | 连续涨为正、跌为负 |

### 波段

| 方法 | 说明 |
| --- | --- |
| `find_peaks(field="high", order=2)` | 严格局部峰 |
| `find_valleys(field="low", order=2)` | 严格局部谷 |
| `swing_points(order=2)` | 峰谷合并、按时间排序 |
| `to_trend(...)` | 相邻摆动点连成 `up`/`down`/`flat` 段 |

返回点形如 `{"index", "date", "value", "kind"}`；趋势段含 `start_index`/`end_index`/`direction` 等。

### K 线结构

| 方法 | 说明 |
| --- | --- |
| `body` / `upper_wick` / `lower_wick` / `true_range` | 单根（可传 `index`） |
| `is_bullish` / `is_bearish` | close vs open |
| `breakout_above(field="high", n=20)` | 最新 close 突破前 n 根高点 |
| `breakdown_below(field="low", n=20)` | 对称 |
| `gap()` | `{kind, pct, delta}`，`kind` 为 `up`/`down`/`none` |
| `retracement(*, from_peak=True, order=2)` | 相对最近一波 swing 的回撤比例 |

实现：`core/modules/strategy/.../hook_params/series_ops.py`；`Series` 上为薄封装。

---

## 5. `CalendarSlice` — 横截面（轻量）

仅 `on_calendar_slice`。日期默认不进 `flags`；需要时用 `as_of`。

| 成员 | 说明 |
| --- | --- |
| `ids()` / `len` / `count` | 当日实体 |
| `has(entity_id)` | 是否在片中 |
| `records_of(entity_id)` | 取该股 `Records` |
| `iter_records()` | 按 id 顺序 yield `Records` |
| `as_of` | 当日日期字符串 |
| `is_period_start` 等 | 月/年开收盘旗标（见类型） |
| `flags` | 可见旗标（**不含** `as_of_date`） |

不要在这里做全市场因子排序；挑 id 或简单规则即可：

```python
def on_calendar_slice(self, ctx, calendar_slice: CalendarSlice) -> list[str]:
    if not calendar_slice.is_first_open_of_month:
        return []
    return calendar_slice.ids()  # 或自行过滤
```

---

## 6. `Opportunities` — 选仓（轻量）

仅 `select_portfolio_entries`。排序/打分优先用 settings 的 `opportunity_selection`；钩子覆盖时自己写逻辑。

| 成员 | 说明 |
| --- | --- |
| 迭代 / `len` / `get(opportunity_id)` / `to_ids()` | 基本集合 |
| `remaining_slots` | 剩余槽位 |
| `held_ids` / `is_held(entity_id)` | 已持有 |
| `entity_id(opp)` / `entities()` | 股票 id |
| `head(n)` | 前 n 个（**到达序，不排序**） |
| `exclude_held()` | 去掉已持仓，保持到达序 |
| `account` | 原始快照 dict |

```python
def select_portfolio_entries(self, ctx, opportunities: Opportunities):
    picked = opportunities.exclude_held()
    return picked[: opportunities.remaining_slots]
```

必须返回 **Opportunity 对象**，不要返回股票 id 字符串。

---

## 7. 常见写法

### RSI 超卖 + 归因

```python
def is_opportunity(self, ctx: StrategyContext, records: Records) -> bool:
    rsi = records.field("rsi14")
    if rsi is None or rsi >= 30:
        return False
    ctx.capture("rsi", rsi)
    ctx.capture("close", records.field("close"))
    return True
```

### 均线金叉（用 Series）

```python
def is_opportunity(self, ctx, records: Records) -> bool:
    s = records.series()
    if not s.crossed_above("ma5", "ma20"):
        return False
    ctx.capture("close", s.at("close"))
    return True
```

### 日线 + 周线共振

```python
def is_opportunity(self, ctx, records: Records) -> bool:
    if not records.has("stock.kline.weekly"):
        return False
    if not records.both_rising("close", key_b="stock.kline.weekly"):
        return False
    weekly = records.align("stock.kline.weekly")
    ctx.capture("weekly_close", None if weekly is None else weekly.get("close"))
    return True
```

### 自定义止盈（持仓浮盈）

```python
def is_take_profit(self, ctx, records, *, custom, stage) -> bool:
    if custom != "pnl_20":
        return False
    pnl = records.unrealized_pnl_pct()  # 默认裸价
    return pnl is not None and pnl >= 0.20
```

---

## 8. 反模式

| 不要 | 要 |
| --- | --- |
| 在 `ctx` 上找当日 K 线 | 用 `records` / `calendar_slice.records_of` |
| 手写 RSI/EMA 循环 | settings 声明指标，读字段 |
| `is_opportunity` 里 `Opportunity(...)` | 只返回 `bool` |
| `select_portfolio_entries` 返回 id 列表 | 返回 `Opportunity` |
| 在 `CalendarSlice`/`Opportunities` 上做复杂打分框架 | 简单滤 + settings 排序，或钩子内手写几行 |
| 把跨日状态塞进 `capture` | 跨日用 `ctx.state`，归因用 `capture` |

---

## 相关

- [编写策略](write_strategy.md) — 模板、settings 骨架  
- [配置策略 settings](config_strategy_settings.md) — 字段说明  
- [用技术指标](use_indicators.md) — 指标字段命名  
- 模块 API：`core/modules/strategy/API.md`（contracts 表）  
- 设计背景：`core/modules/strategy/docs/notes/HOOKS_REDESIGN_0_6_0.md`
