---
title: run backtest 运行回测
aliases:
  - cli
  - backtest
  - run
  - simulate
summary: 使用NTQ运行一个策略回测。
---

# 如何运行回测

## 快速开始

```bash
# 完整回测（枚举 → 价格因子 → 组合）
python cli.py s

# 指定策略
python cli.py s --strategy demo/random/random_v1

# 强制重跑（不复用缓存）
python cli.py s -f
```

## 分步执行

NTQ 的回测分四步，可以单独跑：

| 命令                                    | 缩写   | 说明       |
| ------------------------------------- | ---- | -------- |
| `python cli.py strategy_enumerate`    | `se` | 第一步：枚举机会 |
| `python cli.py strategy_price_factor` | `sp` | 第二步：单笔模拟 |
| `python cli.py strategy_portfolio`    | `so` | 第三步：组合模拟 |
| `python cli.py strategy_simulate`     | `s`  | 全部串行     |
| `python cli.py strategy_analyze`      | `sa` | 归因分析     |

### 分步示例

```bash
# 只跑枚举
python cli.py se --strategy demo/random/random_v1

# 只跑价格因子（需要先有枚举结果）
python cli.py sp --strategy demo/random/random_v1

# 只跑组合模拟（需要先有价格因子结果）
python cli.py so --strategy demo/random/random_v1

# 强制重跑某一步
python cli.py sp -f --strategy demo/foo
```

## 全局参数

| 参数                | 说明          |
| ----------------- | ----------- |
| `--strategy NAME` | 指定策略路径或 key |
| `-f`              | 强制刷新/重算/覆盖  |
| `--verbose`       | 详细日志        |

## 执行流程

```
s (simulate)
  ├── se (enumerate)     → 枚举结果 → enum/
  ├── sp (price_factor)  → 单笔模拟 → price/
  ├── so (portfolio)     → 组合模拟 → portfolio/
  └── sa (analyze)       → 归因报告 → analysis/
```

每步产出一个子目录，都在同一个版本目录下：

```
{strategy}/results/simulations/{version_id}/
  enum/        # 第一步产物
  price/       # 第二步产物
  portfolio/   # 第三步产物
  analysis/    # 归因产物
```

## 缓存机制

- 如果指纹没变（settings 白名单 + 股票池 + 环境都一样），直接命中已有版本，秒返回

- `-f` 强制重跑，不复用缓存

- 改了非 effective 字段（如 `meta`、`is_enabled`）不会换版本

## 归因分析

组合模拟完成后，如果 `settings.analysis.enabled = True`，自动生成归因报告：

```bash
# 手动触发归因
python cli.py sa --strategy demo/random/random_v1

# 指定步骤和版本
python cli.py sa --step portfolio --version 3
```

## 输出

每个步骤完成后会在终端输出摘要报告。完整报告保存在版本目录下。查看版本：

```bash
python cli.py v    # 查看版本信息
```

## 常见操作

| 场景              | 命令                                           |
| --------------- | -------------------------------------------- |
| 第一次跑策略          | `python cli.py s --strategy my_strategy`     |
| 改了 settings 后重跑 | `python cli.py s -f --strategy my_strategy`  |
| 只想看有没有机会        | `python cli.py se --strategy my_strategy`    |
| 组合结果没变，只重算归因    | `python cli.py sa --strategy my_strategy`    |
| 删一个版本           | `python cli.py sdv --strategy my_strategy:3` |

