# Tag 架构

**版本：** `0.4.2`

---

## 模块介绍

`modules.tag` 将 userspace 场景编排为标签计算：

**Discovery**（`settings.py` + `tag.py`）→ **settings 校验** → **metadata ensure** → 按 **`data.base` 路由** → **flush tag_value**。

- **per_entity** → `TagEntityPipeline` / `TagSlicePipeline`（经 BacktestEngine）
- **global** → `TagGlobalPipeline`（主进程日历推进，不走 BE）
- **non_time_series** → `TagNonTimeSeriesPipeline`（主进程一次计算，不走 BE）

---

## 模块目标

- **配置驱动**：场景目录 + `settings.py` + `TagHooks`，无需改框架即可扩展。
- **可复用资产**：标签落库后供策略与下游读取。
- **防泄露**：计算走 as_of / JobContext 前缀语义，不把全历史直接塞给业务钩子。

---

## 工作拆分

| 区域 | 职责 |
|------|------|
| `tag.py` | Facade：`execute` / `refresh` / `list_*` / `find`；按 `base_route` 分发 |
| `contracts.py` | 公开 hooks / 枚举类型 |
| `core/services/` | discovery、metadata_ensure、entity_list |
| `core/engines/shared/` | 全引擎共用：tag_settings / hooks / flush / calc_window / prior_values |
| `core/engines/per_entity/` | entity_based / slice_based；`shared/` 仅 BE job_payload / pipeline_hooks |
| `core/engines/global_based/` | TagGlobalPipeline / TagGlobalDataLoader |
| `core/engines/non_time_series/` | TagNonTimeSeriesPipeline / TagNonTimeSeriesDataLoader |
| `core.bff.APIs.tag` | UI catalog / runner 薄壳；进度 `TagRunProgress` |
| `core/infra/cli` | `cli.py tag`（模块内无 CLI） |

调度配置（仅 per_entity）：`core/default_config/worker.json` → `job_pipeline.tag`（经 BE `WorkerProfiles.TAG`）。

---

## 执行流（摘要）

```text
Tag.execute
  → Discovery / TagSettings.validate
  → Scenario + MetadataEnsureService
  → base_route = data.base（scope × type）
  → per_entity: TagEntityListResolver(list_data_key)
       → TagEntityPipeline | TagSlicePipeline → BacktestEngine → flush
  → global: [__global__] → TagGlobalPipeline（日历 as_of 循环）→ flush
  → non_time_series: [__global__] → TagNonTimeSeriesPipeline（一次 calculate_tag）→ flush
```

边界细节见 [BOUNDARY_NOTES.md](BOUNDARY_NOTES.md)。

---

## 依赖

见根目录 `module_info.yaml`。数据读写依赖 `data_manager`；**per_entity** 调度依赖 `backtest_engine`（global / non_ts 不依赖 BE 执行路径）。
