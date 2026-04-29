# 组件：Scanner（扫描层）

**版本：** `0.2.0`

## 职责

- **Layer 1**：面向「最新交易日」的机会发现；结果体量小于全量枚举，通常为 **JSON** 机会列表。
- 整合 **扫描日解析**、**本地缓存**、**多进程** 调用用户 **`BaseStrategyWorker`**，以及 **Adapter** 分发（通知、控制台等）。

## 子模块

| 文件 | 说明 |
|------|------|
| `scanner.py` | **`Scanner`** 数据类：组装 `ScanDateResolver`、`ScanCacheManager`、`AdapterDispatcher`，`scan()` 全流程 |
| `scan_date_resolver.py` | 结合交易日历解析实际扫描日、股票全集或子集 |
| `scan_cache_manager.py` | 按策略与日期缓存扫描结果（路径在 `PathManager` 约定下） |
| `adapter_dispatcher.py` | 按配置名称加载 **`modules.adapter`** 中机会适配器并分发 |

## 与 StrategyManager 的关系

- **`StrategyManager.scan`**：按 **`StrategyInfo`** 构建 Job（**`JobBuilderHelper.build_scan_jobs`**），**`ProcessWorker`**调度 **`StrategyManager._execute_single_job`** → 用户 **`BaseStrategyWorker.run()`**，结果经 **`OpportunityService`** 写入 `scan/`。
- **`Scanner`**：可选的一体化入口（自行解析扫描日与全市场股票列表、写缓存、调 Adapters）；配置来自 **`StrategyDiscoveryHelper.load_strategy`** 得到的整包 **`StrategySettings`**，Job 中 **`settings`** 为完整字典，与子进程 **`BaseStrategyWorker`** 约定一致。

## 配置

-扫描相关字段在整包 settings 的 **`scanner`** 块（见 **`data_classes/strategy_settings/scanner_settings.py`**）：`max_workers`、`adapters`、`watch_list`、`max_cache_days`、`use_strict_previous_trading_day` 等。
