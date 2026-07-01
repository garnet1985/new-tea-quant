# Testing (refactor freeze)

Strategy / enumerator refactor in progress. **All pytest cases are skipped by default.**

## What stays

- Test source files under `**/__test__/`
- Case registries: `**/__test__/test_cases.yaml` (scenario inventory for re-enable)

## Run tests manually

```bash
NTQ_TESTS_ENABLED=1 python -m pytest core/modules/strategy/__test__/ -v
NTQ_TESTS_ENABLED=1 python -m pytest -v   # full suite (slow)
```

Single test during refactor:

```python
@pytest.mark.force_run
def test_something(): ...
```

## Re-enable globally

Remove or narrow the skip hook in `/conftest.py` when the refactor stabilizes.

## Strategy module — pending cases (not yet in yaml)

| Area | Case |
|------|------|
| `StrategyContext` | `load_strategy` → validate files / hooks / settings |
| `StrategyContext` | `with_userspace` resolves dates, entity_ids, output_dir once |
| `StrategySettings` | `resolve`, `execution_mode`, `fingerprint_hash` |
| `EnumeratorEngine` | thin route: `StrategyContext` → entity/slice pipeline |
| Facade | `Strategy.enumerate` only discovery + engine |

See also `core/modules/strategy/__test__/test_cases.yaml`.
