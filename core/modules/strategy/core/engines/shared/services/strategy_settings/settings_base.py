"""Settings base class with common validation utilities."""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .validation_report import ValidationReport


class SettingsBase(ABC):
    """Settings base class with common validation utilities."""

    LEVEL_CRITICAL = 'critical'
    LEVEL_WARNING = 'warning'

    @staticmethod
    def new_validation() -> ValidationReport:
        """Create new validation report."""
        return ValidationReport(is_valid=True)

    @staticmethod
    def add_critical(
        report: ValidationReport,
        field_path: str,
        message: str,
        suggested_fix: Optional[str] = None,
    ) -> None:
        """Add critical error to report."""
        report.errors.append({
            'level': SettingsBase.LEVEL_CRITICAL,
            'field_path': field_path,
            'message': message,
            'suggested_fix': suggested_fix,
        })
        report.is_valid = False

    @staticmethod
    def add_warning(
        report: ValidationReport,
        field_path: str,
        message: str,
        suggested_fix: Optional[str] = None,
    ) -> None:
        """Add warning to report."""
        report.warnings.append({
            'level': SettingsBase.LEVEL_WARNING,
            'field_path': field_path,
            'message': message,
            'suggested_fix': suggested_fix,
        })

    @staticmethod
    def ensure_dict_block(raw: Dict[str, Any], key: str) -> Dict[str, Any]:
        """Ensure a block is dict."""
        block = raw.get(key)
        if block is None or not isinstance(block, dict):
            return {}
        return dict(block)

    @staticmethod
    def deep_copy_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        """Deep copy dict."""
        return copy.deepcopy(d)

    @abstractmethod
    def apply_defaults(self) -> None:
        """Apply default values."""
        pass

    @abstractmethod
    def validate(self) -> ValidationReport:
        """Validate settings."""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        pass


__all__ = ['SettingsBase']