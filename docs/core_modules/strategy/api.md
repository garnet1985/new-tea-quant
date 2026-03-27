# Strategy 模块 API 文档

按「描述、函数签名、参数、输出、示例」列出各 API。仅包含用户需要主动调用的入口；由框架自动调用的内部函数不列入。架构说明见 [architecture.md](./architecture.md) 与 [overview.md](./overview.md)。

---

## StrategyManager

### StrategyManager（构造函数）

**描述**：创建策略管理器。负责发现用户策略、加载配置与数据、协调 Scanner / 模拟器等组件。一般在命令行或脚本中构造一次后复用。

**函数签名**：`StrategyManager(is_verbose: bool = False)`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `is_verbose` | `bool` | 是否输出更详细日志（如进度、统计信息），默认 `False` |

**输出**：无（构造实例）

**Example**：

```python
from core.modules.strategy.strategy_manager import StrategyManager

manager = StrategyManager(is_verbose=True)
```

---

### scan

**描述**：执行**实时机会扫描**（Scanner 模式）。按配置扫描一个或多个策略在某个交易日的机会，结果持久化到 `results/scan/{date}/` 目录，用于实盘提示或后续分析。

**函数签名**：`StrategyManager.scan(strategy_name: str | None = None, date: str | None = None) -> None`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str \| None` | 策略名称；为 `None` 时会扫描所有 `is_enabled` 的策略 |
| `date` | `str \| None` | 扫描日期（`YYYYMMDD`），默认使用当天日期 |

**输出**：`None`（扫描结果写入结果目录）

**Example**：

```python
from core.modules.strategy.strategy_manager import StrategyManager

manager = StrategyManager(is_verbose=True)

# 扫描单个策略
manager.scan(strategy_name="my_strategy")

# 扫描所有启用的策略
manager.scan()
```

---

### simulate

**描述**：执行**历史回测模拟**（Simulator 模式）。按策略配置和采样规则，对指定日期范围进行完整回测，结果写入 `results/simulate/{strategy_name}/{session_id}/`。

**函数签名**：`StrategyManager.simulate(strategy_name: str | None = None, session_id: str | None = None, date: str | None = None) -> None`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str \| None` | 策略名称；为 `None` 时模拟所有启用的策略 |
| `session_id` | `str \| None` | 会话 ID；为 `None` 时自动创建新的 session |
| `date` | `str \| None` | 要回测的扫描日期（`YYYYMMDD`）；为 `None` 时使用最近一次扫描日期 |

**输出**：`None`（回测机会、交易记录和 summary 写入结果目录）

**Example**：

```python
from core.modules.strategy.strategy_manager import StrategyManager

manager = StrategyManager(is_verbose=True)

# 回测单个策略（自动创建 session）
manager.simulate(strategy_name="my_strategy")
```

---

## OpportunityEnumerator

### enumerate

**描述**：对指定策略执行**底层机会枚举**（Layer 0）。完整枚举所有可能的投资机会，并按股票写出 CSV 双表（`opportunities.csv` + `targets.csv`）。返回本次枚举的概要信息。

**函数签名**：`OpportunityEnumerator.enumerate(strategy_name: str, start_date: str, end_date: str, stock_list: List[str], max_workers: str | int = "auto") -> List[Dict[str, Any]]`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str` | 策略名称（对应 `userspace/strategies/{strategy_name}`） |
| `start_date` | `str` | 开始日期（`YYYYMMDD`），用于 metadata 记录与上层消费 |
| `end_date` | `str` | 结束日期（`YYYYMMDD`） |
| `stock_list` | `List[str]` | 股票 ID 列表 |
| `max_workers` | `str \| int` | 最大并行数；`"auto"` 为自动决策，其它为手动指定 |

**输出**：`List[Dict[str, Any]]` —— 每个元素为一次枚举运行的 summary（包含版本号、机会数量等）

**Example**：

```python
from core.modules.strategy.components.opportunity_enumerator.opportunity_enumerator import OpportunityEnumerator

summary_list = OpportunityEnumerator.enumerate(
    strategy_name="my_strategy",
    start_date="20230101",
    end_date="20231231",
    stock_list=["000001.SZ", "000002.SZ"],
    max_workers="auto",
)

for summary in summary_list:
    print(summary["version_id"], summary["opportunity_count"])
```

---

## PriceFactorSimulator

### PriceFactorSimulator（构造函数）

**描述**：创建价格因子模拟器（Layer 2）。根据策略 settings 构建模拟配置，并与枚举器输出版本协同工作，用于验证策略在**价格层面**的效果。

**函数签名**：`PriceFactorSimulator(is_verbose: bool = False)`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `is_verbose` | `bool` | 是否输出详细日志，默认 `False` |

**输出**：无（构造实例）

**Example**：

```python
from core.modules.strategy.components.simulator.price_factor import PriceFactorSimulator

simulator = PriceFactorSimulator(is_verbose=True)
```

---

### run

**描述**：对指定策略执行**价格因子模拟**。读取枚举器输出版本（枚举输出结果），对每只股票构建模拟作业并多进程执行，输出轻量级 summary 结果和版本目录。

**函数签名**：`PriceFactorSimulator.run(strategy_name: str) -> Dict[str, Any]`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str` | 策略名称（对应 `userspace/strategies/{strategy_name}`） |

**输出**：`Dict[str, Any]` —— 模拟结果摘要（包含版本号、统计信息等）

**Example**：

```python
from core.modules.strategy.components.simulator.price_factor import PriceFactorSimulator

simulator = PriceFactorSimulator(is_verbose=True)
summary = simulator.run(strategy_name="my_strategy")
print(summary)
```

---

## CapitalAllocationSimulator

### CapitalAllocationSimulator（构造函数）

**描述**：创建资金分配模拟器（Layer 3）。在 PriceFactorSimulator 验证价格因子有效后，基于 枚举输出机会流和资金管理配置，模拟真实资金约束下的交易与仓位分配。

**函数签名**：`CapitalAllocationSimulator(is_verbose: bool = False)`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `is_verbose` | `bool` | 是否输出详细日志，默认 `False` |

**输出**：无（构造实例）

**Example**：

```python
from core.modules.strategy.components.simulator.capital_allocation import CapitalAllocationSimulator

simulator = CapitalAllocationSimulator(is_verbose=True)
```

---

### run

**描述**：对指定策略执行**资金分配模拟**。读取枚举器输出版本中生成的事件流（枚举输出结果），结合资金、手续费和分配策略配置，生成交易记录与权益曲线。

**函数签名**：`CapitalAllocationSimulator.run(strategy_name: str) -> Dict[str, Any]`

**参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `strategy_name` | `str` | 策略名称（对应 `userspace/strategies/{strategy_name}`） |

**输出**：`Dict[str, Any]` —— 模拟结果摘要（包含版本号、交易统计、权益曲线路径等）

**Example**：

```python
from core.modules.strategy.components.simulator.capital_allocation import CapitalAllocationSimulator

simulator = CapitalAllocationSimulator(is_verbose=True)
summary = simulator.run(strategy_name="my_strategy")
print(summary)
```

---

## 相关文档

- [Strategy 架构](./architecture.md)
- [Strategy 概览](./overview.md)
- [Scanner 设计文档](../../../../core/modules/strategy/docs/SCANNER_DESIGN.md)

