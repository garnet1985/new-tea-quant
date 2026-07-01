"""Strategy settings proxy (shell/container for all sub-settings)."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict

from .general_settings import GeneralSettings
from .enumerator_settings import EnumeratorSettings
from .validation_report import ValidationReport


@dataclass
class StrategySettings:
    """Strategy settings proxy (shell/container for all sub-settings).

    2层结构：
    - 外层：StrategySettings（proxy/壳子）
    - 内层：GeneralSettings、EnumeratorSettings等子配置类

    简化版本：只包含GeneralSettings和EnumeratorSettings。
    TODO: 后续添加完整的子配置类（MarketProfileSettings、FeesSettings、SimulationSettings等）。
    """
    raw_settings: Dict[str, Any]
    _validated: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        """Post-init: deep copy raw_settings and create sub-settings."""
        object.__setattr__(self, 'raw_settings', copy.deepcopy(self.raw_settings))
        object.__setattr__(self, 'general', GeneralSettings(raw_settings=self.raw_settings))
        object.__setattr__(self, 'enumerator', EnumeratorSettings(raw_settings=self.raw_settings))

    @property
    def is_enabled(self) -> bool:
        """Get is_enabled flag."""
        return self.general.is_enabled

    @property
    def display_name(self) -> str:
        """Get display name."""
        return self.general.display_name

    def apply_defaults(self) -> None:
        """Apply defaults to all sub-settings."""
        self.general.apply_defaults()
        self.enumerator.apply_defaults()

    def validate(self) -> ValidationReport:
        """Validate all sub-settings."""
        report = ValidationReport(is_valid=True)

        # Validate general
        general_report = self.general.validate()
        report.errors.extend(general_report.errors)
        report.warnings.extend(general_report.warnings)
        if not general_report.is_valid:
            report.is_valid = False

        # Validate enumerator
        enum_report = self.enumerator.validate()
        report.errors.extend(enum_report.errors)
        report.warnings.extend(enum_report.warnings)
        if not enum_report.is_valid:
            report.is_valid = False

        self._validated = report.is_usable()
        return report

    def is_valid(self) -> bool:
        """Check if settings is valid."""
        return bool(self._validated)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        self.apply_defaults()
        out = copy.deepcopy(self.raw_settings)
        out['is_enabled'] = self.is_enabled
        out['meta'] = self.general.meta
        out['core'] = self.general.core
        out['enumerator'] = self.enumerator.to_dict()
        return out


__all__ = ['StrategySettings']