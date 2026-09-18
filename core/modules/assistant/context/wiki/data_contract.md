---
title: 数据契约
aliases:
  - data contract
  - datakey
  - 数据契约
  - 数据合约
  - 数据键
summary: 用数据键声明依赖；策略里 ctx.data.items 走契约而不是直接查库。
---

# 数据契约

数据契约说明「有哪些数据、长什么样、怎么按需加载」。策略不要直接查库，用数据键声明依赖，运行时用 `ctx.data.items_with_meta()` 按键取数（`ctx.data` 不是函数）。

| 概念 | 含义 |
| --- | --- |
| 数据键 | 字符串标识，如 `stock.kline.daily` |
| 声明 | 这个键的类型、范围、加载方式 |
| 签发 | 按键和运行窗口拿到一份合约实例，再取数据 |

## 常用数据键

| 键 | 范围 | 用途 |
| --- | --- | --- |
| `stock.list` | 全局 | 股票列表 |
| `stock.kline.daily/weekly/monthly` | 逐股 | K 线 |
| `stock.finance.quarterly` | 逐股 | 季度财务 |
| `stock.indicators.daily` | 逐股 | 日频指标 |
| `stock.adj_factor.eventlog` | 逐股 | 复权因子事件 |
| `stock.moneyflow.daily` | 逐股 | 资金流 |
| `stock.st_periods` | 逐股 | ST/\*ST 时段 |
| `index.list` | 全局 | 指数列表 |
| `index.kline.daily` | 逐股 | 指数日 K |
| `index.weight.daily` | 逐股 | 指数权重 |
| `trade.calendar` | 全局 | 交易日历 |
| `macro.gdp/cpi/ppi/pmi/lpr/shibor` | 全局 | 宏观 |
| `tag` | 全局 | 标签 |

用户可在 `userspace/extensions/data_contract/` 下加自己的键，系统会合并进注册表。

## 策略里怎么声明

```python
"data": {
    "base": {"data_key": "stock.kline.daily"},
    "required": [
        {"data_key": "stock.finance.quarterly"},
        {"data_key": "stock.moneyflow.daily"},
    ],
}
```

`base` 决定回测怎么推进：逐股逐日、全局一份、或一次性静态表。`required` 是额外依赖。

框架会：

- 归一化声明（键、参数、范围）
- 全局数据只加载一次，再分给各任务
- 逐股数据在任务里按窗口或按时间切片加载
- 底层仍走数据访问层，不在策略里直连数据库

当 base 是 `stock.kline.*` 时，系统会自动带上 `stock.st_periods`。

## 合约长什么样

每份合约有三层：

| 层 | 内容 |
| --- | --- |
| meta | 键、类型（时序 / 非时序）、范围（全局 / 逐股）、唯一键 |
| runtime | 起止时间、股票列表 |
| specific | 类型特有字段 |

逐股合约必须指出对应的列表键（通常是 `stock.list`），用来确定覆盖哪些实体。

自定义契约放在 `userspace/extensions/data_contract/<key>/`：`declaration.py` + `loader.py`，并在 `data_keys.py` 注册。声明和加载器必须成对；键不能重复。
