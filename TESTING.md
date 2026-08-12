# Testing

Default CI / local suite: `core/infra` + `core/modules` + `setup` (see `pytest.ini`).

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

## Strategy module — pending cases (not yet covered)

| Area | Case |
|------|------|
| `StrategyContext` | `load_strategy` → validate files / hooks / settings |
| `StrategyContext` | `with_userspace` resolves dates, entity_ids, output_dir once |
| `StrategySettings` | `resolve`, `execution_mode`, `fingerprint_hash` |
| `EnumeratorPipeline` | 统一编排：settings → jobs → BE → report；按 mode 选用 JobBuilder/Executor |
| Facade | `Strategy.enumerate` only discovery + engine |
