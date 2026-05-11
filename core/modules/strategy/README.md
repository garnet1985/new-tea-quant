# 策略模块（Strategy Module）

`core/modules/strategy` 为策略运行时实现的主入口目录。

当前结构（Flow 形式组织）：

- `strategy_manager.py`：顶层入口，对外提供 scan / simulate / analyze 等主流程编排
- `engines/`：按引擎域拆分实现，核心以 **Flow** 为中心组织（而非散落的函数式入口）
  - `scanner/`：实时扫描 Flow（针对最新一日/窗口，产出 active opportunities）
  - `enumerator/`：机会枚举 Flow（产出 opportunities + targets，作为底层事实表/缓存层）
  - `simulator/price_factor/`：价格因子回测 Flow（快速验证价格层 alpha）
  - `simulator/capital_allocation/`：带资金约束回测 Flow（更接近真实交易过程）
  - `analyzer/`：结果分析与摘要 Flow（结构化汇总与指标）
  - `shared/`：多引擎共用的数据结构与辅助函数
- `services/`：跨 Flow 的共享能力（发现/配置、数据读写、缓存、产物落地、校验、launcher 编排等）

迁移说明：

- 旧版 `strategy1` 已移除。
- 运行时流程统一围绕已发现的 `DiscoveredStrategy`，并在各引擎域内以 Flow 组织实现。

详细设计与契约见 **`docs/`** 目录。
