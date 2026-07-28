# Tag 架构

**版本：** `0.4.0`

---

## 模块介绍

`modules.tag` 将 userspace 场景编排为可并行标签计算：

**Discovery**（`settings.py` + `tag.py`）→ **settings 校验** → **metadata ensure** → **entity/slice pipeline**（经 BacktestEngine）→ **flush tag_value**。

---

## 模块目标

- **配置驱动**：场景目录 + `settings.py` + `TagHooks`，无需改框架即可扩展。
- **可复用资产**：标签落库后供策略与下游读取。
- **防泄露**：计算走 as_of / JobContext 前缀语义，不把全历史直接塞给业务钩子。

---

## 工作拆分

| 区域 | 职责 |
|------|------|
| `tag.py` | Facade：`execute` / `refresh` / `list_*` / `find` |
| `contracts.py` | 公开 hooks / 枚举类型 |
| `core/services/` | discovery、metadata_ensure、entity_list |
| `core/engines/` | entity_based / slice_based + shared（window、progress、flush、hooks） |
| `core/bff_support/` | UI：`TagCatalog` / `TagRunLauncher` |
| `core/infra/cli` | `cli.py tag`（模块内无 CLI） |

调度配置：`core/default_config/worker.json` → `job_pipeline.tag`（经 `TagWorkerProfile` / BE worker_profile）。

---

## 执行流（摘要）

```text
Tag.execute
  → Discovery / TagSettings.validate
  → Scenario + MetadataEnsureService
  → TagEntityListResolver
  → TagEntityPipeline | TagSlicePipeline
       → BacktestEngine（jobs / Timeline|Slice）
       → TagValueFlushService（dry_run 时跳过写库）
```

边界细节见 [BOUNDARY_NOTES.md](BOUNDARY_NOTES.md)。

---

## 依赖

见根目录 `module_info.yaml`。数据读写依赖 `data_manager`；调度依赖 `backtest_engine`。
