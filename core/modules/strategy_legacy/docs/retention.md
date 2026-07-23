# 保留与清理（Retention）

策略域有两套独立的「版本」概念，清理职责分离。

## 术语

| 名称 | 存储 | 配置 | 模块 |
|------|------|------|------|
| 工作台 `version` | `sys_strategy_workbench_snapshot` 表行 | `MAX_SNAPSHOT_ROWS_PER_STRATEGY`（默认 50） | `workbench_snapshot_retention.py` |
| 磁盘 `output_version` | `results/simulations/{enum\|price\|capital}/<id>/` | `simulation.retention.max_output_versions`（默认 3） | `simulation_output_retention.py` |

`version_id`（`v3`）仅为展示；与磁盘目录名 `<id>` 无自动同步关系。

## 磁盘清理

- **入口**：`prune_disk_output_after_sim_run(strategy, sim_kind, settings)`；维护全树用 `prune_disk_outputs_for_strategy`。
- **触发**：enum / price / capital 全量跑完的 `postprocess` 末尾；**DB 缓存命中**时也会调用 `prune_disk_outputs_for_strategy`。
- **规则**：每个 `sim_kind` 根目录下，按数字目录名保留最新 N 个；**被工作台 `result_report` 或下游 metadata 引用的目录名不删**。

## 工作台 DB 清理

- **入口**：`WorkbenchSnapshotRetention.prune_oldest_if_over_limit`（`SimulatorResDbCacheService.set_cache` 后调用）。
- **删行**：记录日志中的磁盘路径引用（**不**随删行 `rmtree` 磁盘目录）。
- **`write_count`**：`result_report._db_cache_meta.write_count` 仅作同行 merge **次数审计**；**不**触发删行、**不**分配新 `version`。工作台 `version` 仅在 **`settings_fp` / `env_fp` 变化** 时递增新行（见 [`db-cache-service.md`](./db-cache-service.md) §6.1）。

## 配置示例

```python
"simulation": {
    "template": "standard",
    "retention": {
        "max_output_versions": 3,
    },
},
```
