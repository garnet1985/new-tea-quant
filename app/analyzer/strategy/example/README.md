### 如何添加一个自定义投资策略（示例指引）

这个目录提供了最小可运行的示例：`example.py`（策略入口）、`example_settings.py`（策略配置）、`example_simulator.py`（单日模拟逻辑）。参考它们即可快速创建你自己的策略。

### 目录结构与命名约定

- **策略目录**: 在 `app/analyzer/strategy/` 下新建你的策略文件夹，例如 `MyStrategy/`
- **入口文件命名**: 入口文件需与文件夹同名，例如 `MyStrategy/MyStrategy.py`
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
        self.strategy_settings = {...}  # 可从单独 settings.py 导入
        self.simulator = Simulator()

    def initialize(self):
        self.required_tables = {
            "stock_index": self.db.get_table_instance("stock_index"),
            "stock_kline": self.db.get_table_instance("stock_kline"),
            "adj_factor": self.db.get_table_instance("adj_factor"),
        }

    async def scan(self):
        # 返回机会列表：List[Dict[str, Any]]
        return []

    def simulate(self):
        return self.simulator.run(
            settings=self.strategy_settings,
            on_simulate_one_day=MySimulator.simulate_single_day,
            on_single_stock_summary=self.stock_summary,
        )

    def stock_summary(self, result):
        return {}
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

- **folder_name**: 用于存放该策略产物的父目录名（与策略目录同名更直观）
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


