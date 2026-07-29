# 策略工作台 BFF：`routes` 编排层约定

契约与语义以 [`core/ui/fed/src/pages/strategyWorkbenchPage/API.md`](../../../../fed/src/pages/strategyWorkbenchPage/API.md) 为准。

## HTTP 前缀

- 蓝图注册：`url_prefix='/api'`（`core/ui/bff/app.py`）。
- 路由模块：`core/ui/bff/APIs/strategy_workbench/routes.py`。
- **完整 URL** = **`/api`** + 路由表中路径（例如 **`GET /api/v1/strategy/<strategy_name>/version/latest`**）。

## 原则

- **编排层（routes）**：解析输入、调用后端模块、组装信封 `ok` / `error`。
- **实现层**：工作台经 `modules.strategy.core.bff_support`；策略包经 `modules.strategy.core.services.package`。BFF 不做缓存命中判断。

## V2 路由 × 编排步骤（已实现）

| V2 | 方法 | 路由（文件内声明） | 编排摘要 |
|----|------|-------------------|----------|
| V2-01 | GET | `/v1/strategy/<strategy_name>/version/latest` | `WorkbenchSnapshots.fetch_latest` → `workbench_snapshot_to_message` → `ui_flags` → `ok` |
| V2-02 | GET | `/v1/strategies/list` | `pagination_params` → `StrategyCatalog.fetch_discovered_strategies_page`（新 strategy 模块）→ `ok({items,total,page,limit})` |
| V2-03 | GET | `/v1/strategy/<strategy_name>/versions` | `WorkbenchSnapshots.list_dropdown` → `ok({items})` |
| V2-04 | GET | `/v1/strategy/settings/capital-allocation-strategies` | `StrategySettingsOptions.items_capital_allocation_strategies`（新 portfolio modes）→ `ok({items})` |
| V2-04 | GET | `/v1/strategy/settings/sampling-strategies` | `StrategySettingsOptions.items_sampling_strategies`（含 weighted）→ `ok({items})` |
| V2-04 | GET | `/v1/strategy/settings/simulation-templates` | `StrategySettingsOptions.items_simulation_templates`（defaults=`assumption.tradability` 嵌套）→ `ok({items})` |
| V2-04 | GET | `/v1/strategy/settings/skip-investment-when` | `StrategySettingsOptions.items_skip_enter_when`（语义=`risk_control.skip_enter_when`；URL 兼容保留）→ `ok({items})` |
| V2-04 | GET | `/v1/strategy/settings/market-profiles` | `StrategySettingsOptions.items_market_profiles` → `ok({items})` |
| V2-05 | POST | `/v1/strategy/<strategy_name>/<step>/run` | `WorkbenchRunLauncher.submit`（`Strategy.simulate` 后台线程 + run envelope）→ `ok`（含 **`run_id`**、**`steps`**） |
| V2-06b | GET | `/v1/strategy/<strategy_name>/run/progress` | query `job_id` → `WorkbenchRunLauncher.get_run_progress` → `ok` / 404 |
| V2-06 | GET | `/v1/strategy/<strategy_name>/<step>/progress` | query `job_id` → `WorkbenchRunLauncher.get_step_progress`（由 envelope 派生）→ `ok` / 404 |
| V2-07 | GET | `/v1/strategy/<strategy_name>/<step>/report/<version_id>` | path `version_id` → `WorkbenchReports.build_step_report`（槽位 `enum` / `price_factor` / `portfolio`；缺 metrics 时从 `overall_report.json` hydrate）→ `ok` / 404 |
| V2-07b | GET | `/v1/strategy/<strategy_name>/<step>/report_ref/<version_id>` | path `version_id` → `WorkbenchReports.build_step_report_ref`（`entity_list.json` → ``stock_ref``；排序与分页由前端）→ `ok` / 404 |
| V2-07c | GET | `/v1/strategy/<strategy_name>/<step>/stock/<stock_id>` | query `version_id` → `WorkbenchStockDetail.build`（enum/price；NEW entity CSV + K 线 markers）→ `ok` / 404 |
| V2-08 | GET | `/v1/strategy/<strategy_name>/version/<version_id>` | `parse_version_id` → `WorkbenchSnapshots.fetch_by_version` → `workbench_snapshot_to_message` → `ok` |
| V2-09 | POST | `/v1/strategy/<strategy_name>/apply-settings/<version_id>` | `json_payload`（可选 `pretty`）→ `WorkbenchApplySettings.apply` → `ok` |
| V2-11 | DELETE | `/v1/strategy/workbench-snapshot-cache` | `WorkbenchCacheClear.clear_all` → `ok`（`deleted_count`）/ 503 |
| V2-12 | DELETE | `/v1/strategy/<strategy_name>/version/<version_id>/workbench-snapshot-cache` | `parse_version_id` → `WorkbenchCacheClear.clear_by_version` → `ok` / 404 |
| V2-13 | GET | `/v1/strategy/<strategy_name>/package/export` | `package_stack.export_*`（bundle / single strategy）→ zip |
| V2-14 | POST | `/v1/strategy/package/import/preview` | multipart → `preview_strategy_bundle_import` → `ok` |
| V2-15 | POST | `/v1/strategy/package/import` | multipart → `import_strategy_bundle` → `ok` / 409 |

**未注册**：**V2-10** `versions/range`（契约见 API.md；实现待定）。

错误分支：各 handler 内 `error(...)`；校验失败多为 400，资源缺失 404，写盘/存储异常按 handler 映射。
