"""Settings validation report."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ValidationReport:
    """Settings validation result."""
    is_valid: bool = True
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)

    def has_critical_errors(self) -> bool:
        """Check if has critical errors."""
        return any(e.get('level') == 'critical' for e in self.errors)

    def is_usable(self) -> bool:
        """Check if settings is usable (no critical errors)."""
        return bool(self.is_valid) and not self.has_critical_errors()


__all__ = ['ValidationReport']