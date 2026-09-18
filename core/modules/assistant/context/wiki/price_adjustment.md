---
title: 价格复权机制
aliases:
  - price adjustment
  - qfq
  - hfq
  - kline
  - roi
summary: NTQ中的价格复权机制和使用场景。
---

# 价格复权机制

## 为什么需要复权

股票发生分红、送股、转增等公司行为后，股价会不连续跳变。如果不做复权处理，回测中的收益率计算会被虚假的大跌或大涨污染。

NTQ 采用**前复权（qfq）为主、后复权（hfq）为辅**的双轨制，并在不同场景使用不同价格层。

## 三层价格

K 线加载后，每根 K 线包含三层价格：

| 层            | 字段                                    | 计算方式                     | 用途             |
| ------------ | ------------------------------------- | ------------------------ | -------------- |
| **qfq（前复权）** | `open/close/high/low/pre_close`（顶层字段） | `raw × F(段) / F(最新) + C` | 信号、扫描、均线、形态识别  |
| **hfq（后复权）** | `hfq.open/close/high/low/pre_close`   | `raw × F(t)`             | ROI、比例止盈止损、PnL |
| **raw（原始）**  | `raw.open/close/high/low/pre_close`   | 原始价格                     | 份额计算、现金扣除、买入逻辑 |

```python
# 一根 K 线的数据结构
{
    "date": "20200102",
    "open": 10.5,       # qfq
    "close": 10.8,      # qfq
    "high": 11.0,       # qfq
    "low": 10.3,        # qfq
    "pre_close": 10.2,   # qfq
    "raw": {
        "open": 12.0,
        "close": 12.3,
        "high": 12.5,
        "low": 11.8,
        "pre_close": 11.7,
    },
    "hfq": {
        "open": 9.6,
        "close": 9.8,
        "high": 10.0,
        "low": 9.4,
        "pre_close": 9.3,
    },
    "adj_factor": 0.8,  # 该日有效复权因子
}
```

## 复权因子事件链

复权因子存储在 `sys_adj_factor_events` 表中：

| 字段            | 类型            | 说明            |
| ------------- | ------------- | ------------- |
| `id`          | varchar       | 股票代码          |
| `event_date`  | varchar(8)    | 事件日期 YYYYMMDD |
| `factor`      | decimal(12,4) | 绝对复权因子 F(t)   |
| `qfq_anchor`  | decimal       | 事件日前复权收盘价快照   |
| `raw_anchor`  | decimal       | 事件日原始收盘价快照    |
| `qfq_diff`    | decimal       | 可选的差值缓存（回退用）  |
| `last_update` | varchar       | 用于续期增量更新      |

每只股票维护一条事件链，按 `event_date` 排序。

### 有效事件解析

`load_effective_events_for_dates()` 为每个日期确定生效的复权事件：

- 选择 `event_date <= 目标日期` 的最近事件

- `strict=True`：无历史事件则不复权（返回原始价格）

- `strict=False`：无历史事件但存在最早事件时，推断起始事件（`is_inferred=True`）

- 无任何事件可选时 `is_adjusted=False`，使用原始价格

## 前复权公式

采用"全局偏移法"：

```
C = qfq_anchor_latest - raw_anchor_latest × F_latest / F(latest)

qfq(t) = raw(t) × F(段) / F(最新) + C
```

其中：

- `raw(t)` 是原始 OHLC

- `F(段)` 是该日生效事件的复权因子

- `F(最新)` 是事件链中最新事件的复权因子

- `C` 是从最新事件的锚点推导的全局偏移量

当最新事件缺少锚点数据时，系统会记录警告并回退到 `qfq_diff` 差值。

## 后复权公式

```
hfq(t) = raw(t) × F(t)
```

后复权不持久化，在查询时实时计算。

## 关键约束

| 规则                   | 说明                                     |
| -------------------- | -------------------------------------- |
| **ROI 必须用 hfq**      | `ROI = (sell_hfq - buy_hfq) / buy_hfq` |
| **PnL 用 raw × ROI**  | `PnL = shares × buy_raw × ROI`         |
| **qfq 不可用于收益率**      | 前复权可能产生负值，破坏比例计算                       |
| **raw 不可用于 ROI**     | 分权事件会导致虚假跳变                            |
| **买入用 raw + 份额**     | 现金扣除基于原始价格                             |
| **HfqRoi 是唯一收益率计算类** | 封装了 hfq 比例运算，禁止绕过                      |

### HfqRoi

```python
from core.modules.strategy.core.engines.shared.services.hfq_roi import HfqRoi

# 计算收益率
roi = HfqRoi.calculate(buy_hfq, sell_hfq)  # (sell - buy) / buy

# 计算盈亏
pnl = HfqRoi.pnl(buy_raw, sell_hfq, shares)

# 测算目标价
target = HfqRoi.target_price(buy_hfq, target_roi)
```

## 加载接口

`KlineService` 提供多种加载方式：

| 方法                         | 说明               |
| -------------------------- | ---------------- |
| `load_raw()`               | 原始 K 线，不复权       |
| `load_qfq()`               | 前复权 K 线（默认路径）    |
| `load_qfq_split()`         | 前复权，按实体拆分返回      |
| `load_qfq_strict()`        | 严格前复权，只用历史事件，不推断 |
| `load_batch()`             | 批量加载多只股票的前复权 K 线 |
| `load_adj_factor_events()` | 只加载复权因子事件        |

`adjust` 参数在当前版本中被忽略，保留仅为向后兼容。

## 与策略的关系

策略钩子中通过 `ctx.data("stock.kline.daily")` 获取的 K 线数据默认是前复权。三层价格都在每根 K 线中可用：

```python
def has_opportunity(self, ctx: StrategyContext) -> bool:
    klines = ctx.data("stock.kline.daily")
    if not klines:
        return False

    # 用 qfq 做信号判断
    close = [bar["close"] for bar in klines]
    ma5 = sum(close[-5:]) / 5

    return close[-1] > ma5

# ROI 在 price_factor 阶段自动用 hfq 计算
# raw 用于份额和现金计算
```

策略开发者无需手动选择复权方式——框架在 price\_factor 引擎中自动使用正确的价格层。
