# Decision 001: Enumerator Reuse by Containment

## Status
Accepted

## Context

Enumerator runs are resource-heavy. A strict "settings hash equal => reuse" rule is not enough for real requests because many requests are subsets of previous runs:

- Previous run covered 500 stocks.
- New request asks for 50 stocks inside that 500.
- New request time range is inside the previous range.

The system should reuse previous results when the previous run contains the new request.

## Decision

We introduce `StrategyRunFingerprint` (historical alias `EnumeratorFingerprint`) as a run/request descriptor and use containment-based reuse planning.

Fingerprint fields:

- `start_date`, `end_date`
- `settings_core`
- `stock_ids`
- `strategy_name` (for validation)
- `worker_module_path`, `worker_class_name`, `worker_code_hash` (code-change invalidation)
- `data_contract_signature` (contract/settings-data-change invalidation)

Runtime rules:

1. If cached fingerprint contains the request fingerprint, reuse the cached version directly.
2. If only `stock_ids` are not fully covered, run only the stock-id diff.
3. If core settings or time range are not compatible, rebuild fully.
4. If worker code hash or data contract signature changed, rebuild fully.

Only completed enumerator runs produce reusable fingerprints.

## Consequences

- Reuse becomes subset-aware instead of equality-only.
- Partial stock diff execution is supported and reduces unnecessary work.
- Further invalidation checks (e.g. contract/code change) can be added incrementally without changing caller-facing flow shape.
