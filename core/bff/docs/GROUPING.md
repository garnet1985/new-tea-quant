# BFF 业务域分组

HTTP 路径与响应契约以 FED 各页 `API.md`（有则）及本目录 [`routes/`](routes/) 为准；目录与 blueprint 按业务域划分。

## 当前域布局

| 域 | 路径 | URL |
|----|------|-----|
| platform | `APIs/platform/health` | `/api/health` |
| platform | `APIs/platform/runtime` | `/api/v1/runtime/pipeline` |
| platform | `APIs/platform/setup` | `/api/v1/setup/*` |
| platform | `APIs/platform/app_settings` | `/api/v1/settings/*`（含 database / data / cache / **trace**） |
| data | `APIs/data/sources` | `/api/v1/data-sources/*` |
| data | `APIs/data/contracts` | `/api/v1/data-contracts/*` |
| strategy | `APIs/strategy/`（`routes/` + `helpers/`） | `/api/v1/strategy/*` |
| tag | `APIs/tag/`（`routes/` + `helpers/`） | `/api/v1/tags/*`、`/api/v1/tag/*` |

## settings 消歧

| 名称 | 归属 | URL |
|------|------|-----|
| **app_settings** | platform | `/api/v1/settings/database`、`/data`、`/cache/clear`、`/trace` |
| **simulation_options** | strategy | `/api/v1/strategy/settings/*`（资本配置、采样、仿真模板等） |

## 业务域边界

| 域 | 含 | 不含 |
|----|----|------|
| **strategy** | workbench + scan + package + strategy catalog | app 级 settings |
| **tag** | tag list + tag run | runtime/pipeline（平台能力） |
| **data** | data_source + data_contract 目录/新鲜度 | — |
| **platform** | health + runtime/pipeline + setup + app settings/cache/trace | strategy 仿真 options |

## 实现下沉（已完成）

| 域 | UI catalog / snapshot | 异步进度 / job |
|----|----------------------|----------------|
| strategy | BFF `helpers/`（snapshots、hydrate） | core `PipelineProgress` / `ScanJob`；BFF runner 薄壳 |
| tag | BFF `helpers/tag_catalog` | core `TagRunProgress`；BFF `routes/runner/tag_run` |
| data_contract | BFF `helpers/contract_catalog` | — |
| data_source | BFF `helpers/source_catalog` | — |

`modules/*/launcher` 与 `bff/support` 业务逻辑已删除 / 废弃；勿再写入 `support/`。
