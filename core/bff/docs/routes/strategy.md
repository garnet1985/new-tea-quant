# 策略域 BFF：`routes/` 编排

**版本：** 0.1.0

FED 侧尚无独立 `strategy*/API.md`（原 `strategyWorkbenchPage/mocks/API.md` 已移除）；本文件为策略 HTTP 路由与编排的当前 SSOT，字段语义以工作台 / 设计页前端消费为准。

## 目录

```text
core/bff/APIs/strategy/
  api_base.py               # strategy_api_bp, API_BASE_PATH
  helpers/                  # snapshots / report_hydrate / formatting …
  routes/
    catalog/                # V2-02
    package/                # V2-13 … 15
    report/                 # V2-07*
    settings/               # V2-04 / V2-09
    version/                # V2-01/03/08 + cache + pin
    folder/                 # 打开策略目录
    runner/                 # V2-05/06* + scan 薄壳；进度落盘在 strategy core
```

## 原则

- **路径**：有 target 时统一为 `/v1/strategy/{strategy_key_or_name}/…`（``meta.key`` 或 path name，可多段）；无 target 的全局资源（catalog、settings 选项、package import、全表 cache、scan/context）不加 strategy 段。
- **共用类方法**：``DiscoveryService.resolve_strategy_path``、``WorkbenchVersionId.parse``、``WorkbenchStep.try_parse``（挂在类上，不单独 export 函数）。
- **routes/<area>/routes.py**：解析 HTTP → `impl.lazy_load()` → `ok` / `error`。
- **routes/<area>/implementer.py**：领域编排 / DTO；lazy-import strategy core 与本包 helpers。
- **Snapshot**：前端概念（多 version settings）；读模型在 ``helpers/workbench_snapshots``（磁盘 registry）。后端 run 经 ``Strategy.simulate`` 写 ``simulations/{vid}/``，BFF 不做 cache 命中判断。
- 不再保留独立的 ``cache`` 路由模块；磁盘 version 清理与固定挂在 **version**。
- Version / 指纹规则见 ``modules.strategy`` [VERSIONING.md](../../modules/strategy/docs/VERSIONING.md)。
- BFF 不做缓存命中判断。
- 工作台三步 ``enum | price | portfolio`` 与核心共用 ``WorkbenchStep``（``core.modules.strategy.contracts``）。

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
| V2-07 | GET | `/v1/strategy/<strategy_key_or_name>/report/<step>/<version_id>` | `routes/report/` — 含 ``report`` + ``analysis``（``enabled`` / ``available`` / ``facts`` / ``conclusion``）。portfolio ``capitalMetrics`` 另附完整 ``eventCurveLabels/Values``、``eventDrawdownValues``、``tradeEvents``（买卖点；来自 ``equity_curve.json`` / ``trades.json``，非 ≤80 抽稀序列） |
| V2-07b | GET | `/v1/strategy/<strategy_key_or_name>/report/<step>/<version_id>/ref` | `routes/report/` |
| V2-07c | GET | `/v1/strategy/<strategy_key_or_name>/report/<step>/<version_id>/stock/<stock_id>` | `routes/report/` |
| V2-08 | GET | `/v1/strategy/<strategy_key_or_name>/version/<version_id>` | `routes/version/` |
| occupancy | GET | `/v1/strategy/<strategy_key_or_name>/settings/current` | `routes/settings/` — 当前 `settings.py` 字节 rev + 正文 + execute 投影 |
| persist | POST | `/v1/strategy/<strategy_key_or_name>/settings/persist` | `routes/settings/` — 草稿写回；`If-Match` / `settings_rev`，冲突 409 |
| V2-09 | POST | `/v1/strategy/<strategy_key_or_name>/settings/apply/<version_id>` | `routes/settings/` — 恢复历史 version 配置到 ``settings.py``；同样 If-Match |
| V2-11 | DELETE | `/v1/strategy/version/cache` | `routes/version/` |
| V2-12 | DELETE | `/v1/strategy/<strategy_key_or_name>/version/<version_id>/cache` | `routes/version/` |
| pin | POST | `/v1/strategy/<strategy_key_or_name>/version/<version_id>/pin` | `routes/version/` — 固定（只改 `meta.json` 根上 `pinned`） |
| pin | DELETE | `/v1/strategy/<strategy_key_or_name>/version/<version_id>/pin` | `routes/version/` — 取消固定 |
| folder | POST | `/v1/strategy/<strategy_key_or_name>/folder/reveal` | `routes/folder/` — 本机打开策略目录 |
| V2-13 | GET | `/v1/strategy/<strategy_key_or_name>/package/export` | `routes/package/` |
| V2-14 | POST | `/v1/strategy/package/import/preview` | `routes/package/` |
| V2-15 | POST | `/v1/strategy/package/import` | `routes/package/` |
| scan | GET | `/v1/strategy/scan/context` | `routes/runner/` |
| scan | GET/POST | `/v1/strategy/<strategy_key_or_name>/scan` | `routes/runner/` |
| scan | GET | `/v1/strategy/<strategy_key_or_name>/scan/progress` | `routes/runner/` |

**未注册**：V2-10 `versions/range`。
