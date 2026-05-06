# 策略工作台 BFF：`routes` 编排层约定

契约与语义以 [`core/ui/fed/src/pages/strategyWorkbenchPage/API.md`](../../../../fed/src/pages/strategyWorkbenchPage/API.md) 为准。

## HTTP 前缀

- 蓝图注册：`url_prefix='/api'`（`core/ui/bff/app.py`）。
- 路由模块：`core/ui/bff/APIs/strategy_workbench/routes.py`。
- **完整 URL** = **`/api`** + 路由表中路径（例如 **`GET /api/v1/strategy/<strategy_name>/version/latest`**）。

## 原则

- **编排层（routes）**：解析输入、调用 launcher、组装信封 `ok` / `error`。
- **实现层**：业务在 `core/modules/strategy/services/launcher/` 等；BFF 不做缓存命中判断。

## V2 路由 × 编排步骤（已实现）

| V2 | 方法 | 路由（文件内声明） | 编排摘要 |
|----|------|-------------------|----------|
| V2-01 | GET | `/v1/strategy/<strategy_name>/version/latest` | `fetch_latest_workbench_snapshot` → `workbench_snapshot_to_message` → `ok` |
| V2-02 | GET | `/v1/strategies/list` | `pagination_params` → `fetch_discovered_strategies_page` → `ok({items,total,page,limit})` |
| V2-03 | GET | `/v1/strategy/<strategy_name>/versions` | `fetch_strategy_versions_dropdown` → `ok({items})` |
| V2-04 | GET | `/v1/strategy/settings/capital-allocation-strategies` | `items_capital_allocation_strategies()` → `ok({items})` |
| V2-04 | GET | `/v1/strategy/settings/sampling-strategies` | `items_sampling_strategies()` → `ok({items})` |
| V2-05 | POST | `/v1/strategy/<strategy_name>/<step>/run` | `json_payload` → `trigger_workbench_step_run` → `ok` |
| V2-06 | GET | `/v1/strategy/<strategy_name>/<step>/progress` | query `job_id` → `get_step_progress` → `ok` / 404 |
| V2-07 | GET | `/v1/strategy/<strategy_name>/<step>/report` | query `version_id` → `build_step_report_message` → `ok` / 404 |
| V2-08 | GET | `/v1/strategy/<strategy_name>/version/<version_id>` | `fetch_workbench_snapshot_by_snapshot_id` → `workbench_snapshot_to_message` → `ok` |
| V2-09 | POST | `/v1/strategy/<strategy_name>/apply-settings/<version_id>` | `json_payload`（可选 `pretty`）→ `apply_workbench_snapshot_settings_to_userspace` → `ok` |

**未注册**：**V2-10** `versions/range`（契约见 API.md；实现待定）。

错误分支：各 handler 内 `error(...)`；校验失败多为 400，资源缺失 404，写盘/存储异常按 handler 映射。
