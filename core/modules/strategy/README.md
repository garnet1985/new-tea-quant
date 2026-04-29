# Strategy Module

`core/modules/strategy` is the canonical strategy runtime implementation.

Current structure:
- `strategy_manager.py`: top-level scan/simulate orchestrator
- `engines/`: scanner, simulator, analyzer engines
- `services/`: cross-engine shared capabilities (discovery, data, artifacts, validation, injection)
- `engines/shared/`: shared DTOs and helpers used by multiple engines

Migration status:
- Legacy `strategy1` has been removed.
- Runtime flow is unified around discovered `StrategyInfo` and engine-local implementations.

