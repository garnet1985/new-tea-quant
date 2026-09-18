---
title: run backtest 运行回测
aliases:
  - cli
  - backtest
  - run
  - simulate
  - 回测
  - 运行回测
summary: 用 CLI 跑枚举、价格因子、组合模拟（决策者是另一步）。
---

# 如何运行回测

## 快速开始

```bash
# 完整模拟链路：价格因子 → 组合（没有枚举结果时会先补跑枚举）
python cli.py s

# 指定策略（用 meta.key，或磁盘相对路径）
python cli.py s --strategy random_v1

# 忽略缓存，写入同一 version 目录
python cli.py s -f
```

`s` 才是跑回测。`spn` 只固定已有 version。报告在 `{strategy}/results/simulations/`，没有 `reports/`。

概念上的四步见 [回测四步流程](../wiki/strategy/backtest_pipeline.md)。CLI `s` **不包含**决策者（`sd`）和单独的归因命令（`sa`）。

## 分步执行

| 命令                                    | 缩写   | 说明 |
| ------------------------------------- | ---- | -------- |
| `python cli.py strategy_enumerate`    | `se` | 第一步：枚举机会 |
| `python cli.py strategy_price_factor` | `sp` | 第二步：单笔模拟 |
| `python cli.py strategy_portfolio`    | `so` | 第三步：组合模拟 |
| `python cli.py strategy_simulate`     | `s`  | 价格因子 → 组合（缺枚举则先 se） |
| `python cli.py strategy_analyze`      | `sa` | 归因分析（独立命令） |
| `python cli.py strategy_decision`     | `sd` | 第四步：决策者回放 |

### 分步示例

```bash
python cli.py se --strategy random_v1
python cli.py sp --strategy random_v1
python cli.py so --strategy random_v1
python cli.py sp -f --strategy random_v1
```

## 全局参数

| 参数                | 说明 |
| ----------------- | ----------- |
| `--strategy NAME` | 策略 `meta.key` 或相对 `userspace/strategies/` 的路径 |
| `-f`              | 忽略缓存；同指纹仍写入原 version，不是新开一个 |
| `--verbose`       | 详细日志        |

## 执行流程

```
s (simulate)
  ├── 若缺枚举 → se (enumerate)  → enum/
  ├── sp (price_factor)         → price/
  └── so (portfolio)            → portfolio/
        └── analysis.enabled 时顺带写 analysis/
sa 是单独命令，不是 s 的子步骤。
sd 是决策者，基于已有枚举版本交互回放。
```

产物在同一个版本目录下（**没有** `reports/`）：

```
{strategy}/results/simulations/{version_id}/
  enum/
  price/
  portfolio/
  analysis/
```

## 缓存机制

- 指纹没变（settings 白名单 + 股票池 + 环境一样）会命中已有版本

- `-f` 强制重算，但仍落在同一 version

- 只改 `meta`、`is_enabled` 等非 effective 字段不会换版本

## 归因分析

组合完成后，若 `settings.analysis.enabled = True`，该次组合会带归因产物。也可事后单独跑：

```bash
python cli.py sa --strategy random_v1
python cli.py sa --step portfolio --version 3
```

## 输出

每步结束后终端有摘要，完整报告在版本目录。策略回测 version **没有**列表 CLI；`python cli.py v` 只打印 NTQ 核心版本。目录在 `{strategy}/results/simulations/`，日常在制定策略工作台看图。各步看哪些表见 [如何读回测报告](read_backtest_report.md)。

## 常见操作

| 场景              | 命令 |
| --------------- | -------------------------------------------- |
| 第一次跑策略          | `python cli.py s --strategy my_strategy`     |
| 改了 settings 后重跑 | `python cli.py s -f --strategy my_strategy`  |
| 只想看有没有机会        | `python cli.py se --strategy my_strategy`    |
| 组合结果没变，只重算归因    | `python cli.py sa --strategy my_strategy`    |
| 删一个版本           | `python cli.py sdv --strategy my_strategy:3` |
| 固定一个已有 version | `python cli.py spn --strategy my_strategy:3`（不是跑回测） |

MACD / RSI 怎么写再怎么跑，见 [用技术指标](use_indicators.md)。新建策略见 [编写策略](write_strategy.md)。
