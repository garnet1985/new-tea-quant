from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple

from .base import BaseContract
from .contract_scope import ContractScope


@dataclass(frozen=True, slots=True)
class PerEntityContract(BaseContract):
    """
    PerEntityContract (MVP)

    Per-entity contracts share the same structural rule:
    - scope is always PER_ENTITY (fixed by type)
    - caller must provide an entity identifier in context (e.g. stock_id)

    This base class centralizes context merge + entity_id validation so that
    concrete per-entity contracts (static/time-axis) don't duplicate it.
    """

    context_entity_id_key: str = "entity_id"

    # Structural attributes (fixed by this contract type)
    _scope: ContractScope = field(default=ContractScope.PER_ENTITY, init=False, repr=False)

    @property
    def scope(self) -> ContractScope:
        return self._scope

    def _merge_context(self, context: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
        if not context:
            return self.context
        merged: Dict[str, Any] = dict(self.context or {})
        merged.update(dict(context))
        return merged

    def _require_entity_id(self, context: Optional[Mapping[str, Any]]) -> Tuple[Any, Mapping[str, Any]]:
        merged_ctx = self._merge_context(context)
        entity_id = merged_ctx.get(self.context_entity_id_key)
        if not entity_id:
            raise KeyError(
                "PerEntityContract: missing entity_id in context "
                f"(key='{self.context_entity_id_key}')"
            )
        return entity_id, merged_ctx

