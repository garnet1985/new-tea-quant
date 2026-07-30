# 策略域 BFF：`routes/` 编排层

契约与语义以 [`core/ui/fed/src/pages/strategyWorkbenchPage/mocks/API.md`](../../../ui/fed/src/pages/strategyWorkbenchPage/mocks/API.md) 为准。

## 目录

```text
core/bff/APIs/strategy/
  api_base.py               # strategy_api_bp, API_BASE_PATH
  helpers/                  # formatting / params / query / …
  routes/
    catalog/                # V2-02
    package/                # V2-13 … 15
    report/                 # V2-07*
    settings/               # V2-04 / V2-09
    version/                # V2-01/03/08 + cache
    runner/                 # V2-05/06* + scan
  helpers/
```

## 原则

- **路径**：有 target 时统一为 `/v1/strategy/{strategy_key_or_name}/…`（``meta.key`` 或 path name，可多段）；无 target 的全局资源（catalog、settings 选项、package import、全表 cache、scan/context）不加 strategy 段。
- **共用类方法**：``DiscoveryService.resolve_strategy_path``、``WorkbenchVersionId.parse``、``WorkbenchStep.try_parse``（挂在类上，不单独 export 函数）。
- **routes/<area>/routes.py**：解析 HTTP → `impl.lazy_load()` → `ok` / `error`。
- **routes/<area>/implementer.py**：领域编排 / DTO；可 lazy-import strategy core / launcher。
- 不再保留独立的 ``cache`` 路由模块；快照 DbCache 清理挂在 **version**。
- BFF 不做缓存命中判断。
- 工作台三步 ``enum | price | portfolio`` 与核心共用 ``WorkbenchStep``（``core.modules.strategy.core.enums``）。

## V2 路由 × 文件

| V2 | 方法 | 路由 | 文件 |
|----|------|------|------|
| V2-01 | GET | `/v1/strategy/<strategy_key_or_name>/version/latest` | `routes/version/` |
| V2-02 | GET | `/v1/strategy/catalog/<page>/<limit>` | `routes/catalog/` |
| V2-03 | GET | `/v1/strategy/<strategy_key_or_name>/versions` | `routes/version/` |
| V2-04 | GET | `/v1/strategy/settings/{portfolio,sampling,simulation,risk-control,market-rules}` | `routes/settings/` |
| V2-05 | POST | `/v1/strategy/<strategy_key_or_name>/<step>/run` | `routes/runner/` |
| V2-06b | GET | `/v1/strategy/<strategy_key_or_name>/run/progress` | `routes/runner/` |
| V2-06 | GET | `/v1/strategy/<strategy_key_or_name>/<step>/progress` | `routes/runner/` |
| V2-07 | GET | `/v1/strategy/<strategy_key_or_name>/report/<step>/<version_id>` | `routes/report/` |
| V2-07b | GET | `/v1/strategy/<strategy_key_or_name>/report/<step>/<version_id>/ref` | `routes/report/` |
| V2-07c | GET | `/v1/strategy/<strategy_key_or_name>/report/<step>/<version_id>/stock/<stock_id>` | `routes/report/` |
| V2-08 | GET | `/v1/strategy/<strategy_key_or_name>/version/<version_id>` | `routes/version/` |
| V2-09 | POST | `/v1/strategy/<strategy_key_or_name>/settings/apply/<version_id>` | `routes/settings/` |
| V2-11 | DELETE | `/v1/strategy/version/cache` | `routes/version/` |
| V2-12 | DELETE | `/v1/strategy/<strategy_key_or_name>/version/<version_id>/cache` | `routes/version/` |
| V2-13 | GET | `/v1/strategy/<strategy_key_or_name>/package/export` | `routes/package/` |
| V2-14 | POST | `/v1/strategy/package/import/preview` | `routes/package/` |
| V2-15 | POST | `/v1/strategy/package/import` | `routes/package/` |
| scan | GET | `/v1/strategy/scan/context` | `routes/runner/` |
| scan | GET/POST | `/v1/strategy/<strategy_key_or_name>/scan` | `routes/runner/` |
| scan | GET | `/v1/strategy/<strategy_key_or_name>/scan/progress` | `routes/runner/` |

**未注册**：V2-10 `versions/range`。
