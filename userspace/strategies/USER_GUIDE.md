# 策略用户指南（userspace）

这份文档给“要自己写策略”的用户，目标是：从零开始能跑通一个策略，并知道后续怎么迭代。

---

## 1. 策略到底由哪两部分组成？

一个策略目录通常就两件核心文件：

- `settings.py`：策略参数和运行方式
- `strategy_worker.py`：买入信号逻辑（`scan_opportunity`）

框架负责：

- 数据准备（按 settings）
- 扫描 / 枚举 / 模拟执行
- 结果输出与版本管理

你主要负责“策略逻辑 + 配置”。

---

## 2. 最小可运行模板

目录：

```text
userspace/strategies/my_strategy/
├── settings.py
└── strategy_worker.py
```

`settings.py` 最小建议：

```python
settings = {
    "name": "my_strategy",
    "description": "demo",
    "is_enabled": True,
    "core": {"rsi_oversold_threshold": 20},
    "data": {
        "base_required_data": {"params": {"term": "daily", "adjust": "qfq"}},
        "extra_required_data_sources": [],
        "min_required_records": 30,
        "indicators": {"rsi": [{"period": 14}]},
    },
    "goal": {
        "expiration": {"fixed_window_in_days": 30, "is_trading_days": True},
        "stop_loss": {"stages": [{"name": "loss10%", "ratio": -0.1, "close_invest": True}]},
        "take_profit": {"stages": [{"name": "win20%", "ratio": 0.2, "close_invest": True}]},
    },
}
```

`strategy_worker.py` 最小建议：

```python
from typing import Dict, Any, Optional
from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from core.modules.strategy.models.opportunity import Opportunity


class MyStrategyWorker(BaseStrategyWorker):
    def scan_opportunity(self, data: Dict[str, Any], settings: Dict[str, Any]) -> Optional[Opportunity]:
        klines = data.get("klines", [])
        if not klines:
            return None
        latest = klines[-1]
        if latest.get("rsi14") is None:
            return None
        if latest["rsi14"] >= settings["core"]["rsi_oversold_threshold"]:
            return None
        return Opportunity(stock=self.stock_info, record_of_today=latest)
```

---

## 3. 运行命令怎么选？

### 只看今天有没有信号

```bash
python start-cli.py scan --strategy my_strategy
```

### 先枚举机会，再做模拟

```bash
python start-cli.py enumerate --strategy my_strategy
python start-cli.py simulate --strategy my_strategy
```

### 只跑价格层或资金层

```bash
python start-cli.py simulate_price --strategy my_strategy
python start-cli.py simulate_allocation --strategy my_strategy
```

---

## 4. 常见改动点（最常用）

- 改信号阈值：`settings["core"]`
- 改数据周期/复权：`settings["data"]["base_required_data"]["params"]`
- 增加额外依赖数据（如 macro/tag）：`extra_required_data_sources`
- 改止盈止损：`settings["goal"]`
- 控制测试规模：`settings["sampling"]` / `enumerator.use_sampling`

---

## 5. 结果在哪里看？

默认在：

`userspace/strategies/<strategy_name>/results/`

常见子目录包含：

- `opportunity_enums/`（枚举结果）
- `simulations/`（价格与资金模拟结果）
- `scan/`（扫描结果）

---

## 6. 常见问题

### Q1：为什么命令跑了但没用到我的策略？

- 检查 `settings.py` 的 `is_enabled` 是否为 `True`
- 检查 `--strategy` 参数是否和目录名/配置名一致

### Q2：为什么一直没有机会？

- 先打印 `scan_opportunity` 里关键条件（例如 RSI 值）
- 先降低阈值，确认链路是通的，再逐步收紧条件

### Q3：为什么提示数据不足？

- 提高历史数据覆盖范围
- 或降低 `min_required_records`

---

## 7. 参考

- 参数大全：`userspace/strategies/settings_example.py`
- 入口文档：`userspace/strategies/README.md`
- 核心模块：`core/modules/strategy/README.md`
