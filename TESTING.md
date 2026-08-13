# Testing

Default CI / local suite: `core/infra` + `core/modules` + `core/tables` (see `pytest.ini`).

```bash
python -m pytest -v
```

## Skip policy

**Skip only when the case cannot run in this repo’s CLI / GitHub CI because of missing external environment** (live MySQL/PgSQL server, proprietary dumps, interactive TTY, hardware, etc.).

```python
@pytest.mark.skipif(not shutil.which("mysql"), reason="needs local mysql client")
def test_live_mysql(): ...
```

Do **not** skip for stale / outdated APIs — delete those tests (or rewrite them).

`@pytest.mark.force_run` is a no-op leftover from the old refactor freeze; safe to leave or delete on touch.

## Strategy / data_source — critical-path cases (unit)

已覆盖（无 BE 全链路 / 无外网）：

| Area | Case |
|------|------|
| Scanner | 空目标 → `{}`；demo happy（mock `run`）；非 demo 严格门闸 → `ValueError` |
| EnumeratorPipeline | 未知 `execution_mode` → `ValueError`；`_to_report` 空失败；`_mode_job_stack` slice/entity |
| StockSampler | 空列表 / 未知策略 / uniform 全量 / random seed / weighted 全 0 回退 |
| GlobalEntityCache | `seed_system_globals` 过滤空白 id |
| date_range_helper | REFRESH / INCREMENTAL(+1) / 空 ctx / 缺 last_update 兜底 |
| execution_scheduler | 拓扑序 / 缺依赖 / 环依赖 |
| StrategySettings | `execution_mode`；`fingerprint_diff` 忽略 scanner/meta；`fingerprint_hash` 稳定/窗口敏感；effective merge |
| StrategyContext | `assemble`；`fill`/`refill` 需 stock_list；共享 `custom` 与 settings 缓存 |
| Facade simulate | enumerate 单 step；`Strategy.enumerate` 委托；缺策略失败；cache miss → `EnumeratorPipeline.run` + 写 cache；`validate_for_run` 需 steps |

仍待（半集成 / 更重 fixtures）：

| Area | Case |
|------|------|
| EnumeratorPipeline | 完整 settings → jobs → BE → report（需采样 + BE mock 更深） |
| StrategySettings.validate | 多 section 组合校验报告（有子 section 测时可再补门面级） |
