"""Enumerator settings data class."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from .settings_base import SettingsBase
from .validation_report import ValidationReport


@dataclass
class EnumeratorSettings(SettingsBase):
    """Enumerator settings.

    简化版本：只包含enumerator块的基础配置。
    TODO: 后续完善完整的enumerator配置（calendar_slice、dispatch_keys等）。
    """
    raw_settings: Dict[str, Any]

    @property
    def enumerator(self) -> Dict[str, Any]:
        """Get enumerator dict."""
        return SettingsBase.ensure_dict_block(self.raw_settings, 'enumerator')

    @property
    def is_verbose(self) -> bool:
        """Get is_verbose flag."""
        return bool(self.enumerator.get('is_verbose', False))

    def apply_defaults(self) -> None:
        """Apply default values."""
        # Ensure enumerator block exists
        if 'enumerator' not in self.raw_settings or not isinstance(self.raw_settings['enumerator'], dict):
            self.raw_settings['enumerator'] = {}
        # Ensure is_verbose exists
        if 'is_verbose' not in self.enumerator:
            self.raw_settings['enumerator']['is_verbose'] = False

    def validate(self) -> ValidationReport:
        """Validate settings."""
        report = SettingsBase.new_validation()
        self.apply_defaults()

        # Validate is_verbose
        if not isinstance(self.enumerator.get('is_verbose'), bool):
            SettingsBase.add_warning(
                report,
                'enumerator.is_verbose',
                'is_verbose should be bool',
                suggested_fix='Set is_verbose to true or false',
            )

        return report

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        self.apply_defaults()
        return {
            'is_verbose': self.is_verbose,
        }


__all__ = ['EnumeratorSettings']