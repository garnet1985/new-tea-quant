---
title: 配置策略 settings
aliases:
  - settings.py
  - goal
  - 止盈止损
  - 止损止盈
  - 策略配置
  - 配置
summary: 策略 settings.py 各块字段，以及 goal 止盈止损怎么写。
---

# 策略 settings.py

描述 `settings.py` 的完整结构。字段是 Python 字典，大部分时候当 JSON 写即可。

## 顶层结构

```python
settings = {
    "is_enabled": True,            # bool, 策略是否启用
    "meta": {...},                 # 策略元信息
    "market_profile": "china_a_stock",  # str, 市场画像
    "core": {...},                 # 策略私有参数（自由定义）
    "data": {...},                 # 数据声明
    "simulation": {...},           # 回测执行配置
    "goal": {...},                 # 止盈止损过期规则
    "sampling": {...},             # 股票池采样
    "portfolio": {...},           # 资金管理
    "scanner": {...},              # 扫描配置
    "fees": {...},                 # 手续费
    "analysis": {...},             # 归因分析
}
```

必须字段：`meta.key`（应与策略目录名一致）。加载时会对缺块补默认，所以省略某些块也能跑；新建策略请用模板写全 `data` / `goal` / `simulation` / `portfolio` / `fees`，不要只留 `meta`。settings **不和** `data.json` 合并。

## meta

```python
"meta": {
    "key": "rsi_v1",               # str, 必填, 策略唯一标识, CLI 用 --strategy 找它
    "display_name": "RSI 超卖反弹",   # str, 显示名
    "description": "RSI 低于 30 时买入",  # str, 描述
    "category": "mean_reversion",  # str, 分类
    "keywords": ["rsi", "oversold"],  # list[str], 关键词
}
```

注意：改 `key` 等于换了一个策略，历史版本不会自动关联。

## core

策略私有参数，自由定义。在钩子里通过 `self.core_int(ctx.settings, key)` 和 `self.core_float(ctx.settings, key, clamp)` 读取。

```python
"core": {
    "rsi_period": 14,            # int
    "rsi_threshold": 30,         # float
    "rebalance_period": "year",  # str
}
```

无固定字段名，策略自定义。

## data

声明策略需要什么数据。

```python
"data": {
    "base": {
        "data_key": "stock.kline.daily",   # str, 基础 K 线数据
        "params": {},                       # dict, 不要写 adjust；顶层 OHLC 已是前复权
        "indicators": {                      # dict, 可选, 框架写入每根 K 线
            "rsi": [{"length": 14}],         # 当天 bar：rsi14
            "macd": [{"fast": 12, "slow": 26, "signal": 9}],
        },
    },
    "required": [                            # list[dict], 可选, 附加数据源
        {"data_key": "stock.finance.quarterly"},
        {"data_key": "macro.cpi"},
    ],
    "min_required_records": 100,             # int, 最少 K 线根数
}
```

`base.data_key` 决定数据路由模式：

- `stock.kline.daily` → 逐股逐日（entity\_based）

- `market.index.daily` → 全局单份（global）

- 静态表（如行业映射）→ 不按时间遍历（non\_time\_series）

`ctx.data` 不是函数。钩子里：

```python
data = ctx.data.items_with_meta()
klines = data.get(ctx.base_data_key) or []          # 当天及之前，前复权
finance = data.get("stock.finance.quarterly") or [] # required 里声明的键
today = ctx.record_of_today
rsi14 = today.get("rsi14") if today else None       # 单列注入字段 {name}{length}
```

不要写 `params.adjust`（会被剥掉）。指标在 `data.base.indicators` 声明，钩子读 K 线上的字段，不要钩子里再手算一遍。RSI 字段是 `{name}{length}`（`rsi14`）。MACD 是三列长名字，见 [用技术指标](use_indicators.md)。

## simulation

回测执行配置。

