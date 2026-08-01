# BFF 路由编排索引

HTTP 前缀一律为 `/api`（见 `core/bff/app.py`）。契约细节以 FED `API.md` 与各域 `ROUTES_ORCHESTRATION.md` 为准。

| 域 | Blueprint 包 | 编排文档 | 实现 |
|----|--------------|----------|------|
| platform / health | `APIs/platform/health` | — | `core.system.get_version` |
| platform / runtime | `APIs/platform/runtime` | Tag T1-00 引用 | `infra.system_actions…pipeline_lease` |
| platform / setup | `APIs/platform/setup` | — | `setup` meta + `SetupRuntimeManager` |
| platform / app_settings | `APIs/platform/app_settings` | — | `app_settings/service.py` + `database_defaults` |
| data / sources | `APIs/data/sources` | [`sources/ROUTES_ORCHESTRATION.md`](APIs/data/sources/ROUTES_ORCHESTRATION.md) | BFF helpers + implementer |
| data / contracts | `APIs/data/contracts` | [`contracts/ROUTES_ORCHESTRATION.md`](APIs/data/contracts/ROUTES_ORCHESTRATION.md) | BFF helpers + implementer |
| strategy | `APIs/strategy`（`routes/` + `helpers/`） | [`strategy/ROUTES_ORCHESTRATION.md`](APIs/strategy/ROUTES_ORCHESTRATION.md) | core `PipelineProgress` / `ScanJob`；BFF snapshots + runner 薄壳 |
| tag | `APIs/tag`（`routes/` + `helpers/`） | [`tag/ROUTES_ORCHESTRATION.md`](APIs/tag/ROUTES_ORCHESTRATION.md) | core `TagRunProgress`；BFF catalog + runner 薄壳 |

分组准则见 [`GROUPING.md`](GROUPING.md)、[`README.md`](README.md)。
