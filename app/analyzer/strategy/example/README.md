### 如何添加一个自定义投资策略（示例指引）

这个目录提供了最小可运行的示例：`example.py`（策略入口）、`settings.py`（策略配置）。参考它们即可快速创建你自己的策略。

### 目录结构与命名约定

- **策略目录**: 在 `app/analyzer/strategy/` 下新建你的策略文件夹，例如 `MYST/`。注意：你的策略文件夹必须是你的基类里的`abbreviation`的值
- **策略设置**: 在 `app/analyzer/strategy/` 下新建你的策略设置文件，名字必须是`settings.py`, 并且里边的变量名必须叫`settings`
- **入口文件命名**: 入口文件需与文件夹同名，例如 `MyStrategy/MYST.py`。注意：你的策略文件名必须是你的基类里的`abbreviation`的值
- **策略类**: 在入口文件中定义一个继承自 `BaseStrategy` 的类（类名不限）
- **是否启用**: 通过类属性 `is_enabled: bool` 控制是否参与扫描/模拟

### 最小实现要点

1) 继承 `BaseStrategy` 并声明必要信息

```python
from app.analyzer.libs.base_strategy import BaseStrategy
from app.analyzer.libs.simulator.simulator import Simulator

class MyStrategy(BaseStrategy):
    is_enabled = True

    def __init__(self, db, is_verbose: bool = False):
        super().__init__(
            db=db,
            is_verbose=is_verbose,
            name="My Strategy",
            abbreviation="MYST"  # 短、唯一、机器可读（表前缀/标识）
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

可直接复用 `example/example_settings.py` 结构：

- **mode**: 是否只跑黑名单、测试股票数量等
- **klines**: 模拟所需的 K 线周期与基础周期（`base_term`）
- **simulation**: 回测起止日期
- **goal**: 止盈/止损目标及阶段配置
- **blacklist**: 黑名单配置（配合 `mode.blacklist_only` 使用）

### 自动发现与注册

应用会在启动时自动扫描 `app/analyzer/strategy/*/*`：

- 目录名为 `YourStrategy`，入口文件为 `YourStrategy.py`
- 入口文件内存在一个继承 `BaseStrategy` 的类（且具有 `is_enabled` 属性）
- 若 `is_enabled = True`，系统会实例化并调用 `initialize()`，注册所需表；随后即可参与 `scan()` 与 `simulate()`

相关代码参考：`app/analyzer/analyzer.py` 中的策略注册逻辑。

### 启用与运行

1) 在你的策略类中将 `is_enabled = True`
2) 运行应用入口：

```bash
python start.py
```

默认会执行模拟流程（见 `start.py` 的 `app.simulate()`）。如需只扫描，可在 `start.py` 中改为调用 `await app.scan()`。

### 示例文件对照

- 策略入口：`example.py`
- 策略设置：`example_settings.py`
- 单日逻辑：`example_simulator.py`

产物（如快速模拟报告）默认写入 `app/analyzer/strategy/<folder_name>/tmp/`。


