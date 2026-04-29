# 组件：SimulatorHooksDispatcher（模拟器钩子）

**版本：** `0.2.0`

## 职责

- 为 **`PriceFactorSimulator`** 与 **`CapitalAllocationSimulator`** 提供**统一**的钩子调度入口，调用用户 **`BaseStrategyWorker`** 子类上可选实现的 **模拟阶段钩子**（如模拟开始/结束、按配置切片回调等，具体见 **`base_strategy_worker.py`** 中 `on_*` 与 simulator 相关段落）。

## 主要文件

| 路径 | 说明 |
|------|------|
| `simulator/base/simulator_hooks_dispatcher.py` | **`SimulatorHooksDispatcher`**：按策略名加载 worker 模块，解析类并分发到各钩子方法 |

## 说明

- 钩子失败策略由模拟器主流程定义（通常**不应**阻断主结果落盘）；实现时保持轻量、无副作用或自行捕获异常。
