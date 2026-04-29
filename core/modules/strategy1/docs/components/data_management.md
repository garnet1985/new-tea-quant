# 组件：StrategyDataManager（策略数据管理）

**版本：** `0.2.0`

## 职责

- 在 **`BaseStrategyWorker`** 子进程中，按 **`StrategySettings.data`** 声明装载 **DataContract**、可选 **指标**（**`IndicatorService`**）、以及 **DataCursor**。
- 提供 **Scanner** 与 **Simulate** 两条加载路径：**最新窗口** vs **历史区间**；对外统一 **`get_data_until(as_of)`** 语义，避免未来数据泄露。

## 主要文件

| 路径 | 说明 |
|------|------|
| `strategy_data_manager.py` | **`StrategyDataManager`**：`load_latest_data` / `load_historical_data`、`get_loaded_data`、`get_data_until`、`get_klines` 等 |

## 依赖模块

- **`modules.data_contract`**：契约发行与缓存
- **`modules.data_cursor`**：**`DataCursorManager`** 前缀视图
- **`modules.indicator`**：按 settings 预计算指标列并挂到 kline 行上

## 与 BaseStrategyWorker

- **`BaseStrategyWorker`** 在 **`__init__`** 中构造 **`StrategyDataManager`**；**`scan_opportunity`** / **`scan_opportunity_with_data`** 收到的 **`data`** 字典结构与 **`get_data_until`** 输出一致。