```python
"simulation": {
    "execution": {
        "start_date": "20220101",    # str, 回测起始日期 YYYYMMDD
        "end_date": "20241231",     # str, 回测结束日期 YYYYMMDD
        "mode": "slice_based",      # str, slice_based / entity_based
    },
    "assumption": {
        "template": "custom",       # str, standard / strict / ideal / extreme / custom / none
        "tradability": {
            "monitor_price": "close",
            "enter_price": "next_open",     # next_open / touch / open / close
            "exit_price": "close",           # next_open / open / close / high / low
            "slippage": {"enter_bps": 0.0, "exit_bps": 0.0},
            "edges": {
                "allow_enter_at_limit_up": False,    # 涨停不买
                "allow_exit_at_limit_down": False,    # 跌停不卖
            },
            "liquidity": {
                "max_participation_rate": None,       # 最大参与率
                "participation_on_exceed": "clip",     # clip / skip
            },
            "delisted_exit_price": "last_tradable_close",  # last_tradable_close / same_tick_close
        },
        "target_check_order": ["check_stop_loss", "check_take_profit", "check_expiration"],
    },
    "risk_control": {
        "skip_enter_when": ["st", "star_st"],    # ST/星ST 不买
        "force_exit_when": ["st"],               # 持仓变 ST 强平
        "pending_enter": {
            "max_wait_open_days": 5,             # 挂单最多等几个交易日
            "max_entry_drift": None,             # 最大入场偏移
            "abort_enter_when": ["st"],          # 挂单期间变 ST 撤单
        },
    },
}
```

### execution.mode 枚举

| 值              | 逻辑               | 适用         |
| -------------- | ---------------- | ---------- |
| `slice_based`  | 按时间切片，每片处理全部股票   | 多股票、中等时间窗口 |
| `entity_based` | 按股票分组，每组独立跑完整时间线 | 少股票、长时间窗口  |

### assumption.template 枚举

| 值          | 说明                  |
| ---------- | ------------------- |
| `standard` | 限价触及买入，收盘监控；涨停不买、跌停不卖；超参与率裁剪 |
| `strict`   | 同 standard 的涨跌停限制，超参与率则跳过 |
| `ideal`    | 涨跌停也可成交，仍有参与率上限（超限裁剪） |
| `extreme`  | 次日开盘尝试进场，涨跌停可成交，超限跳过 |
| `custom`   | 自定义 tradability 各字段 |
| `none`     | 不设假设                |

### target\_check\_order

止损止盈过期的检查顺序。默认 `["check_stop_loss", "check_take_profit", "check_expiration"]`。调换顺序会影响同日同时触发时的处理结果。

## goal

止盈止损过期规则。策略最核心的配置。

### 简单目标

```python
"goal": {
    "stop_loss": {
        "stages": [
            {"ratio": -0.10, "close_invest": True},   # 亏 10% 全部止损
        ],
    },
    "take_profit": {
        "stages": [
            {"ratio": 0.30, "close_invest": True},     # 涨 30% 全部止盈
        ],
    },
}
```

### 多段目标

```python
"goal": {
    "expiration": {"fixed_window_in_days": 100, "mode": "trading_day"},
    "stop_loss": {
        "stages": [
            {"ratio": -0.20, "close_invest": True},
        ],
    },
    "take_profit": {
        "stages": [
            {"ratio": 0.15, "exit_ratio": 0, "actions": ["set_protect_loss"]},   # 涨 15%：不卖，把止损抬到成本价
            {"ratio": 0.30, "exit_ratio": 0.5},                                   # 涨 30%：卖 50%
            {"ratio": 0.50, "exit_ratio": 0.4, "actions": ["set_dynamic_loss"]}, # 涨 50%：卖 40%，剩余交给动态止损
        ],
    },
    "protect_loss": {"ratio": 0, "close_invest": True},       # 保护性止损：成本价平仓
    "dynamic_loss": {"ratio": -0.15, "close_invest": True},   # 动态止损：从最高点回撤 15% 平仓
}
```

### stage 字段

