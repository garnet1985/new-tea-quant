# 策略域 BFF：`routes/` 编排层

契约与语义以 [`core/ui/fed/src/pages/strategyWorkbenchPage/mocks/API.md`](../../../ui/fed/src/pages/strategyWorkbenchPage/mocks/API.md) 为准。

## 目录

```text
core/bff/APIs/strategy/
  api_base.py               # strategy_api_bp, API_BASE_PATH
  stack.py                  # 懒加载 launcher（version / runner / settings 仍用）
  routes/
    catalog/                # V2-02
    package/                # V2-13 … 15
    report/                 # V2-07* + 原 V2-11/12 cache
    version/ | runner/ | settings/  # stubs / 迁移中
  helpers/
```

## 原则

- **routes/<area>/routes.py**：解析 HTTP → `impl.lazy_load()` → `ok` / `error`。
- **routes/<area>/implementer.py**：领域编排 / DTO；可 lazy-import strategy core。
- 不再保留独立的 ``cache`` 路由模块；快照 DbCache 清理挂在 **version**。
- BFF 不做缓存命中判断。
- 工作台三步 ``enum | price | portfolio`` 与核心共用 ``WorkbenchStep``（``core.modules.strategy.core.enums``）。

## V2 路由 × 文件

| V2 | 方法 | 路由 | 文件 |
|----|------|------|------|
| V2-01 | GET | `/v1/strategy/<name>/version/latest` | `routes/version/`（迁移中） |
| V2-02 | GET | `/v1/strategy/catalog/<page>/<limit>` | `routes/catalog/` |
| V2-03 | GET | `/v1/strategy/<name>/versions` | `routes/version/` |
| V2-04 | GET | `/v1/strategy/settings/*` | `routes/settings/` |
| V2-05 | POST | `/v1/strategy/<name>/<step>/run` | `routes/runner/` |
| V2-06b | GET | `/v1/strategy/<name>/run/progress` | `routes/runner/` |
| V2-06 | GET | `/v1/strategy/<name>/<step>/progress` | `routes/runner/` |
| V2-07 | GET | `/v1/strategy/report/<step>/<version_id>/<strategy_key_or_name>` | `routes/report/` |
| V2-07b | GET | `/v1/strategy/report/<step>/<version_id>/ref/<strategy_key_or_name>` | `routes/report/` |
| V2-07c | GET | `/v1/strategy/report/<step>/<version_id>/stock/<stock_id>/<strategy_key_or_name>` | `routes/report/` |
| V2-08 | GET | `/v1/strategy/<name>/version/<id>` | `routes/version/` |
| V2-09 | POST | apply-settings | `routes/version/` |
| V2-11 | DELETE | `/v1/strategy/version/cache` | `routes/version/` |
| V2-12 | DELETE | `/v1/strategy/version/<version_id>/cache/<strategy_key_or_name>` | `routes/version/` |
| V2-13 | GET | `/v1/strategy/package/export/<strategy_key_or_name>` | `routes/package/` |
| V2-14 | POST | `/v1/strategy/package/import/preview` | `routes/package/` |
| V2-15 | POST | `/v1/strategy/package/import` | `routes/package/` |
| scan | * | `/v1/strategy/.../scan*` | `routes/runner/` |

**未注册**：V2-10 `versions/range`。
