# 策略模块（Strategy Module）

`core/modules/strategy` 为策略运行时实现的主入口目录。

当前结构：

- `strategy_manager.py`：顶层扫描 / 模拟编排
- `engines/`：扫描器、模拟器、分析器等引擎
- `services/`：跨引擎共享能力（发现、数据、产物、校验、注入等）
- `engines/shared/`：多引擎共用的数据结构与辅助函数

迁移说明：

- 旧版 `strategy1` 已移除。
- 运行时流程统一围绕已发现的 `DiscoveredStrategy` 与各引擎内实现。

详细设计与契约见 **`docs/`** 目录。
