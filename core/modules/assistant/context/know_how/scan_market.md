---
title: scan market 扫描市场中的机会
aliases:
  - scan
  - real time
  - market
  - cli
  - 扫描
  - 策略选股
  - 扫描选股
summary: 用界面「策略选股」或 CLI 扫描当天机会；后处理适配器用 scanner.adapters。
---

# 如何扫描实时行情

## 什么是扫描

扫描（Scan）用当前市场数据运行策略的 `has_opportunity` 钩子，找出今天有哪些交易机会。和回测不同，扫描只跑枚举这一步，不做后续的价格因子和组合模拟。

界面入口：导航 **策略选股**。扫描使用策略目录里当前的 `settings.py`，没有单独的发布步骤。要扫「真」市场，数据得够新（需自接数据源）。只想看演示：选「扫描演示」模式，应用会把「今天」当成本地数据最晚交易日的下一天。

## 基本用法

```bash
# 扫描所有已启用策略
python cli.py c

# 指定策略
python cli.py c --strategy random_v1

# demo 模式（放宽严格交易日门闸）
python cli.py c --demo
```

## 输出

扫描完成后在终端输出每个策略的摘要：

```
  [random_v1] date=20260918 opportunities=5 universe=300 hit_stocks=5 at_limit_up=1
         日期模式=latest_completed；来源=trade_calendar
```

| 输出字段            | 说明             |
| --------------- | -------------- |
| `date`          | 扫描日期           |
| `opportunities` | 发现的机会总数        |
| `universe`      | 股票池总数          |
| `hit_stocks`    | 命中的股票数         |
| `at_limit_up`   | 涨停时触发的数量（不可交易） |

## 适配器后处理

如果策略配置了 `scanner.adapters`，扫描完成后会调用适配器做后处理：

```python
# settings.py
"scanner": {
    "adapters": "industry_report",
}
```

详见 [如何编写适配器](write_adapter.md)。

## 严格交易日门闸

默认情况下，扫描使用**严格上一交易日**逻辑——确保扫描日期是一个真实的交易日。

`--demo` 参数放宽这个门闸：

- 关闭严格交易日检查

- 跳过锚点 vs K 线对齐验证

- 适合开发调试时使用

## scanner 配置

```python
"scanner": {
    "adapters": ["console"],              # 后处理适配器
    "use_strict_previous_trading_day": True,  # 严格交易日
    "max_cache_days": 10,                 # 缓存天数
    "watch_list": "",                     # 观察列表
}
```

## 与回测的区别

| 维度 | 扫描（Scan）            | 回测（Simulate） |
| -- | ------------------- | ------------ |
| 时间 | 当天实时                | 历史时间窗口       |
| 步骤 | 只跑枚举                | 价格因子+组合（决策者另跑） |
| 输出 | 机会列表                | 完整回测报告       |
| 缓存 | `max_cache_days` 控制 | 版本指纹缓存       |
| 数据 | 最新行情                | 历史 K 线       |

## 扫描缓存

扫描结果会缓存 `max_cache_days` 天。重复扫描且日期没变时可能直接返回缓存。当前 CLI **没有**把 `-f` 传给扫描，不要用 `cli.py c -f` 指望强制刷新。

## 多策略扫描

不指定 `--strategy` 时扫描所有已启用策略（`is_enabled: True`）：

```bash
python cli.py c
```

每个策略独立输出摘要。即使策略未启用，显式指定 `--strategy` 时也会扫描。

## 常见操作

| 场景         | 命令                                       |
| ---------- | ---------------------------------------- |
| 每日扫描所有策略   | `python cli.py c`                        |
| 只扫描某个策略    | `python cli.py c --strategy my_strategy` |
| 强制刷新缓存     | 当前扫描 CLI 不支持 `-f`                 |
| 调试模式（放宽门闸） | `python cli.py c --demo`                 |

