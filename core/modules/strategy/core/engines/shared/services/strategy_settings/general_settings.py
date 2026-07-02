"""General settings (meta + is_enabled + core)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .settings_base import SettingsBase
from .validation_report import ValidationReport


@dataclass
class GeneralSettings(SettingsBase):
    """General settings (meta + is_enabled + core).

    简化版本：只包含meta、is_enabled、core三个基础字段。
    TODO: 后续可扩展为完整的StrategyMetaSettings等子配置类。
    """
    raw_settings: Dict[str, Any]

    @property
    def meta(self) -> Dict[str, Any]:
        """Get meta dict."""
        return SettingsBase.ensure_dict_block(self.raw_settings, 'meta')

    @property
    def is_enabled(self) -> bool:
        """Get is_enabled flag."""
        return bool(self.raw_settings.get('is_enabled', False))

    @property
    def core(self) -> Dict[str, Any]:
        """Get core dict."""
        return SettingsBase.ensure_dict_block(self.raw_settings, 'core')

    @property
    def key(self) -> str:
        """Get module key from meta (future CLI / discovery id)."""
        return str(self.meta.get('key', '')).strip()

    @property
    def display_name(self) -> str:
        """Get display name from meta."""
        return str(self.meta.get('display_name', '')).strip()

    @property
    def description(self) -> str:
        """Get description from meta."""
        desc = self.meta.get('description')
        if desc is None:
            return ''
        if isinstance(desc, str):
            return desc.strip()
        if isinstance(desc, List):
            parts = [str(item).strip() for item in desc if item and str(item).strip()]
            return ''.join(parts)
        return str(desc).strip()

    def apply_defaults(self) -> None:
        """Apply default values."""
        # Ensure meta block exists
        if 'meta' not in self.raw_settings or not isinstance(self.raw_settings['meta'], dict):
            self.raw_settings['meta'] = {}
        # Ensure display_name exists
        if 'display_name' not in self.meta:
            self.raw_settings['meta']['display_name'] = ''
        # Ensure is_enabled exists
        if 'is_enabled' not in self.raw_settings:
            self.raw_settings['is_enabled'] = False
        # Ensure core block exists
        if 'core' not in self.raw_settings or not isinstance(self.raw_settings['core'], dict):
            self.raw_settings['core'] = {}

    def validate(self) -> ValidationReport:
        """Validate settings."""
        report = SettingsBase.new_validation()
        self.apply_defaults()

        # Validate is_enabled
        if not isinstance(self.raw_settings.get('is_enabled'), bool):
            SettingsBase.add_warning(
                report,
                'is_enabled',
                'is_enabled should be bool',
                suggested_fix='Set is_enabled to true or false',
            )

        # Validate core
        if not isinstance(self.core, dict):
            SettingsBase.add_critical(
                report,
                'core',
                'core must be dict',
                suggested_fix='Set core to {} or dict with strategy parameters',
            )

        return report

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        self.apply_defaults()
        return {
            'is_enabled': self.is_enabled,
            'meta': {
                'key': self.key,
                'display_name': self.display_name,
                'description': self.description,
            },
            'core': dict(self.core),
        }


__all__ = ['GeneralSettings']