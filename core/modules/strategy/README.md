# Strategy Module (New Architecture Skeleton)

This is the new `strategy` module skeleton.

Current status:
- New structure is in place
- Foundation migration uses bridge imports from `core/modules/strategy1`
- Incremental in-place migration will remove bridge dependencies module by module

Planned layers:
- `managers/`: top-level orchestrators
- `engines/`: scanner, simulator, analyzer flows
- `services/`: shared capabilities
- `models/`: cross-engine shared entities

