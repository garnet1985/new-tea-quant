# Strategy Settings Fingerprint Policy

## Goal

Define a stable, explicit rule set for:

- API settings shape canonicalization (avoid same-meaning different-structure payloads)
- enumerator cache fingerprint participation

This prevents cache misses caused by structural drift (for example, duplicated root/meta fields).

## Canonical Settings Shape (API / DB Snapshot)

WorkBench API and DB snapshot payloads must use the same normalized shape produced by:

- `StrategySettings(raw_settings=...).validate()`
- `StrategySettings.to_dict()`

This is the single source of truth.  
Backward compatibility may parse `meta`, but canonical persisted/output shape follows the validated dataclass output.

## Enumerator Fingerprint Field Policy

For enumerator cache matching, use the following policy.

### Hash-participating blocks

- `core`: hash
- `data`: hash
- `goal`: hash
- `sampling`: hash
- `fees`: hash

### Simulator blocks

- `capital_simulator`:
  - runtime fields: ignore
  - non-runtime fields: hash
- `price_simulator`:
  - runtime fields: ignore
  - non-runtime fields: hash

### Enumerator block

- `enumerator.use_sampling`: hash
- other enumerator runtime/perf fields: ignore

### Metadata blocks

- `meta`: ignore for enumerator fingerprint (if present in legacy payloads)
- metadata fields (`name`, `description`, `is_enabled`): treat as non-core for enumerator fingerprint

## Notes

- This policy applies to enumerator cache matching. Other simulators can keep their own policy maps.
- Any policy change should be treated as cache-key behavior change and documented in changelog/decision notes.
- For debugability, workbench snapshot rows persist:
  - `enum_fingerprint_id`
  - `enum_scope_fingerprint_id`
- Enumerator output directory persists `0_fingerprint.json` alongside `0_metadata.json`.
