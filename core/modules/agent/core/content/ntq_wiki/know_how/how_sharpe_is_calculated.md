---
title: NTQ 资金层夏普怎么算
aliases:
  - sharpe
  - 夏普
  - 夏普比率
  - Sortino
  - 怎么算夏普
  - 如何计算夏普
summary: 投资模拟（资金层）夏普 / Sortino 的口径：日频盯市净值、隔夜 SHIBOR、年化 √252。
---

# 资金层夏普 / Sortino 怎么算

问「NTQ 里夏普是怎么算的 / 如何实现」时，指的是**投资模拟（组合 / 资金层）报告**里的夏普，不是机会盘点或价格回测里的单笔指标。

## 一句话

每个交易日把账户按市价盯市 → 算日收益率 → 减去无风险 → 均值 / 样本标准差 → 再乘 √252 年化。

## 公式（夏普）

```text
夏普 = mean(r − rf) / sample_std(r − rf) × √252
```

- `r`：日频盯市后的账户日收益  
- `rf`：无风险日利率，来自**隔夜 SHIBOR**（`one_night`），按年化百分数折成日利率  
- 样本标准差；交易日少于 2 或波动≈0 时报告显示为「—」

Sortino 同理：分子仍是超额收益均值，分母用下行波动；上涨日贡献 0，分母按全部交易日段数。

## 关键口径（避免误解）

- 夏普属于**整份账户**，不是单笔机会、也不是价格层单笔 ROI。  
- 净值曲线是**每个开市日盯市**，不是只在成交换日记点再硬乘 √252（旧口径已废弃）。  
- 盯市用成交后的持仓 + 持仓期内后复权收盘；现金利息**不**加回净值，只进夏普/Sortino 的无风险扣减。  
- Calmar 仍是区间总收益 / 最大回撤（同一条盯市曲线），不是年化 Calmar。

## 出现在哪一步

回测第三步「投资模拟 / 组合模拟」的资金报告。先有成交回放，再在写报告前做盯市与风险比计算。

## 快捷落点

| 类型 | 位置 |
|------|------|
| 产品说明 | 本文；组合概念见 [组合模拟](../wiki/strategy/strategy_portfolio.md) |
| 模块 | `modules.strategy` · portfolio 资金模拟 |
| 算法说明（开发） | `core/modules/strategy/core/engines/portfolio/docs/DAILY_MTM_RISK_RATIOS.md` |
| 核心计算 | `core/modules/strategy/core/engines/portfolio/report_manager/capital_metrics.py` |
| 模拟器 | `core/modules/strategy/core/engines/portfolio/simulator.py`（成交回放；盯市在报告阶段） |

## 自己怎么核对

1. 跑完投资模拟，打开资金报告看夏普字段。  
2. 需要公式细节时读上表「算法说明」文档。  
3. 不要用机会盘点或价格层数字去「拼」出一个账户夏普。
