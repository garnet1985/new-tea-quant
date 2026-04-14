# 组件：OpportunityService（机会 JSON 服务）

**版本：** `0.2.0`

## 职责

- 管理 **`StrategyManager.scan` / `simulate`** 产出的 **JSON** 文件：按日期或 **`session_id`** 分目录存储机会列表、summary、配置快照。
- 路径根源于 **`PathManager.strategy_scan_results`**、**`PathManager.strategy_results`** 等约定。

## 主要方法（概念）

- **扫描**：`save_scan_config` / `save_scan_opportunities` / `save_scan_summary`
- **模拟**：`save_simulate_config` / `save_simulate_opportunities` / `save_simulate_summary`
- 读取与合并历史文件的方法见源码（供 CLI 或 Adapter 使用）。

## 与枚举 CSV 的区别

- **OpportunityEnumerator** 使用 **CSV双表** 服务 Layer 2/3；**OpportunityService** 服务 **Scanner/Simulate（Manager路径）** 的 **JSON** 工件，二者目录与格式不同。
