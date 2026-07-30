# BFF 业务域分组对照

HTTP 路径与响应契约保持不变；仅目录与 blueprint 归属按业务域重组。

## 域对照（旧 → 新）

| 域 | 旧路径 | 新路径 | URL（不变） |
|----|--------|--------|-------------|
| platform | `APIs/health` | `APIs/platform/health` | `/api/health` |
| platform | `APIs/runtime` | `APIs/platform/runtime` | `/api/v1/runtime/pipeline` |
| platform | `APIs/setup` | `APIs/platform/setup` | `/api/v1/setup/*` |
| platform | `APIs/settings` | `APIs/platform/app_settings` | `/api/v1/settings/*` |
| data | `APIs/data_source` | `APIs/data/sources` | `/api/v1/data-sources/*` |
| data | `APIs/data_contract` | `APIs/data/contracts` | `/api/v1/data-contracts/*` |
| strategy | `APIs/strategy_workbench` | `APIs/strategy/workbench` | `/api/v1/strategy/*`, `/api/v1/strategies/*` |
| strategy | `APIs/strategy_scan` | `APIs/strategy/scan` | `/api/v1/strategy/*/scan*` |
| tag | `APIs/tag` | `APIs/tag` | `/api/v1/tags/*`, `/api/v1/tag/*` |

## settings 消歧

| 名称 | 归属 | URL |
|------|------|-----|
| **app_settings** | platform | `/v1/settings/database`, `/v1/settings/data`, `/v1/settings/cache/clear` |
| **simulation_options** | strategy | `/v1/strategy/settings/*`（资本配置、采样、仿真模板等） |

## 实现下沉（已完成）

| 原 `bff/support` | 现 `core.modules.*.launcher` |
|------------------|------------------------------|
| `support/tag/*` | `modules/tag/launcher/` |
| `support/strategy/*` | `modules/strategy/launcher/` |
| （断链）data_contract catalog | `modules/data_contract/launcher/` |
| data_source catalog | `modules/data_source/launcher/` |
