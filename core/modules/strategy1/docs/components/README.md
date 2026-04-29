# Strategy 组件文档索引

**版本：** `0.2.0`

各子目录职责细化说明（与 `../ARCHITECTURE.md` 总览配合阅读）。

| 文档 | 说明 |
|------|------|
| [opportunity_enumerator.md](opportunity_enumerator.md) | Layer 0：全市场机会枚举、CSV 双表、多进程 Worker |
| [scanner.md](scanner.md) | Layer 1：扫描日解析、缓存、多进程扫描、Adapter 分发 |
| [simulator_price_factor.md](simulator_price_factor.md) | Layer 2：基于枚举输出的价格层模拟（多进程） |
| [simulator_capital_allocation.md](simulator_capital_allocation.md) | Layer 3：事件驱动、账户与费用、单进程模拟 |
| [simulator_hooks.md](simulator_hooks.md) | 模拟器共用：`SimulatorHooksDispatcher` 与用户钩子 |
| [data_management.md](data_management.md) | `StrategyDataManager`：契约、指标、DataCursor、as_of 数据 |
| [analyzer.md](analyzer.md) | 模拟结束后可选统计 / ML 分析报告 |
| [opportunity_service.md](opportunity_service.md) | 扫描与 simulate 结果的 JSON 落盘与路径约定 |
| [session_manager.md](session_manager.md) | `session_id` 与 `meta.json` |

返回 [模块入口 README](../../README.md)中的「相关文档」。
