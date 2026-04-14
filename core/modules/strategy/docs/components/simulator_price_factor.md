# 组件：PriceFactorSimulator（价格因子模拟）

**版本：** `0.2.0`

## 职责

- **Layer 2**：在**无组合资金约束**前提下，基于 **枚举器 CSV输出** 复现或简化计算每笔机会的持有期收益（ROI 等），用于快速检验信号质量。
- **多进程**：按股票拆分 **`PriceFactorSimulatorWorker`**，与枚举器类似的 **`ProcessWorker`** 模式。

## 主要类型

| 路径 | 说明 |
|------|------|
| `price_factor_simulator.py` | **`PriceFactorSimulator.run(strategy_name)`**：加载 settings、解析/自动生成枚举版本、创建模拟器版本目录、构建 jobs、汇总、可选 **Analyzer** |
| `price_factor_simulator.py`（Worker类） | 子进程：读单股枚举片段、撮合目标价、写该股结果 JSON |
| `investment_builder.py` / `result_aggregator.py` / `stock_summary_builder.py` | 投资对象构建与会话级汇总 |
| `result_presenter.py` | 控制台展示 |
| `helpers.py` | 数值与 JSON 编码等工具 |

## 数据依赖

- **输入**：某次 **`OpportunityEnumerator`** 输出版本目录下的分股文件（具体布局由 **`DataLoader`** / **`ResultPathManager`** 约定）。
- **输出**：`VersionManager.create_price_factor_version` 创建的模拟器版本目录下的结果与 `session` 级 summary；缺失枚举版本时可 **自动触发** 一次枚举。

## 公开入口

- **`PriceFactorSimulator(...).run(strategy_name: str) -> Dict[str, Any]`**
