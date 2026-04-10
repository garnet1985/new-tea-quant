from __future__ import annotations

from dataclasses import dataclass, field

from .base import BaseContract
from .contract_scope import ContractScope


@dataclass(frozen=True, slots=True)
class GlobalContract(BaseContract):
    """
    GlobalContract (MVP)

    Global contracts share the same structural rule:
    - scope is always GLOBAL (fixed by type)

    Note:
    - Global contracts should NOT require entity_id in context.
    """

    _scope: ContractScope = field(default=ContractScope.GLOBAL, init=False, repr=False)

    @property
    def scope(self) -> ContractScope:
        return self._scope

