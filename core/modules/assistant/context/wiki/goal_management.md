---
title: goal management 回测目标管理
aliases:
  - goal
  - stop loss
  - take profit
  - expiration
  - strategy
  - goal stages
summary: NTQ的回测目标设置与管理
---

# 止盈止损体系（Goal Management）

## 概念

NTQ 的止盈止损不只是一个固定的盈亏比例，而是一个多阶段的目标管理系统。每个投资机会买入后，系统逐日检查是否触发止损、止盈或过期。

## 三种出场机制

| 机制 | 触发条件              | 配置位置                      |
| -- | ----------------- | ------------------------- |
| 止损 | 亏损达到设定比例，或自定义条件满足 | `goal.stop_loss.stages`   |
| 止盈 | 盈利达到设定比例，或自定义条件满足 | `goal.take_profit.stages` |
| 过期 | 持仓超过设定天数          | `goal.expiration`         |

## Stage 结构

每个 stage 可以用两种触发方式之一：

| 字段             | 类型    | 说明                                               |
| -------------- | ----- | ------------------------------------------------ |
| `ratio`        | float | 固定比例触发。正数止盈，负数止损。与 `custom` 互斥                   |
| `custom`       | str   | 自定义触发条件名，会调用钩子 `is_stop_loss` / `is_take_profit` |
| `close_invest` | bool  | True = 整笔退出                                      |
| `exit_ratio`   | float | 退出比例（0\~1），相对初始总仓位                               |
| `actions`      | list  | 触发后附加动作：`set_protect_loss`、`set_dynamic_loss`    |

## 简单模式

```python
"goal": {
    "stop_loss": {"stages": [{"ratio": -0.10, "close_invest": True}]},
    "take_profit": {"stages": [{"ratio": 0.30, "close_invest": True}]},
}
```

亏 10% 全部止损，涨 30% 全部止盈。

## 多段模式

```python
"goal": {
    "expiration": {"fixed_window_in_days": 100, "mode": "trading_day"},
    "stop_loss": {"stages": [{"ratio": -0.20, "close_invest": True}]},
    "take_profit": {
        "stages": [
            {"ratio": 0.15, "exit_ratio": 0, "actions": ["set_protect_loss"]},
            {"ratio": 0.30, "exit_ratio": 0.5},
            {"ratio": 0.50, "exit_ratio": 0.4, "actions": ["set_dynamic_loss"]},
        ],
    },
    "protect_loss": {"ratio": 0, "close_invest": True},
    "dynamic_loss": {"ratio": -0.15, "close_invest": True},
}
```

含义：

1. 涨 15%：不卖（`exit_ratio: 0`），但把止损抬到成本价（`set_protect_loss`）
2. 涨 30%：卖出初始仓位的 50%
3. 涨 50%：再卖 40%，剩余交给动态止损（`set_dynamic_loss`）
4. 动态止损：从最高点回撤 15% 时平仓
5. 过期：持仓 100 个交易日后强制平仓

## 保护性止损 vs 动态止损

| 类型                    | 触发比例基准                       | 激活方式                            |
| --------------------- | ---------------------------- | ------------------------------- |
| 保护性止损（`protect_loss`） | 成本价（ratio=0 表示成本价平仓）         | `actions: ["set_protect_loss"]` |
| 动态止损（`dynamic_loss`）  | 从最高点回撤（ratio=-0.15 表示回撤 15%） | `actions: ["set_dynamic_loss"]` |

## 自定义触发

用 `custom` 字段替代 `ratio`，让止损止盈基于技术指标而非固定比例：

```python
"goal": {
    "stop_loss": {"stages": [{"custom": "below_ma20", "close_invest": True}]},
    "take_profit": {"stages": [{"custom": "rsi_overbought", "close_invest": True}]},
}
```

策略钩子里实现对应逻辑：

```python
def is_stop_loss(self, ctx, *, custom, stage) -> bool:
    if custom == "below_ma20":
        klines = ctx.data("stock.kline.daily")
        if klines and len(klines) >= 20:
            ma20 = sum(b["close"] for b in klines[-20:]) / 20
            return klines[-1]["close"] < ma20
    return False
```

## 检查顺序

`target_check_order` 控制止损止盈过期的检查顺序，默认 `["check_stop_loss", "check_take_profit", "check_expiration"]`。同日同时触发时，排在前面的优先执行。

## exit\_ratio 的分母

`exit_ratio` 的分母是**初始总仓位**，不是当前剩余仓位。比如初始买 1000 股，`exit_ratio: 0.5` 卖 500 股，再触发 `exit_ratio: 0.4` 卖 400 股，剩余 100 股。
