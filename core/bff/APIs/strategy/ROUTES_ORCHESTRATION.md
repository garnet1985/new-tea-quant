# 策略域 BFF：`routes/` 编排层

契约与语义以 [`core/ui/fed/src/pages/strategyWorkbenchPage/API.md`](../../../ui/fed/src/pages/strategyWorkbenchPage/API.md) 为准。

## 目录

```text
core/bff/APIs/strategy/
  blueprint.py              # strategy_api_bp
  stack.py                  # 懒加载 launcher / package
  routes/                   # 按关注点拆分的 HTTP handlers
    catalog.py              # V2-02
    snapshots.py            # V2-01 / 03 / 08
    options.py              # V2-04 simulation options
    run.py                  # V2-05 / 06 / 06b
    reports.py              # V2-07*
    apply_settings.py       # V2-09
    cache.py                # V2-11 / 12
    package/                # V2-13 … 15
    scan.py                 # scan context / run / progress
  helpers/                  # DTO / multipart / query（无领域 I/O）
    formatting.py
    execution_panel.py
    package_upload.py
    query.py
```

## 原则

- **routes/**：解析输入、调 `stack.get_stack()`、组装 `ok` / `error`。
- **helpers/**：HTTP/DTO 辅助，不碰 DB / launcher。
- **stack.py**：懒加载 `modules.strategy.launcher` 与 package services。
- BFF 不做缓存命中判断。

## V2 路由 × 文件

| V2 | 方法 | 路由 | 文件 |
|----|------|------|------|
| V2-01 | GET | `/v1/strategy/<name>/version/latest` | `routes/snapshots.py` |
| V2-02 | GET | `/v1/strategy/catalog/<page>/<limit>` | `routes/catalog/` |
| V2-03 | GET | `/v1/strategy/<name>/versions` | `routes/snapshots.py` |
| V2-04 | GET | `/v1/strategy/settings/*` | `routes/options.py` |
| V2-05 | POST | `/v1/strategy/<name>/<step>/run` | `routes/run.py` |
| V2-06b | GET | `/v1/strategy/<name>/run/progress` | `routes/run.py` |
| V2-06 | GET | `/v1/strategy/<name>/<step>/progress` | `routes/run.py` |
| V2-07* | GET | report / report_ref / stock | `routes/reports.py` |
| V2-08 | GET | `/v1/strategy/<name>/version/<id>` | `routes/snapshots.py` |
| V2-09 | POST | apply-settings | `routes/apply_settings.py` |
| V2-11/12 | DELETE | workbench-snapshot-cache | `routes/cache.py` |
| V2-13 | GET | `/v1/strategy/package/export/<strategy_key_or_name>` | `routes/package/` |
| V2-14 | POST | `/v1/strategy/package/import/preview` | `routes/package/` |
| V2-15 | POST | `/v1/strategy/package/import` | `routes/package/` |
| scan | * | `/v1/strategy/.../scan*` | `routes/scan.py` |

**未注册**：V2-10 `versions/range`。
