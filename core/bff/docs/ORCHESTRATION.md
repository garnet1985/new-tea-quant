# BFF 路由编排索引

**版本：** 0.2.0

HTTP 前缀一律为 `/api`（见 `core/bff/app.py`）。契约细节优先看 FED 各页 `API.md`（有则）；实现步骤看 [`routes/`](routes/)。

| 域 | Blueprint 包 | 编排文档 | 实现 |
|----|--------------|----------|------|
| platform / health | `APIs/platform/health` | — | `core.system.get_version` |
| platform / runtime | `APIs/platform/runtime` | Tag T1-00 引用 | `infra.system_actions` pipeline lease |
| platform / setup | `APIs/platform/setup` | — | `setup` meta + `SetupRuntimeManager` |
| platform / app_settings | `APIs/platform/app_settings` | — | `app_settings/service.py`（含 trace） |
| data / sources | `APIs/data/sources` | [`routes/data_sources.md`](routes/data_sources.md) | BFF helpers + implementer |
| data / contracts | `APIs/data/contracts` | [`routes/data_contracts.md`](routes/data_contracts.md) | BFF helpers + implementer |
| strategy | `APIs/strategy`（`routes/` + `helpers/`） | [`routes/strategy.md`](routes/strategy.md) | core `PipelineProgress` / `ScanJob`；BFF snapshots + runner 薄壳 |
| tag | `APIs/tag`（`routes/` + `helpers/`） | [`routes/tag.md`](routes/tag.md) | core `TagRunProgress`；BFF catalog + runner 薄壳 |

分组准则见 [`GROUPING.md`](GROUPING.md)、架构见 [`ARCHITECTURE.md`](ARCHITECTURE.md)。
