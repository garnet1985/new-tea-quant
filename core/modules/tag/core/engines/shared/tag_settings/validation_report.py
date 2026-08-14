"""Settings validation report.

消费者: tag_settings sections, TagSettings
"""

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
        return any(e.get("level") == "critical" for e in self.errors)

    def is_usable(self) -> bool:
        return bool(self.is_valid) and not self.has_critical_errors()


__all__ = ["ValidationReport"]
