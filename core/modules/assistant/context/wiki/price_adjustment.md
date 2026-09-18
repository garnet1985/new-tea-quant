---
title: 价格复权机制
aliases:
  - price adjustment
  - qfq
  - hfq
  - kline
  - roi
  - 复权
  - 前复权
  - 后复权
summary: 信号用前复权，收益率用后复权，成交记录用裸价。
---

# 价格复权

分红、送股后股价会跳变。不做复权，回测收益率会被假的大跌大涨污染。

NTQ 三层价格同时出现在每根 K 线上：

| 层 | 字段 | 用途 |
| --- | --- | --- |
| 前复权 qfq | 顶层 `open/close/high/low/pre_close` | 信号、扫描、均线 |
| 后复权 hfq | `hfq.open/close/...` | ROI、比例止盈止损 |
| 裸价 raw | `raw.open/close/...` | 份额、扣现金、成交记录 |

```python
{
    "date": "20200102",
    "open": 10.5,          # qfq
    "close": 10.8,
    "raw": {"open": 12.0, "close": 12.3, ...},
    "hfq": {"open": 9.6, "close": 9.8, ...},
    "adj_factor": 0.8,
}
```

## 口径

| 规则 | 说明 |
| --- | --- |
| ROI 用后复权 | `(卖出后复权 - 买入后复权) / 买入后复权` |
| 现金盈亏用裸价 | 成交金额按 raw，不要用前复权去除 |
| 前复权不算收益率 | 可能为负，破坏比例 |
| 裸价不算 ROI | 除权跳变是假收益 |

策略钩子里 `ctx.data.items_with_meta()` 拿到的 K 线，顶层 OHLC 默认是前复权。不要写 `params.adjust`。价格因子引擎会自己选对层，通常不必手算 ROI。

## 因子从哪来

复权因子在 `sys_adj_factor_events`：每只股票一条按日期排序的事件链。某日生效事件 = `event_date <= 该日` 的最近一条。没有事件时用裸价。

前复权用全局偏移，把历史接到最新价附近；后复权是 `裸价 × 当日因子`，查询时现算，不落库。
