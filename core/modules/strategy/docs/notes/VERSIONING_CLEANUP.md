# Versioning 清理说明（旧磁盘布局）

**适用：** 用户盘仍是 `simulations/enum/N` 等旧布局时。现行规格见 [VERSIONING.md](../VERSIONING.md)。

---

## 1. 旧磁盘布局（无迁移）

旧路径（**已废弃**）：

```text
results/simulations/enum/N/
results/simulations/price/N/
results/simulations/portfolio/N/
  各带独立 meta.json / next_output_version
```

新路径见 [VERSIONING.md §2](../VERSIONING.md)。

**做法：** 删除整个 `results/simulations/` 后重新 `se` / `sp` / `so`。不提供自动迁移。

### CLI / API 清理

| 操作 | 命令 / API |
|------|------------|
| 删某策略全部 simulation 磁盘 | `TempCleanup.clear_backtest_results_disk(strategy_names=[...])` |
| 删某策略整个 `results/` | `TempCleanup.clear_strategy_results_disk(...)` |
| 删全部策略 simulation 磁盘 | `ArtifactRetention.clear_all()` 或 BFF `DELETE /version/cache` |
| 删单策略单 version | `ArtifactRetention.clear_by_version`、CLI `sdv`、或 BFF `DELETE …/version/:id/cache` |
| 固定 / 取消固定 | CLI `spn` / `sup`，BFF `POST\|DELETE …/version/:id/pin` |
| devcli 勾选 backtest results | `TempCleanup.run(clear_backtest_results=True)` |

路径：`core/infra/cli/dev/scripts/temp_cleanup/temp_cleanup.py`、`core/modules/strategy/core/services/artifacts/retention.py`

---

## 2. 已删除的 legacy DB 快照

表 `sys_strategy_workbench_snapshot` 及 `SimulationCacheManager` **已从代码库移除**。

- simulate / cache / version 列表 **仅** 读写磁盘 `simulations/meta.json` registry。
- 若本地 `strategy.duckdb` 仍含该表，可手动 `DROP TABLE` 或重建库；runtime 不再访问。

---

## 3. 用户盘 demo 策略

若 `userspace/strategies/.../results/simulations/enum/` 等旧目录仍存在：

1. 备份需要保留的报告（可选）
2. 删除 `results/simulations/` 或整个 `results/`
3. 重新跑 demo（例如 `python cli.py se --strategy rsi_v1 --stocks 10`）

新 run 后应出现 `simulations/meta.json` 与 `simulations/1/enum/` 等结构。

---

## 4. 回归单测锚点

| 测试文件 | 覆盖 |
|----------|------|
| `__test__/test_disk_version_e2e.py` | simulate miss/hit + registry |
| `__test__/test_versioning_regression.py` | env_invalid、共享 vid、ignore_cache 同 vid |
| `__test__/test_analysis_version_layout_e2e.py` | `{vid}/{step}/analysis/` |
| `services/artifacts/__test__/test_artifact_store.py` | allocate / prune / pin skip |
| `services/artifacts/__test__/test_version_meta.py` | registry + 根上 `pinned` |
| `services/artifacts/__test__/test_retention.py` | keep-N + 删 version 同步 unpin |
| BFF step report `analysis` 字段 | `Strategy.resolve_step_analysis` + `enabled` / `facts` |

---

## 5. 明确不清理

- `core/modules/backtest_engine/__performance__/reports/` 内历史 metrics 路径字符串（只读报告，不影响 runtime）
