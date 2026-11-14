# data.json 键职责

路径：

- 默认：`core/default_config/data.json`
- 覆盖：`userspace/system/config/data.json`（深度合并）

---

## 日期相关（核心）

| 键 | 默认 | 负责 | 责任边界 |
|----|------|--------|----------|
| `default_start_date` | `20080101` | **全局历史地板**：包括策略回测，标签计算，数据获取 | `null` |
| `assumed_latest_completed_trading_date` | `null` | **假定的最新已完成交易日**（用于全局覆盖回测或者扫描需要的最新日期） | **不决定数据获取的截止日期** |

```text
数据为空的时候 获取数据的默认起点时间是 default_start_date（默认开始时间）
获取数据默认的时间结束点是 真实交易日历的最新日期（不使用假设的最新完成的交易日）
机会扫描的严格模式使用真实完成交易日，演示模式是使用假设的最新完成交易日
```

---

## `default_start_date`

| 用途 | 入口 |
|------|------|
| 空表 / force / 新实体 renew 起点 | `RenewCommonHelper.get_default_date_range` 等 |
| 策略回测未写 `start` | `simulation_settings/execution.resolve_period` |
| Tag 未写 `start` | `tag/.../calculation_settings.resolve_period` |
| Timeline 合法窗下界 | `backtest_engine/.../timeline.system_bounds` |
| 无界查询下界 | `Utils.date.get_query_date_range_min` |
| 复权 CSV 对齐 | `adj_factor_events/csv_import` |

---

## `assumed_latest_completed_trading_date`

- `null`：`CalendarService.get_latest_completed_trading_date` 走日历 / 网络 / K 线 fallback。
- 非空 YYYYMMDD：该 API **直接返回该日**（演示包/扫描假定世界停在这天）。

影响（**非 renew 截止**）：

| 用途 | 入口 |
|------|------|
| 计算侧「最新已完成交易日」 | `CalendarService.get_latest_completed_trading_date` |
| 回测 / Tag 默认终点 | 经 `latest_completed` 间接 |
| Timeline 上界 | `system_bounds` |
| Scanner 非严格锚点 | `ScanDateResolver` |
| 新鲜度 UI 展示已配置假定日 | `freshness_probe` |
| 复权 CSV 事件日截断 | `adj_factor_events/csv_import` |

**为何需要：** 演示数据钉窗时，扫描/回测需要一个假定的「今天」。  
**不是：** 会员下载权限，也不是 renew 追新的截止日。

---

## 其他键

| 键 | 说明 |
|----|------|
| `default_market_profile_key` | 默认市场 profile |
| `use_sample_stock_list` | 开发样本股数量（后门） |
| `retention.*` | 仿真/scan 产物保留 |
| `decimal_places.*` | 展示/复权小数位 |
| `benchmark_stock_index_list` | 基准指数元数据 |

---

## 相关代码

- `ProjectContext.config.get_default_start_date` / `get_assumed_latest_completed_trading_date`
- renew：`renew_progress.sync_market_day` / `resolve_uptodate_day`；context 注入见 `DataSourceHooks.on_prepare_context`
- 日历权威（可读 assumed）：`CalendarService.get_latest_completed_trading_date`
