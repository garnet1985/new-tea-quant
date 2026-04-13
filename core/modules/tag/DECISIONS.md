# Tag Decisions

## Decision 001: Split Tag Into `entity_based` And `general`

- **Status**: Accepted
- **Date**: 2026-04-13
- **Scope**: `core/modules/tag`

### Context

Tag configuration previously mixed two different intents in one model:

- Tags attached to concrete entities (for example, per-stock tags).
- Tags describing a global/context state (for example, macro regime).

This caused repeated ambiguity in design and implementation:

- Is `target_entity` defining data source, owner, or both?
- How should `required` multi-source inputs decide execution axis?
- Where should computed tag values be attached when there is no natural entity?

### Decision

Tag is explicitly split into two kinds:

- `entity_based`: tag value belongs to concrete entities.
- `general`: tag value belongs to a general/context owner (non per-entity semantics).

### Why this split

1. **Removes semantic ambiguity**
   - `entity_based` answers “tag belongs to which entity”.
   - `general` answers “tag describes global/context state”.

2. **Makes execution deterministic**
   - `entity_based` runs per entity set.
   - `general` runs on a single context owner.

3. **Aligns with common industry patterns**
   - Asset/security-level signals vs market/macro regime signals.

4. **Reduces config confusion**
   - Users select kind first, then fill only relevant fields.

### Configuration implications

Shared data section:

- `data.required`: all required data contracts.
- `data.tag_time_axis_based_on`: which required data provides the time axis.

Rules:

- `entity_based`
  - `target_entity` is used.
  - `data.tag_time_axis_based_on` is optional; defaults to target-entity axis.
- `general`
  - `target_entity` can be omitted.
  - `data.tag_time_axis_based_on` is mandatory.

Validation baseline:

- `data.required` must be non-empty.
- `data.required[*].data_id` must be unique.
- If configured, `data.tag_time_axis_based_on` must exist in `data.required`.
- Axis data must be time-series.

### Consequences

Positive:

- Cleaner mental model and easier onboarding.
- Clearer storage ownership semantics.
- Easier to evolve per-kind execution and optimization independently.

Trade-offs:

- Need explicit kind selection in settings.
- Need dual-path validation and documentation.

### Alternatives considered

1. **Single model with optional `target_entity` only**
   - Rejected: still ambiguous for global/context cases.

2. **Infer kind automatically from required data**
   - Rejected: implicit behavior is hard to reason about and hard to debug.

### Follow-up

- Keep docs/examples consistent with this split.
- Keep runtime APIs explicit about owner semantics.
- Revisit naming only if user feedback shows confusion.

---

## Decision 002: Do Not Support Cross-Sectional Slice Mode Yet

- **Status**: Accepted
- **Date**: 2026-04-13
- **Scope**: `core/modules/tag`

### Context

Tag discussions identified another orthogonal dimension:

- `independent` mode: each entity computes independently (current runtime path).
- `cross_sectional` mode: same-date slice over a universe, then compare/rank across entities.

Cross-sectional mode is significantly more complex than independent mode in the current architecture.

### Decision

For now, Tag module only supports independent per-entity computation.

Cross-sectional slice mode is explicitly deferred and tracked as future TODO work.

### Why defer

1. **High memory pressure risk**
   - Cross-sectional requires same-date multi-entity windows in memory.
   - Without robust caching/streaming design, memory blow-up is likely.

2. **Cache design not ready**
   - Needs dedicated cache keys and lifecycle for date-slice + universe combinations.
   - Needs clear invalidation strategy under incremental/refresh runs.

3. **Execution model mismatch**
   - Current job model is one-entity-per-job.
   - Cross-sectional needs coordinated date-batch execution and aggregation.

### Consequences

- Current behavior remains simple and stable.
- Users must implement only independent tag logic for now.
- Documentation should clearly state cross-sectional is not available yet.

### TODO (Future)

1. Define `calculation_mode` config (`independent` / `cross_sectional`).
2. Design cross-sectional cache strategy (date-slice + universe aware).
3. Add memory guardrails and streaming/batch loading plan.
4. Add dedicated executor path for cross-sectional runs.
5. Add end-to-end tests for correctness and memory bounds.
