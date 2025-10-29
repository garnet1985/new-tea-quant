### 如何添加一个自定义投资策略（示例指引）

这个目录提供了最小可运行的示例：`example.py`（策略入口）、`settings.py`（策略配置）。参考它们即可快速创建你自己的策略。

### 目录结构与命名约定

- **策略目录**: 在 `app/analyzer/strategy/` 下新建你的策略文件夹，例如 `MYST/`。注意：你的策略文件夹必须是你的基类里的`key`的值
- **策略设置**: 在 `app/analyzer/strategy/` 下新建你的策略设置文件，名字必须是`settings.py`, 并且里边的变量名必须叫`settings`
- **入口文件命名**: 入口文件需与文件夹同名，例如 `MyStrategy/MYST.py`。注意：你的策略文件名必须是你的基类里的`key`的值
- **策略类**: 在入口文件中定义一个继承自 `BaseStrategy` 的类（类名不限）
- **是否启用**: 在 `settings.py` 中通过 `is_enabled` 配置控制是否参与扫描/模拟

### 最小实现要点

1) 继承 `BaseStrategy` 并声明必要信息

```python
from app.analyzer.libs.base_strategy import BaseStrategy
from app.analyzer.libs.simulator.simulator import Simulator

class MyStrategy(BaseStrategy):
    def __init__(self, db, is_verbose: bool = False):
        super().__init__(
            db=db,
            is_verbose=is_verbose,
            name="My Strategy",
            key="MYST"  # 短、唯一、机器可读（表前缀/标识）
        )
        super().initialize()

    def scan_opportunity(self, stock_id: str, data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """扫描单只股票的投资机会"""
        # define your opportunity identification logic here...
        # the opportunity need to call BaseStrategy.to_opportunity to convert to a standard opportunity entity
        return None

    # other event methods can be overridden here...
    # on_before_simulate, on_summarize_stock, on_summarize_session, on_before_report

    # if any extra field need to be added to the opportunity, you can override the to_opportunity method
    # to_investment, to_settled_investment
```

2) 提供单日模拟函数（可放在同文件或独立 `MySimulator.py`）

```python
class MySimulator:
    @staticmethod
    def simulate_single_day(stock_id, current_date, current_record, historical_data, current_investment):
        # 返回包含以下键的字典：
        # - new_investment: Optional[Dict]
        # - settled_investments: List[Dict]
        # - current_investment: Optional[Dict]
        return {
            "new_investment": None,
            "settled_investments": [],
            "current_investment": current_investment,
        }
```

3) 策略设置（建议独立成 `settings.py` 并在策略入口中导入）

可直接复用 `example/settings.py` 结构：

```python
settings = {
    # 策略启用状态（必需）
    "is_enabled": True,  # 设为 False 将跳过该策略
    
    # 其他配置...
}
```

主要配置项：
- **is_enabled**: 策略启用状态，True 表示参与扫描/模拟，False 表示跳过
- **mode**: 是否只跑黑名单、测试股票数量等
- **klines**: 模拟所需的 K 线周期与信号检测周期（`signal_base_term`）和模拟执行周期（`simulate_base_term`）
- **simulation**: 回测起止日期
- **goal**: 止盈/止损目标及阶段配置，支持"到期平仓（固定自然日/交易日）"与阶段对到期规则的调整
- **blacklist**: 黑名单配置（配合 `mode.blacklist_only` 使用）

### 自动发现与注册

应用会在启动时自动扫描 `app/analyzer/strategy/*/*`：

- 目录名为 `YourStrategy`，入口文件为 `YourStrategy.py`
- 入口文件内存在一个继承 `BaseStrategy` 的类，且 `settings.py` 中配置了 `is_enabled`
- 若 `settings` 中 `is_enabled = True`，系统会实例化并调用 `initialize()`，注册所需表；随后即可参与 `scan()` 与 `simulate()`

相关代码参考：`app/analyzer/analyzer.py` 中的策略注册逻辑。

### 启用与运行

1) 在你的 `settings.py` 中将 `is_enabled` 设为 `True`
2) 运行应用入口：

```bash
python start.py
```

默认会执行模拟流程（见 `start.py` 的 `app.simulate()`）。如需只扫描，可在 `start.py` 中改为调用 `await app.scan()`。

### goal 配置：固定期限强制平仓（可选）

在 `goal` 下新增以下字段以启用到期平仓能力（不配置则不生效）：

```python
"goal": {
  # 自然日到期；例如 30 天后强制对剩余仓位平仓
  "fixed_days": 30,

  # 交易日到期（可选，计数逻辑为遇到新日期 +1）
  # "fixed_trading_days": 20,

  # 止损与止盈配置（可为空；若均为空，仅按 fixed_* 到期平仓）
  "stop_loss": { ... },
  "take_profit": { ... }
}
```

### 阶段对到期规则的动态调整（可选）

当某个止盈/止损阶段触发时，支持动态调整或取消到期规则：

```python
{
  "name": "win10%",
  "ratio": 0.10,
  "sell_ratio": 0.2,
  # 调整 fixed_days / fixed_trading_days（正为增加，负为减少）
  # "extend_fixed_days": 3,
  # "extend_fixed_trading_days": -2,
  # 取消到期规则
  # "cancel_fixed_days": true,
  # "cancel_fixed_trading_days": true
}
```

行为说明：
- 若仅配置 fixed_*（无止盈止损），则只按到期平仓；
- 若同时存在 fixed_* 与阶段，任一条件达成即对剩余仓位平仓；
- 阶段触发时的 extend/cancel 仅在对应字段存在时才生效。

### 示例文件对照

- 策略入口：`example.py`
- 策略设置：`settings.py`
- 单日逻辑：`example_simulator.py`

产物（如快速模拟报告）默认写入 `app/analyzer/strategy/<folder_name>/tmp/`。


