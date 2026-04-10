from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from typing import Any, Dict, Mapping, Optional

from .contract_scope import ContractScope


@dataclass(frozen=True, slots=True)
class BaseContract(ABC):
    """
    Level-0 contract base (MVP).

    Holds stable identity + diagnostic context; concrete contracts fix scope and issue rules.
    """

    contract_id: str
    name: str
    display_name: str = ""
    context: Optional[Mapping[str, Any]] = None

    @property
    @abstractmethod
    def scope(self) -> ContractScope: ...

    def with_context(self, **extra: Any) -> BaseContract:
        merged: Dict[str, Any] = dict(self.context or {})
        merged.update(extra)
        return replace(self, context=merged)
