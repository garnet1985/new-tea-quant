# 呈现模板 · backtest_portfolio

**scenario：** `backtest_portfolio` — 本轮读过资金模拟报告，且用户要总结 / 解读时使用。  
数字只能来自 work 结论；禁止编造。

## 输出骨架

## 资金模拟

一句话总评：在给定本金与持仓限制下，组合整体是赚是亏、波动大不大。

```metrics
总收益 | {total_return}% | {体感}
最大回撤 | {max_drawdown}%
胜率 | {win_rate}%
夏普 | {sharpe_ratio}
```

补充白话（有才写）：同时持仓是否经常顶满、资金利用是否紧张、和单笔价格回测是否差很多。

> 结论：{一句话}。这是带本金约束的模拟，不是实盘。