| 字段             | 类型         | 说明                                                |
| -------------- | ---------- | ------------------------------------------------- |
| `ratio`        | float      | 触发比例。正数止盈，负数止损。与 `custom` 互斥                      |
| `custom`       | str        | 自定义触发条件名。会调用钩子的 `is_stop_loss` / `is_take_profit` |
| `close_invest` | bool       | True = 整笔退出。与 `exit_ratio` 二选一                    |
| `exit_ratio`   | float      | 退出比例（0\~1），相对初始总仓位                                |
| `actions`      | list\[str] | 触发后附加动作：`set_protect_loss`、`set_dynamic_loss`     |

规则：

- `ratio` 和 `custom` 互斥，一个 stage 只能用一个

- `close_invest=True` 时 `exit_ratio` 等于 1.0

- `actions` 里的 `set_protect_loss` 会激活 `goal.protect_loss` 配置

- `actions` 里的 `set_dynamic_loss` 会激活 `goal.dynamic_loss` 配置

### expiration 字段

| 字段                     | 类型  | 说明                                                        |
| ---------------------- | --- | --------------------------------------------------------- |
| `fixed_window_in_days` | int | 持仓多少天后强制平仓                                                |
| `mode`                 | str | `open_day`（开仓日算起）/ `trading_day`（交易日）/ `natural_day`（日历日） |

## sampling

```python
"sampling": {
    "use_sampling": True,          # bool, 是否采样
    "strategy": "pool",            # str, uniform / stratified / random / pool / blacklist
    "sampling_amount": 500,        # int, 采样数量
    "pool": {
        "stock_ids": ["000001.SZ", "000002.SZ"],  # list[str], pool 模式指定股票
    },
}
```

### sampling.strategy 枚举

| 值            | 说明           |
| ------------ | ------------ |
| `uniform`    | 均匀随机抽样       |
| `stratified` | 分层抽样（按行业/市值） |
| `random`     | 纯随机          |
| `pool`       | 指定股票池        |
| `blacklist`  | 排除指定股票       |

## portfolio

```python
"portfolio": {
    "initial_capital": 1000000,          # int, 初始资金（元）
    "allocation": {
        "mode": "equal_capital",         # str, equal_capital / equal_shares / kelly / custom
        "max_portfolio_size": 10,        # int, 最多同时持有几只
        "max_weight_per_stock": 0.3,     # float, 单只最大仓位比例
        "lots_per_trade": 1,             # int, 每次交易几手（1手=100股，主板规则）
        "kelly_fraction": 0.5,           # float, kelly 模式下的比例
        "skip_trade_when_insufficient": False,  # bool, 资金不足时跳过
    },
    "output": {
        "save_trades": True,             # bool, 保存逐笔成交
        "save_equity_curve": True,       # bool, 保存净值曲线
    },
}
```

### allocation.mode 枚举

| 值               | 说明         |
| --------------- | ---------- |
| `equal_capital` | 等额资金分配     |
| `equal_shares`  | 等股数分配      |
| `kelly`         | 凯利公式分配     |
| `custom`        | 自定义（需实现钩子） |

注意：`lots_per_trade` 默认 1（100股/手），适用于主板和创业板。科创板最低 200 股起，1 股递增。北交所 100 股起，1 股递增。NTQ 当前不按板块区分交易单位。

## scanner

```python
"scanner": {
    "adapters": ["console"],               # list[str], 结果输出方式
    "use_strict_previous_trading_day": True,  # bool, 严格交易日检查
    "max_cache_days": 10,                  # int, 扫描结果保留天数
    "watch_list": "",                      # str, 关注列表
}
```

## fees

```python
"fees": {
    "commission_rate": 0.0003,     # float, 佣金费率（万三）
    "min_commission": 5.0,         # float, 最低佣金（元）
    "stamp_duty_rate": 0.001,      # float, 印花税（千一，卖出收）
    "transfer_fee_rate": 0.00001,  # float, 过户费（万零点一）
}
```

