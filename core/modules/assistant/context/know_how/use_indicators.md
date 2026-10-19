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

K 线是 dict 列表。序列在 `records`：

```python
today = records.latest
klines = list(records.series())
```

顶层 `close` 已是前复权。图表和决策者默认只带 **声明过的** 指标。

## 声明之后读哪个字段

| 声明 | 当天 bar 上的字段 |
| --- | --- |
| `"ma": [{"length": 20}]` | `ma20`（`{name}{length}`；参数必须用 `length`，不要用 `window`） |
| `"rsi": [{"length": 14}]` | `rsi14`（`{name}{length}`） |
| `"ma": [{"length": 5, "alias": "fast_ma"}]` | `fast_ma`（有 `alias` 时只认 alias） |
| `"macd": [{"fast": 12, "slow": 26, "signal": 9, "alias": "macd"}]` | 三列：见下表 |

**`alias`（推荐多参数 / 多列指标用）：** 写在该条参数 dict 里，不参与计算。单列落盘名 = `alias`；多列 = `{alias}_{ta列名小写}`。同一 `settings` 里 `alias` 与可预知的默认名（如 `ma20`）不可重复，也不能叫 `close` 等行情字段。

MACD 推荐声明（带 `alias`）：

| 含义 | 字段 |
| --- | --- |
| DIF / MACD 线 | `macd_macd_12_26_9` |
| DEA / 信号线 | `macd_macds_12_26_9` |
| 柱（DIF−DEA） | `macd_macdh_12_26_9` |

不写 `alias` 时多列直接用 ta 列名小写（如 `macdh_12_26_9`）。改了 fast/slow/signal，列名里的数字会变。

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
            "macd": [{"fast": 12, "slow": 26, "signal": 9, "alias": "macd"}],
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

from core.modules.strategy.contracts import Records, StrategyContext, StrategyHooks

MACD_LINE = "macd_macd_12_26_9"
MACD_SIGNAL = "macd_macds_12_26_9"
MACD_HIST = "macd_macdh_12_26_9"


class MacdGoldenCrossStrategy(StrategyHooks):
    def is_opportunity(self, ctx: StrategyContext, records: Records) -> bool:
        klines = records.last(2)
        if len(klines) < 2:
            return False

        prev, curr = klines
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

4. 跑回测：`python cli.py sim --strategy macd_golden_cross`。或导航 **制定策略**。报告在 `{strategy}/results/simulations/{vid}/`，没有 `reports/`。

## RSI 超卖

settings 的 `data.base.indicators`：`{"rsi": [{"length": 14}]}`。钩子：

```python
today = records.latest
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
| 读 `ma_ma20` / 用 `window` | `length` + 读 `ma20`，或设 `alias` 后读 alias |
| 两个指标共用同一 `alias` | 每个实例唯一 `alias` |
| `meta = {}`、`data = {}` 当两个顶层变量 | 只有一个 `settings = { "meta": ..., "data": ... }` |
| `ctx.data("stock.kline.daily")` | `records.series()` / `records.latest` |
| 只改 `meta`，其余删光 | 用模板写全 |
| 把别的 CLI 缩写当回测 | `python cli.py sim --strategy 目录或key` |
| 报告写在 `reports/` | `{strategy}/results/simulations/{vid}/` |
| `-n` 之后仍用 `empty_strategy` | 改 `meta.key` 与目录名一致 |
