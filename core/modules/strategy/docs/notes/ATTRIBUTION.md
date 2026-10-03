# 归因要答什么

**状态：** 总方向已锁定（2026-10-03）。展示：[ATTRIBUTION_PRESENT.md](./ATTRIBUTION_PRESENT.md)（一层一份；事实 / 结论 / 建议）。自变量 / 因变量 / `attribution.py` 配置：[ATTRIBUTION_INPUTS.md](./ATTRIBUTION_INPUTS.md)。枚举层 [ATTRIBUTION_ENUM.md](./ATTRIBUTION_ENUM.md)；价格层 [ATTRIBUTION_PRICE.md](./ATTRIBUTION_PRICE.md) / 回放 [PRICE_REPLAY.md](./PRICE_REPLAY.md)；组合层 [ATTRIBUTION_PORTFOLIO.md](./ATTRIBUTION_PORTFOLIO.md)。战役展格仍以 [ATTRIBUTION_CAMPAIGN.md](./ATTRIBUTION_CAMPAIGN.md) 为准。

**一句话：** 归因给回测者看「这个结果为什么是这样、下一步改什么」；不是给数据科学家看「哪个特征 SHAP 最大」。

---

## 1. 现在错在哪

战役 `sea` / `spa` / `soa` 在做：对 N 个 version（主号 + 副本）的汇总数字做旋钮减法；价格层（`spa`）还可把各格机会铺平做 XGB+SHAP。

回测者要的是：

- 机会够不够分散（普遍现象还是少数票/少数日子）
- 止损止盈过期合不合理（对哪类票、哪段时期）
- 钱有没有用在刀刃上（机会有没有买到、买到的仓位合不合理）
- 各道门在找机会时有没有干活（关过滤 / 放宽信号各砍或放出多少）

这些数字很多已经在 `{vid}/enum|price|portfolio/overall_report.json` 和枚举明细里，gather 丢掉了。SHAP 还把同一 version 里的止损常数当特征。

原则：

- 先层内诊断，再跨格对照**同一套诊断指标**，最后才是单笔 ML
- 诊断只陈述已发生的；「如果改 X」必须对应 `inputs` 展开后真有的对照格，没有就只给方向、不编百分比
- ML 只回答「已经触发的机会里，现场因子还能否把赚和亏分开」，不能替代发现能力、止损、资金
- 决策模拟（`sd`）不进归因战役；滚动仍走 `sw`，不和参数战役混表
- 不去 N 个战役格子上做回归

---

## 2. 三层回测配什么诊断

| 回测层 | 诊断 | 状态 |
|--------|------|------|
| 枚举 | 机会多不多、两种分散、门有没有干活、目标路径合不合理 | CLI `sea`（须先 `se`） |
| 价格 | 去噪后等权机会账；合并/可交易性有没有偏 | CLI `spa`（须先 `sp`）；Trades/XGB 仅此层 |
| 组合 | 钱有没有买到该买的；买到 vs 漏掉 | CLI `soa`（须先 `so`） |
| 滚动 | 窗口稳不稳 | CLI `sw`；默认每窗到 portfolio |
枚举含重叠、每笔机会独立走完 `goal`。价格按段合并后可并行。组合再受资金与同股持仓约束。三层不要重复报同一个「总收益」。

---

## 3. 统计和机器学习

- 分散、出场原因、利用率、门的有/无：描述统计 + 对照格减法
- 已触发样本里因子还是否排序：先分桶胜率，样本独立后再考虑 SHAP
- 禁止：在幸存者上用 RSI 值 SHAP 解释「贡献了多少机会」；用 SHAP 解释止损常数；随机拆行把同一笔跨 version 副本漏进训练和测试还当预测力

---

## 4. 明确先不做

- 战役 BFF / UI
- 把归因做成第四层回测
- 行业 Top5 / 牛熊 / HHI 作为第一刀成立条件（可后加）
- 无对照格的反事实百分比（「止损收到 -10% 触发率会到 25%」）
- 执行诊断（人 vs 机器）
