# 组件：OpportunityEnumerator（机会枚举器）

**版本：** `0.2.0`

## 职责

- **完整枚举**：在给定股票集合与日期区间内，按策略逻辑逐日扫描，**不**采用「单持仓主线」剪枝；产出可供 Layer 2/3 复用的**事实表**。
- **高性能落盘**：`opportunities.csv` + `targets.csv`（双表），适合万级～十万级行数。
- **并行**：主进程组装任务，子进程执行 **`OpportunityEnumeratorWorker`**（按需查数，带契约缓存）。

## 主要类型

| 路径 | 说明 |
|------|------|
| `opportunity_enumerator.py` | **`OpportunityEnumerator.enumerate(...)`** 静态入口：加载 **`StrategySettings`**、构建 jobs、`ProcessWorker`、汇总与版本目录写入 |
| `enumerator_worker.py` | 子进程 Worker：按 payload 执行单日/单股枚举逻辑（与策略 Worker 数据路径对齐） |
| `enumerator_settings.py` | **`OpportunityEnumeratorSettings`**：`from_base` / `from_raw` 从整包 settings 抽取枚举块 |
| `performance_profiler.py` | 枚举与模拟共用性能埋点 |

## 与上下游关系

- **输入**：`userspace/strategies/<name>/settings.py` 中的 **`settings`** 字典（经 **`StrategySettings`** 建模）。
- **输出**：`PathManager` 下策略结果树中的 **枚举版本目录**（与 **`VersionManager`** 协同）；供 **`PriceFactorSimulator` / `CapitalAllocationSimulator`** 通过 **`DataLoader`** 读取。
- **自动枚举**：模拟器在缺少依赖版本时可调用 **`OpportunityEnumerator.enumerate`** 预跑一轮（见模拟器文档）。

## 相关代码入口

- `OpportunityEnumerator.enumerate(strategy_name, start_date, end_date, stock_list, max_workers=..., base_settings=...)`