## analysis

```python
"analysis": {
    "enabled": False,    # bool, True 则回测后自动收集归因数据
}
```

## 动态 settings

settings.py 是 Python 文件，支持动态逻辑：

```python
import os

settings = {
    "meta": {"key": "rsi_v1"},
    "core": {
        "rsi_threshold": int(os.environ.get("RSI_THRESHOLD", "30")),
    },
}
```

一般用户当 JSON 写。需要动态参数时才用 Python 特性。

## 配置约束规则

1. `meta.key` 改了 = 新策略，历史版本不关联
2. `ratio` 和 `custom` 在一个 stage 内互斥
3. `close_invest=True` 和 `exit_ratio` 二选一，前者等于 `exit_ratio=1.0`
4. `exit_ratio` 的分母是初始总仓位，不是当前剩余仓位
5. `actions` 中的 `set_protect_loss` / `set_dynamic_loss` 需要对应的 `goal.protect_loss` / `goal.dynamic_loss` 配置存在
6. `data.base.data_key` 决定数据路由模式，影响枚举阶段的遍历方式
7. `execution.mode` 和 `data.base.data_key` 有联动关系：global 类型的 data\_key 通常配合 `slice_based` 模式
8. `lots_per_trade` 对主板/创业板有效，科创板/北交所的交易单位规则不同
9. `assumption.template` 为 `custom` 时才读取 `tradability` 各字段，其他模板有预设值
10. `target_check_order` 的顺序影响同日多条件触发时的处理优先级

## 钩子与 settings 的对应关系

| settings 字段                        | 对应钩子                                                            | 触发条件                    |
| ---------------------------------- | --------------------------------------------------------------- | ----------------------- |
| `goal.stop_loss.stages[].custom`   | `is_stop_loss(ctx, custom, stage)`                              | stage 用 custom 而非 ratio |
| `goal.take_profit.stages[].custom` | `is_take_profit(ctx, custom, stage)`                            | stage 用 custom 而非 ratio |
| `data.base`                        | `has_opportunity` 里 `data.get(ctx.base_data_key)` | 每日每股调用 |
| `data.required[]`                  | `has_opportunity` 里 `data.get(data_key)` | 每日每股调用 |
| `core` 里的字段                        | 钩子里 `self.core_int(ctx.settings, key)` / `self.core_float(...)` | 手动读取                    |

## 常见配置模式速查

### 模式1：简单固定止盈止损

```python
"goal": {
    "stop_loss": {"stages": [{"ratio": -0.10, "close_invest": True}]},
    "take_profit": {"stages": [{"ratio": 0.30, "close_invest": True}]},
}
```

### 模式2：分批止盈 + 保护性止损

```python
"goal": {
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

### 模式3：持仓过期自动平仓

```python
"goal": {
    "expiration": {"fixed_window_in_days": 60, "mode": "trading_day"},
    "stop_loss": {"stages": [{"ratio": -0.10, "close_invest": True}]},
    "take_profit": {"stages": [{"ratio": 0.20, "close_invest": True}]},
}
```

### 模式4：自定义技术指标止损止盈

settings:

```python
"goal": {
    "stop_loss": {"stages": [{"custom": "below_ma20", "close_invest": True}]},
    "take_profit": {"stages": [{"custom": "rsi_overbought", "close_invest": True}]},
}
```

strategy.py:

```python
def is_stop_loss(self, ctx, *, custom, stage):
    if custom == "below_ma20":
        data = ctx.data.items_with_meta()
        klines = data.get(ctx.base_data_key) or []
        if len(klines) >= 20:
            ma20 = sum(b["close"] for b in klines[-20:]) / 20
            return klines[-1]["close"] < ma20
    return False

def is_take_profit(self, ctx, *, custom, stage):
    if custom == "rsi_overbought":
        today = ctx.record_of_today
        rsi = None if today is None else today.get("rsi14")
        return rsi is not None and rsi > 70
    return False
```
