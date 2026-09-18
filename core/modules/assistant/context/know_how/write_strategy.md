---
title: write strategy 写一个策略
aliases:
  - strategy
  - write
  - settings
  - hooks
summary: 使用NTQ为一个实体贴上不同的标签。
---

# 如何编写策略

## 从模板创建

最快的方式是复制空模板：

```bash
python cli.py -n my_rsi_strategy
```

会在 `userspace/strategies/my_rsi_strategy/` 下生成两个文件：`strategy.py` 和 `settings.py`。

## 两个文件

策略由两个文件组成：

| 文件            | 职责                                           |
| ------------- | -------------------------------------------- |
| `strategy.py` | 策略钩子，继承 `StrategyHooks`，实现 `has_opportunity` |
| `settings.py` | 策略配置，一个 Python 字典                            |

## strategy.py

继承 `StrategyHooks`，**必须实现** `has_opportunity`：

```python
from core.modules.strategy.contracts import (
    StrategyContext,
    StrategyHooks,
)

class RsiStrategy(StrategyHooks):
    def has_opportunity(self, ctx: StrategyContext) -> bool:
        klines = ctx.data("stock.kline.daily")
        if klines is None or len(klines) < 14:
            return False

        close = [bar["close"] for bar in klines]
        rsi = self._calc_rsi(close, 14)

        ctx.capture("rsi", rsi)
        ctx.capture("close", close[-1])
        return rsi < 30

    def _calc_rsi(self, closes, period):
        gains, losses = [], []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
```

### 核心钩子

| 钩子                             | 必须 | 说明                               |
| ------------------------------ | -- | -------------------------------- |
| `has_opportunity(ctx) -> bool` | 是  | 每日每股调用一次，返回 True 表示有交易机会         |
| `on_before_scan(ctx)`          | 否  | 扫描前调用一次，适合预加载数据                  |
| `on_after_scan(ctx)`           | 否  | 扫描后调用一次，适合输出统计                   |
| `on_calendar_asof(ctx)`        | 否  | slice\_based 模式下每个日历点调用，可做跨股全局判断 |

### ctx 常用方法

| 方法                              | 说明                    |
| ------------------------------- | --------------------- |
| `ctx.data("stock.kline.daily")` | 获取当日及之前的数据序列（前复权）     |
| `ctx.capture(key, value)`       | 记录信号快照，落报告（事后分析用）     |
| `ctx.remember(key, value)`      | 钩子间传递的易失内存（不落报告）      |
| `ctx.recall(key, default)`      | 取出 remember 的值        |
| `ctx.effective_settings_dict()` | 获取 effective settings |

### 关键设计

- **只返回 True/False**：`Opportunity` 对象由框架自动构建，不要手动 new

- **ctx.capture vs ctx.remember**：capture 落报告归因，remember 不落

- **ctx.data 返回序列**：不是只有当天一根 K 线，是当天及之前的全部历史

## settings.py

```python
settings = {
    "is_enabled": True,
    "meta": {
        "key": "my_rsi_strategy",
        "display_name": "RSI 超卖策略",
        "description": "RSI(14) 低于 30 时买入",
    },
    "core": {
        "rsi_threshold": 30,
    },
    "data": {
        "base": {"data_key": "stock.kline.daily"},
        "min_required_records": 14,
        "required": [],
    },
    "goal": {
        "expiration": {"fixed_window_in_days": 30, "mode": "open_day"},
        "stop_loss": {"stages": [{"ratio": -0.10, "close_invest": True}]},
        "take_profit": {"stages": [{"ratio": 0.30, "close_invest": True}]},
    },
    "fees": {
        "commission_rate": 0.00025,
        "min_commission": 5.0,
        "stamp_duty_rate": 0.001,
        "transfer_fee_rate": 0.0,
    },
    "simulation": {
        "execution": {"start_date": "", "end_date": "", "mode": "entity_based"},
        "assumption": {"template": "standard"},
    },
    "portfolio": {
        "initial_capital": 1_000_000,
        "allocation": {
            "mode": "equal_capital",
            "max_portfolio_size": 10,
            "max_weight_per_stock": 0.3,
            "lots_per_trade": 1,
        },
    },
    "scanner": {
        "adapters": ["console"],
    },
    "analysis": {"enabled": True},
}
```

### 必填字段

| 字段                               | 说明                             |
| -------------------------------- | ------------------------------ |
| `meta.key`                       | 策略唯一标识                         |
| `data.base.data_key`             | 主数据合约，通常是 `stock.kline.daily`  |
| `simulation.execution.mode`      | `entity_based` 或 `slice_based` |
| `simulation.assumption.template` | 交易假设模板                         |
| `portfolio.allocation.mode`      | 资金分配模式                         |

详细的 settings 字段参考见 `global/llm_strategy_settings_reference.md`。

## 执行模式选择

| 模式             | 适用         | 特点                  |
| -------------- | ---------- | ------------------- |
| `entity_based` | 少股票、长时间窗口  | 按股票分组，每组跑完整时间线      |
| `slice_based`  | 多股票、中等时间窗口 | 按日历切片，每片处理全部股票，内存安全 |

## 自定义止盈止损钩子

如果 `goal` 中用了 `custom` 触发条件，需要在 strategy.py 中实现：

```python
def is_stop_loss(self, ctx, *, custom, stage) -> bool:
    if custom == "below_ma20":
        klines = ctx.data("stock.kline.daily")
        if klines and len(klines) >= 20:
            ma20 = sum(b["close"] for b in klines[-20:]) / 20
            return klines[-1]["close"] < ma20
    return False

def is_take_profit(self, ctx, *, custom, stage) -> bool:
    if custom == "rsi_overbought":
        klines = ctx.data("stock.kline.daily")
        if klines and len(klines) >= 14:
            close = [b["close"] for b in klines]
            rsi = self._calc_rsi(close, 14)
            return rsi > 70
    return False
```

settings.py 中对应配置：

```python
"goal": {
    "stop_loss": {"stages": [{"custom": "below_ma20", "close_invest": True}]},
    "take_profit": {"stages": [{"custom": "rsi_overbought", "close_invest": True}]},
}
```

## 完整流程

1. `python cli.py -n my_strategy` — 从模板创建
2. 编写 `strategy.py` 的 `has_opportunity`
3. 配置 `settings.py`
4. `python cli.py s` — 跑完整回测
5. 查看报告，诊断策略问题

