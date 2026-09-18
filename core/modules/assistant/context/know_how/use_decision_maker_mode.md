---
title: use decision maker mode 使用决策者模拟
aliases:
  - decision maker
  - interactive
  - replay
  - cli
summary: 使用NTQ在回测中使用决策者模拟。
---

# 如何使用决策者模式

## 什么是决策者模式

决策者模式让你在枚举产出的机会基础上，逐日推进，自己决定"选谁"和"买多少"，走完后和程序化组合对比。

简单说：**把你的判断替代代码的判断，看看人和策略谁做得更好。**

## 前提条件

- 已经完成枚举（`se`）和组合模拟（`so`），决策者基于已有版本回放

- 策略的 `goal`、`fees`、`portfolio` 设置在决策者模式中不可更改

## 启动会话

```bash
# 默认进入当前 settings.py 命中的 version
# 未完成 0 局 → 新开一局
# 未完成 1 局 → 续上
# 未完成 ≥2 局 → 列出让你选
python cli.py sd

# 指定策略
python cli.py sd --strategy demo/random/random_v1

# 指定旧版本
python cli.py sd --version 3

# 新开一局（不论是否有未完成局）
python cli.py sd --new-session

# 续指定旧局
python cli.py sd --session 1
```

## 会话管理

| 命令                                       | 缩写    | 说明         |
| ---------------------------------------- | ----- | ---------- |
| `python cli.py strategy_decision`        | `sd`  | 开始/继续决策者会话 |
| `python cli.py strategy_decision_list`   | `sdl` | 列出所有会话     |
| `python cli.py strategy_decision_delete` | `sdd` | 删除一个会话     |

### 列出会话

```bash
python cli.py sdl --strategy demo/random/random_v1
python cli.py sdl --version 3
```

### 删除会话

```bash
python cli.py sdd --session 1
python cli.py sdd --session 2 --version 3
```

## 会话磁盘布局

```
{strategy}/results/simulations/{vid}/
  enum/          # 枚举结果（只读）
  price/         # 价格因子结果（只读）
  portfolio/     # 组合模拟结果（只读）
  decision/
    meta.json
    {dm_id}/
      session.json    # 会话状态（支持断点恢复）
```

## 交互流程

进入决策者 REPL 后：

1. **时间推进**：时钟在有 event 的日子暂停

   - 新机会出现

   - 持仓目标成交（卖出）

2. **你的决策**：

   - 从当日所有机会中选哪些进入组合

   - 决定每只投入多少股数（按市场手数步进）

3. **纪律自动执行**：你买入后，止盈止损过期由框架按 `goal` 配置自动执行，你不能干预

## 你能做什么

- **选谁**：从当日机会列表中选择

- **买多少**：决定股数（按最小手数步进）

## 你不能做什么

- 改变策略的止盈止损配置

- 中途手动卖出

- 加仓

- 打破资金分配规则（现金、持仓上限）

## 对比报告

走完后产出和组合层同结构的报告，然后对比：

| 指标   | 你 vs 策略         |
| ---- | --------------- |
| 胜率   | 你 60% vs 策略 55% |
| ROI  | 你 12% vs 策略 8%  |
| 持仓时长 | 你 15天 vs 策略 20天 |

## 断点恢复

会话支持断点恢复——中断后下次 `sd` 可以继续。系统自动保存会话状态到 `session.json`。

## 设计边界

- 决策者模式**不进指纹缓存**——它是交互式回放，不是 `SimulateKind`

- 复用组合层的成交规则（费用、手数、流动性、组合上限）

- 持仓时长按交易日计算（不是自然日）

