---
title: NTQ 回测四步流程
aliases:
  - backtest
  - pipeline
  - overview
  - four-steps
summary: NTQ 回测四步流程介绍
---

# 回测四步流程

NTQ 的核心设计：回测拆成四步，每步独立产出报告。三步串行执行（枚举 → 价格因子 → 组合），第四步是交互式回放（决策者）。

## 流程总览

```
第一步：枚举（Enumerate）
  输入：策略钩子 has_opportunity + 历史数据
  输出：每个交易日每只股票是否有机会（JSON 契约）
  报告：机会概览、分布、节奏分散度、可交易性

第二步：价格因子（Price Factor）
  输入：枚举结果 + 入场/出场假设
  输出：每笔交易的单笔盈亏
  报告：胜率、盈亏比、持仓周期、ROI 分布

第三步：组合模拟（Portfolio）
  输入：价格因子结果 + 资金管理 + 止盈止损
  输出：组合层面的净值曲线和回撤
  报告：账户总览、胜率盈亏、回撤、净值曲线、Sharpe/Sortino

第四步：决策者模式（Decision Maker）
  输入：枚举结果 + 用户手动抉择
  输出：用户作为决策者的组合表现
  报告：与程序化组合的对比报告
```

## 引擎关系

前三步都经过 `BacktestEngine` 调度（多进程/多线程），但引擎不认识策略、股票这些概念——它只管"给我一批 job，我并行跑完告诉你结果"。

- 第一步和第二步：经 BacktestEngine 的 `RunCallbacks` 挂入回测

- 第三步：不走 BacktestEngine，在主进程内完成（不需要多进程，因为已经是组合层面的模拟）

- 第四步：交互式回放，也不是 BacktestEngine 调度

## 数据流

```
枚举结果（JSON 契约）
    ↓ 价格因子引擎消费
价格因子报告 + 逐股 investments
    ↓ 组合引擎消费
组合报告 + 净值曲线 + 逐笔成交
    ↓ 归因分析（可选）
归因报告（facts + insights）
```

枚举结果是**契约**——后续三个引擎（价格因子、组合、决策者）都消费同一份枚举结果，不重复计算。

## 版本系统

一次完整回测 = 一个 version。三步共享同一个 version id。版本绑定指纹：

- 改了 settings 白名单字段 → execute\_fp 变 → 新 version

- 环境变了（NTQ 升级、hooks 源码改了）→ env\_fp 变 → 旧 version 变为"仅供查阅"

- 只改非 effective 字段（如 meta、is\_enabled）→ 不换 version

## CLI 对应

| 步骤     | 命令                             | 缩写   |
| ------ | ------------------------------ | ---- |
| 第一步    | `cli.py strategy_enumerate`    | `se` |
| 第二步    | `cli.py strategy_price_factor` | `sp` |
| 第三步    | `cli.py strategy_portfolio`    | `so` |
| 第四步    | `cli.py strategy_decision`     | `sd` |
| 全部串行   | `cli.py strategy_simulate`     | `s`  |
| 扫描实时行情 | `cli.py scan`                  | `c`  |
| 归因分析   | `cli.py strategy_analyze`      | `sa` |

## 执行模式

枚举和价格因子有两种执行模式：

| 模式             | 逻辑               | 适用         |
| -------------- | ---------------- | ---------- |
| `slice_based`  | 按时间切片，每片处理全部股票   | 多股票、中等时间窗口 |
| `entity_based` | 按股票分组，每组独立跑完整时间线 | 少股票、长时间窗口  |

组合模拟不需要选模式，它在主进程内完成。

## 磁盘布局

```
{strategy}/results/simulations/
  meta.json                    # 索引：next_version_id + registry + pinned
  {vid}/
    settings.json              # 当时完整 settings（恢复用）
    effective_settings.json    # 白名单投影
    scope.json                 # { entity_ids, start_date, end_date }
    enum/                      # 第一步产物
    price/                     # 第二步产物
    portfolio/                 # 第三步产物
    analysis/                  # 归因产物（与该步同生共死）
    decision/{dm_id}/           # 第四步会话
```

