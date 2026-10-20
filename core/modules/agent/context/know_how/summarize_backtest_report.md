---
title: summarize backtest report 用模板总结回测报告
aliases:
  - 总结报告
  - 价格报告
  - 回测总结
summary: 价格层回测总结须套 NTQ 报告模板结构；数字只来自工具摘要。
---

# 用模板总结回测报告

完整变量说明见仓库  
`userspace/extensions/assistant/templates/backtest_report_template.md`。  
**禁止照抄该文件末尾示例里的数字**；只能用 `read_execution_report` / `read_attribution_report` 返回的摘要。

## 何时用这套结构

用户要「总结 / 解读 / 讲讲」某策略的**价格回测**（或明确只要价格层）时使用。  
多层层报（枚举+价格+资金）仍可按层分段，但**价格层内部**按下面七块写。

## 输出骨架（Markdown，写在 reply 里）

### 策略回测报告：{display_name}

**{display_name}** 在 **{start}** 至 **{end}** 的回测周期内，共执行了 **{total_investments}** 笔交易，胜率 **{win_rate}%**，平均持仓 **{avg_duration_in_days}** 天。

核心理念：**{description}**（来自 `strategy_meta`；没有就省略这句）。

#### 收益成绩单

年化、交易日年化、均笔 ROI、累计盈利（注意摘要里比率字段多为小数，展示时换成百分数并标明）。  
跟一句体感（高/稳健/偏低/未盈利），勿保证实盘。

#### 交易拆解

盈利笔数 / 亏损笔数、胜率含义（是否靠盈亏比）、持仓风格（按天数粗分超短/短/中短/中/长）。

#### 钱是怎么赚的（或亏的）

用表格给出 `roi_p10 / p25 / p50 / p75 / p90`（若摘要有）。  
解读中位数正负、四分位距（`roi_iqr`）是集中还是两极分化。

#### 收益「地形图」（有 `roi_buckets` 才写）

列出占比较高的几个区间；点出是否堆在深亏区或高盈区。

#### 策略配置快照（有 `settings_snapshot` 才写）

表格：初始资金、最大持仓、止盈/止损、最长持仓、佣金/印花税等。

#### 综合评语（必答三问）

1. **优势**（一个最亮特征）  
2. **风险**（一个最危险信号）  
3. **建议**（值得尝试 / 先优化参数 / 仅作基准对比 等，可执行）

结语必须提醒：**回测 ≠ 实盘**，勿承诺盈利。

## 归因

若用户同时要归因：在价格报告之后另开 `## 归因`，用 `read_attribution_report` 的 conclusion / sensitivity_rank；不要把归因数字写进价格成绩单。
