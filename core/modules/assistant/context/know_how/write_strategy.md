---
title: write strategy 写一个策略
aliases:
  - strategy
  - write
  - hooks
  - 写策略
  - 策略钩子
summary: 编写策略：strategy.py 钩子与 settings.py。取数用 items_with_meta；指标用 Indicator。
---

# 如何编写策略

## 从模板创建

最快的方式是复制空模板：

```bash
python cli.py -n my_rsi_strategy
```

会在 `userspace/strategies/my_rsi_strategy/` 下生成两个文件：`strategy.py` 和 `settings.py`。模板里的 `meta.key` 仍是 `empty_strategy`，**立刻改成与目录名相同**（这里是 `my_rsi_strategy`）。

## 两个文件

策略由两个文件组成：

| 文件            | 职责                                           |
| ------------- | -------------------------------------------- |
| `strategy.py` | 策略钩子，继承 `StrategyHooks`，实现 `is_opportunity` |
| `settings.py` | 策略配置，一个 Python 字典                            |

## strategy.py

继承 `StrategyHooks`，**必须实现** `is_opportunity`：

```python
from core.modules.strategy.contracts import (
    Records,
    StrategyContext,
    StrategyHooks,
)

class RsiStrategy(StrategyHooks):
    def is_opportunity(self, ctx: StrategyContext, records: Records) -> bool:
        today = records.record_of_today
        if today is None:
            return False
        rsi = today.get("rsi14")  # settings.data.base.indicators 声明后写入
        if rsi is None:
            return False
        ctx.capture("rsi", rsi)
        ctx.capture("close", today.get("close"))
        return rsi < 30
```

指标在 `settings.data.base.indicators` 声明，钩子只读 K 线字段。不要手写 RSI/EMA。MACD 金叉见 [用技术指标](use_indicators.md)。

### 核心钩子

| 钩子 | 必须 | 说明 |
| --- | -- | --- |
| `is_opportunity(ctx, records) -> bool` | 是 | 每日每股调用一次，返回 True 表示有交易机会 |
| `on_calendar_slice(ctx, calendar_slice) -> list[str]` | 否 | slice_based 每个日历日，返回进入单股判定的 id |
| `select_portfolio_entries(ctx, opportunities)` | 否 | 机会多于空位时挑选 |
| `is_stop_loss` / `is_take_profit` | 否 | goal 段写了 custom 时调用 |

`ctx` 在每个钩子里一样：`ctx.info`、`ctx.sample_list`、`ctx.mode`、`ctx.effective_settings_dict()`、`ctx.state`（跨日）、`ctx.capture`（本笔归因）。当日序列在 `records`，不在 `ctx`。

| 取数 | 说明 |
| --- | --- |
| `records.record_of_today` | 当天最后一根 base K 线（无则 `None`） |
| `records.items` | 按数据键取序列 |
| `records.last(n)` / `get_record(date)` / `get_records(start, end)` | 序列快捷 |
| `ctx.base_data_key` | 主数据键，通常 `stock.kline.daily` |
| `ctx.state["key"] = value` | 跨日变量 |
| `ctx.capture(key, value)` | 本笔归因 |

### 关键设计

- **只返回 True/False**：`Opportunity` 对象由框架自动构建，不要手动 new

- **ctx.capture vs ctx.remember**：capture 落报告归因，remember 不落

- **取数**：`data.get(ctx.base_data_key)` 是当天及之前的全部历史（前复权），不是只有当天一根

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
        "base": {
            "data_key": "stock.kline.daily",
            "params": {},
            "indicators": {"rsi": [{"length": 14}]},
        },
        "min_required_records": 30,
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
}
```

### 必填字段

| 字段                               | 说明                             |
| -------------------------------- | ------------------------------ |
| `meta.key`                       | 策略唯一标识，应与目录名一致               |
| `data.base.data_key`             | 主数据契约，通常是 `stock.kline.daily`  |
| `simulation.execution.mode`      | `entity_based` 或 `slice_based` |
| `simulation.assumption.template` | 交易假设模板                         |
| `portfolio.allocation.mode`      | 资金分配模式                         |

详细的 settings 字段参考见 [配置策略 settings](config_strategy_settings.md)。

## 执行模式选择

| 模式             | 适用         | 特点                  |
| -------------- | ---------- | ------------------- |
| `entity_based` | 少股票、长时间窗口  | 按股票分组，每组跑完整时间线      |
| `slice_based`  | 多股票、中等时间窗口 | 按日历切片，每片处理全部股票，内存安全 |

## 自定义止盈止损钩子

如果 `goal` 中用了 `custom` 触发条件，需要在 strategy.py 中实现：

```python
def is_stop_loss(self, ctx, records, *, custom, stage) -> bool:
    if custom == "below_ma20":
        klines = records.items.get(ctx.base_data_key) or []
        if len(klines) >= 20:
            ma20 = sum(b["close"] for b in klines[-20:]) / 20
            return klines[-1]["close"] < ma20
    return False

def is_take_profit(self, ctx, records, *, custom, stage) -> bool:
    if custom == "rsi_overbought":
        today = records.record_of_today
        rsi = None if today is None else today.get("rsi14")
        return rsi is not None and rsi > 70
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

1. `python cli.py -n my_strategy` — 从模板创建（界面列表不能直接「新建」）
2. 把 `settings.py` 的 `meta.key` 改成 `my_strategy`（与目录名一致）
3. 编写 `strategy.py` 的 `is_opportunity`（指标见 [用技术指标](use_indicators.md)）
4. 配齐 `settings.py`（也可之后在制定策略左侧改参数）
5. 导航 **制定策略** 分步跑，或 `python cli.py sim --strategy my_strategy`
6. 报告在 `{strategy}/results/simulations/{vid}/`，看图诊断

界面操作见 [从界面制定策略](use_strategy_workbench.md)。看图见 [如何读回测报告](read_backtest_report.md)。

