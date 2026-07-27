"""Settings section 基类与校验工具。

消费者: MetaSettings, DataSettings, CalculationSettings, TagDefinitionSettings
"""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .validation_report import ValidationReport


class SettingsBase(ABC):
    """Settings base class with common validation utilities."""

    LEVEL_CRITICAL = "critical"
    LEVEL_WARNING = "warning"

    @staticmethod
    def new_validation() -> ValidationReport:
        return ValidationReport(is_valid=True)

    @staticmethod
    def add_critical(
        report: ValidationReport,
        field_path: str,
        message: str,
        suggested_fix: Optional[str] = None,
    ) -> None:
        report.errors.append(
            {
                "level": SettingsBase.LEVEL_CRITICAL,
                "field_path": field_path,
                "message": message,
                "suggested_fix": suggested_fix,
            }
        )
        report.is_valid = False

    @staticmethod
    def add_warning(
        report: ValidationReport,
        field_path: str,
        message: str,
        suggested_fix: Optional[str] = None,
    ) -> None:
        report.warnings.append(
            {
                "level": SettingsBase.LEVEL_WARNING,
                "field_path": field_path,
                "message": message,
                "suggested_fix": suggested_fix,
            }
        )

    @staticmethod
    def ensure_dict_block(raw: Dict[str, Any], key: str) -> Dict[str, Any]:
        block = raw.get(key)
        if block is None or not isinstance(block, dict):
            return {}
        return dict(block)

    @staticmethod
    def deep_copy_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        return copy.deepcopy(d)

    @abstractmethod
    def apply_defaults(self) -> None:
        pass

    @abstractmethod
    def validate(self) -> ValidationReport:
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        pass


__all__ = ["SettingsBase"]
