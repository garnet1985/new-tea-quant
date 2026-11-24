---
title: NTQ 框架问题快速索引
aliases:
  - framework index
  - 框架索引
  - 去哪找
  - 怎么实现
summary: 常问「NTQ 里某某怎么算 / 在哪实现」时，先查本表再打开对应 wiki。
---

# 框架问题快速索引

给助手与人用的**导航表**：先匹配关键词，再打开 wiki；需要源码时看「核心文件」。  
远端会员通道另有可运营的同名索引（官网可改），本文件是开源框架默认副本。

## 资金层夏普怎么算

- keywords: 夏普, sharpe, Sortino, 怎么算, 如何计算, 如何实现, 夏普比率
- wiki: know_how/how_sharpe_is_calculated.md
- module: modules.strategy · portfolio 资金模拟
- code: core/modules/strategy/core/engines/portfolio/docs/DAILY_MTM_RISK_RATIOS.md; core/modules/strategy/core/engines/portfolio/report_manager/capital_metrics.py; core/modules/strategy/core/engines/portfolio/simulator.py
- note: 日频盯市；无风险=隔夜 SHIBOR；×√252；整户而非单笔机会

## 怎么读回测报告

- keywords: 读报告, 回测报告, 怎么看, 夏普怎么读, Calmar
- wiki: know_how/read_backtest_report.md
- module: modules.strategy · 各层报告
- code: core/modules/agent/core/content/templates/backtest_portfolio.md
- note: 「怎么读」看报告 wiki；「怎么算」看资金层夏普专文

## 组合模拟是什么

- keywords: 组合模拟, 投资模拟, portfolio, 第三步, 净值
- wiki: wiki/strategy/strategy_portfolio.md
- module: modules.strategy · portfolio
- code: core/modules/strategy/core/engines/portfolio/simulator.py
- note: 第三步账户层；夏普在资金报告

## 策略钩子怎么写

- keywords: 钩子, hooks, is_opportunity, strategy hooks
- wiki: know_how/use_strategy_hooks.md
- module: modules.strategy · userspace hooks
- code: core/modules/agent/core/content/ntq_wiki/know_how/use_strategy_hooks.md
- note: 买卖信号与机会定义

## 策略 settings 怎么配

- keywords: settings, 止盈止损, goal, stages, 配置
- wiki: know_how/config_strategy_settings.md
- module: modules.strategy · settings
- code: core/modules/agent/core/content/ntq_wiki/wiki/goal_management.md
- note: 配置字段与 goal 纪律
