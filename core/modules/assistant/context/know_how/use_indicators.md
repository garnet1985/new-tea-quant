---
title: use indicators 用技术指标
aliases:
  - Indicator
  - MACD
  - macd
  - RSI
  - rsi
  - 金叉
  - 金叉策略
  - 死叉
  - 指标
  - 均线
  - 布林
  - golden cross
summary: 指标在 settings.data.base.indicators 声明，框架写入 K 线；钩子只读字段。MACD 金叉完整例子。不要手写 EMA。
---

# 如何用技术指标

正路：**在 `settings.py` 的 `data.base.indicators` 里声明**，枚举/扫描时框架算好写回每根 K 线。钩子只读字段，不要手写 EMA，不要对 dict 列表做减法。

K 线是 dict 列表。`ctx.data` **不是函数**：

```python
data = ctx.data.items_with_meta()
klines = data.get(ctx.base_data_key) or []
today = ctx.record_of_today
```

顶层 `close` 已是前复权，不要写 `params.adjust`。图表和决策者默认只带 **声明过的** 指标。

## 声明之后读哪个字段

| 声明 | 当天 bar 上的字段 |
| --- | --- |
| `"rsi": [{"length": 14}]` | `rsi14`（`{name}{length}`） |
| `"macd": [{"fast": 12, "slow": 26, "signal": 9}]` | 三列，名字长：见下表 |

MACD 默认参数注入后的键（必须抄对）：

| 含义 | 字段 |
| --- | --- |
| DIF / MACD 线 | `macd_macd_12_26_9_fast12_signal9_slow26` |
| DEA / 信号线 | `macd_macds_12_26_9_fast12_signal9_slow26` |
| 柱（DIF−DEA） | `macd_macdh_12_26_9_fast12_signal9_slow26` |

改了 fast/slow/signal，键里的数字会变。布林带同类，演示策略用辅助函数拼字段名。

钩子里再调 `Indicator.macd(klines)` 也能算，但图表不画未声明的指标。需要临时试算时：`from core.modules.indicator import Indicator`。

## MACD 金叉（可复制）

金叉：柱从 ≤ 0 上穿到 > 0（等价于 DIF 从下穿过 DEA）。

1. `python cli.py -n macd_golden_cross`，立刻把 `meta.key` 改成 `macd_golden_cross`（模板仍是 `empty_strategy`）。

2. **同一份** `settings.py` 里改 `settings` 这一个字典（不要另起 `meta = {}` / `data = {}`）。`data` 块写成：

```python
"data": {
    "base": {
        "data_key": "stock.kline.daily",
        "params": {},
        "indicators": {
            "macd": [{"fast": 12, "slow": 26, "signal": 9}],
        },
    },
    "min_required_records": 60,
    "required": [],
},
```

模板里的 `goal` / `simulation` / `portfolio` / `fees` 留着。

3. `strategy.py`：

```python
from __future__ import annotations

from core.modules.strategy.contracts import StrategyContext, StrategyHooks

MACD_LINE = "macd_macd_12_26_9_fast12_signal9_slow26"
MACD_SIGNAL = "macd_macds_12_26_9_fast12_signal9_slow26"
MACD_HIST = "macd_macdh_12_26_9_fast12_signal9_slow26"


class MacdGoldenCrossStrategy(StrategyHooks):
    def has_opportunity(self, ctx: StrategyContext) -> bool:
        data = ctx.data.items_with_meta()
        klines = data.get(ctx.base_data_key) or []
        if len(klines) < 2:
            return False

        prev, curr = klines[-2], klines[-1]
        prev_hist, curr_hist = prev.get(MACD_HIST), curr.get(MACD_HIST)
        if None in (prev_hist, curr_hist):
            return False
        if not (prev_hist <= 0 and curr_hist > 0):
            return False

        ctx.capture("macd", curr.get(MACD_LINE))
        ctx.capture("signal", curr.get(MACD_SIGNAL))
        ctx.capture("hist", curr_hist)
        ctx.capture("close", curr.get("close"))
        return True
```

4. 跑回测：`python cli.py s --strategy macd_golden_cross`（**不是** `spn`）。或导航 **制定策略**。报告在 `{strategy}/results/simulations/{vid}/`，没有 `reports/`。

## RSI 超卖

settings 的 `data.base.indicators`：`{"rsi": [{"length": 14}]}`。钩子：

```python
today = ctx.record_of_today
if today is None:
    return False
rsi = today.get("rsi14")
if rsi is None:
    return False
ctx.capture("rsi", rsi)
return rsi < 30
```

## 常见翻车

| 错法 | 对法 |
| --- | --- |
| 钩子里手写 EMA / `Indicator.macd`，settings 不声明 | `data.base.indicators` 声明，钩子读 K 线字段 |
| `meta = {}`、`data = {}` 当两个顶层变量 | 只有一个 `settings = { "meta": ..., "data": ... }` |
| `ctx.data("stock.kline.daily")` | `ctx.data.items_with_meta()` |
| `params: {"adjust": "qfq"}` | 删掉 |
| 只改 `meta`，其余删光 | 用模板写全 |
| `python cli.py spn` 当回测 | `python cli.py s --strategy 目录或key` |
| 报告写在 `reports/` | `{strategy}/results/simulations/{vid}/` |
| `-n` 之后仍用 `empty_strategy` | 改 `meta.key` 与目录名一致 |
