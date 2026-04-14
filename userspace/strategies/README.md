# 策略（`userspace/strategies/`）

这里是**策略用户空间**：你定义“买入信号是什么”（`strategy_worker.py`），以及“策略怎么跑”（`settings.py`），框架会负责把扫描、枚举、模拟流程串起来。

策略模拟和扫描是整个框架的核心，需要理解的概念略多一些，我会尽量用最简单的方法描述清楚：

首先是两个不同的行为：回测 vs 扫描
- 回测：就是用你定义好的一套规则去使用历史数据测试它是不是有效的
- 扫描：就是用你定义的策略跑到最新的数据（需要通过 DataSource 模块拉取最近数据）上去，对所有你觉得有价值的股票扫描一遍，看看有没有现成的机会

其次是多层模拟（只针对回测行为）
- 机会枚举：我通过你定义的找到机会的方法去在历史记录里一条一条测，发现机会我就记录，一直到机会结束。枚举器的作用是记录整个历史中出现的机会（其实在当前系统里，它最重要的作用是缓存 ^_^）
- 价格因子模拟：我通过枚举出来的所有机会去投资1股，一只到投资完整个时间轴，我看看这1个股票的价格是怎么波动的，我的ROI（回报率）是不是正的。这个回测的主要作用是快速验证策略是不是个有效策略
- 资金模拟：我在按照我定义的策略枚举出的所有股票的所有时间段上进行模拟持仓投资，这个模拟加入了自己管理和分配策略，更加真实地模拟现实生活中的投资。里边包括我怎么持有多只股票，怎么分配仓位等等因素的记入

请注意：当前三层模拟对于您可能的重要的含义是：
- 机会枚举：看看我的策略能不能找到机会，找到的多不多。（机会枚举的中间数据对机器学习也比较友好）
- 价格因子模拟：初步看看我的策略是不是对目标股票有效，但注意这里得到的ROI与您的实际策略投资回报不是一回事，这里只能证明您的策略是不是对目标股票产生正向收益，正向收益是不是足够大。
- 资金模拟：这个模拟才是更接近实际的投资模拟。您还需要加入仓位管理才能真正实现盈利。有可能我的策略普遍对大部分股票都是盈利的，但我运气不好就是分配了大部分资金去了亏损的股票，那您的总体收益很可能是负的。


## 一分钟运行自带的example策略

先试着跑一下：

- 打开 `example/settings.py`，确认 `"is_enabled": True`。
- 在仓库根目录执行机会扫描：

```bash
python start-cli.py scan
```
就是基于当前最新数据扫描机会。现实中您需要先拉取最新的数据（renew）再扫描机会（scan）。

- 用历史数据模拟回测：

枚举所有机会：
```bash
python start-cli.py -se
```

价格因子模拟：
```bash
python start-cli.py -sp
```

资金模拟：
```bash
python start-cli.py -sa
```

通过不同模拟，您将看到不同的结果

---

## 从 0 开始创建一个新策略

### Step 1）先建一个策略目录

例如创建：

```text
userspace/strategies/my_strategy/
├── settings.py
└── strategy_worker.py
```

目录名建议和 `settings["name"]` 一致，便于排查与管理。

### Step 2）先写 `settings.py`（决定“怎么跑”）

你可以从 `settings_example.py` 精简出最小版本。最少建议包含：

- `name`
- `is_enabled`
- `core`
- `data.base_required_data`
- `goal`

例如（最小可读示例）：

```python
settings = {
    "name": "my_strategy",
    "description": "my first strategy",
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

### Step 3）写 `strategy_worker.py`（决定“什么时机发信号”）

最核心就是实现 `scan_opportunity(data, settings)`，命中条件就返回 `Opportunity`，否则返回 `None`。

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
        rsi = latest.get("rsi14")
        if rsi is None or rsi >= settings["core"]["rsi_oversold_threshold"]:
            return None
        return Opportunity(stock=self.stock_info, record_of_today=latest)
```

### Step 4）运行并验证

```bash
python start-cli.py scan --strategy my_strategy
python start-cli.py enumerate --strategy my_strategy
python start-cli.py simulate --strategy my_strategy
```

### Step 5）看结果目录

结果通常在：

`userspace/strategies/my_strategy/results/`

这个目录默认是本地产物目录，不建议提交大结果文件到 Git。

## 目录结构

```text
userspace/strategies/
├── settings_example.py
├── example/
├── example_activity_high/
└── <your_strategy>/
    ├── settings.py
    ├── strategy_worker.py
    ├── stock_lists/          # 可选：股票池文件
    └── results/              # 运行后生成
```

## 更多说明

- 详细参数说明看 [settings_example.py](settings_example.py)
- 完整使用说明看 [USER_GUIDE.md](USER_GUIDE.md)
