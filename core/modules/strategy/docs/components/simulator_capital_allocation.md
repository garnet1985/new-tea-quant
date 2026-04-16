# 组件：CapitalAllocationSimulator（资金分配模拟）

**版本：** `0.2.0`

## 职责

- **Layer 3**：在 **全局账户** 状态下，按时间顺序处理枚举产出的事件流（触发/目标），考虑 **费用、仓位上限、资金分配策略** 等，输出组合级权益与交易流水。
- **单进程**：需维护统一 **`Account`** 与持仓，不适合按股票无脑并行。

## 主要类型

| 路径 | 说明 |
|------|------|
| `capital_allocation_simulator.py` | **`CapitalAllocationSimulator.run(strategy_name)`**：加载配置、构建事件流、按日推进、调用钩子、落盘、**Analyzer** |
| `capital_allocation_simulator_config.py` | **`CapitalAllocationSimulatorConfig.from_settings`**：从 **`StrategySettings`** 抽取资金模拟块 |
| `allocation_strategy.py` | 等资金、等股、Kelly 等分配策略入口 |
| `fee_calculator.py` | 费用模型 |
| `helpers.py` | 事件/账户辅助 |
| `result_presenter.py` | 策略级结果展示 |

## 数据流

- **`DataLoader.build_event_stream`**：从枚举版本目录读取 **CSV**，转为有序 **`Event`** 列表。
- 模拟器内按日期驱动 **`Account`** 与 **`Position`**，与 **`models/event.py`**、**`models/account.py`** 一致。

## 公开入口

- **`CapitalAllocationSimulator(...).run(strategy_name: str) -> Dict[str, Any]`**
