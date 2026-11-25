# 呈现模板 · backtest_enum

**scenario：** `backtest_enum` — 本轮读过机会盘点报告，且用户要总结 / 解读时使用。  
数字只能来自 work 结论；禁止编造。

## 输出骨架

## 机会盘点

一句话总评：这段时间里，策略大概多久出现一次机会、覆盖面宽不宽。

```metrics
机会总数 | {total_opportunities}
涉及股票 | {trigger_stocks} / {total_stocks}
触发比例 | {trigger_ratio}%
```

再用两三句白话说明：机会是稀还是密、是否集中在少数股票（有才写）。不要写字段名。

> 结论：{一句话}。
