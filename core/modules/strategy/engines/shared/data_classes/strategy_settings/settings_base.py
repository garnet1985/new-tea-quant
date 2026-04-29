#!/usr/bin/env python3
"""
策略 settings 公共基类与校验结果。
"""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple, Union


@dataclass
class ValidationReport:
    is_valid: bool = True
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)

    def has_critical_errors(self) -> bool:
        return SettingsBase.has_critical(self)

    def is_usable(self) -> bool:
        return SettingsBase.is_usable(self)

    def log_warnings(self, logger) -> None:
        SettingsBase.log_warnings(self, logger)

    def raise_if_critical(self) -> None:
        SettingsBase.raise_if_critical(self)


class SettingsBase(ABC):
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
    def has_critical(report: ValidationReport) -> bool:
        return any(
            e.get("level") == SettingsBase.LEVEL_CRITICAL for e in report.errors
        )

    @staticmethod
    def is_usable(report: ValidationReport) -> bool:
        return bool(report.is_valid) and not SettingsBase.has_critical(report)

    @staticmethod
    def log_warnings(report: ValidationReport, logger) -> None:
        if not report.warnings:
            return
        for w in report.warnings:
            sf = w.get("suggested_fix")
            logger.warning(
                f"[设置警告] {w.get('field_path', '')}: {w.get('message', '')}"
                + (f" (建议：{sf})" if sf else "")
            )

    @staticmethod
    def raise_if_critical(report: ValidationReport) -> None:
        if not SettingsBase.has_critical(report):
            return
        lines = [
            f"[{e.get('field_path', '')}] {e.get('message', '')}"
            + (
                f"\n  建议修复：{e.get('suggested_fix')}"
                if e.get("suggested_fix")
                else ""
            )
            for e in report.errors
            if e.get("level") == SettingsBase.LEVEL_CRITICAL
        ]
        raise ValueError("设置验证失败（Critical）：\n" + "\n".join(lines))

    @staticmethod
    def merge_validation_results(*parts: ValidationReport) -> ValidationReport:
        merged = SettingsBase.new_validation()
        for p in parts:
            merged.errors.extend(p.errors)
            merged.warnings.extend(p.warnings)
            if not p.is_valid:
                merged.is_valid = False
        if SettingsBase.has_critical(merged):
            merged.is_valid = False
        return merged

    @staticmethod
    def append_errors(
        target: ValidationReport,
        errors: Iterable[Dict[str, Any]],
    ) -> None:
        target.errors.extend(errors)

    @staticmethod
    def append_warnings(
        target: ValidationReport,
        warnings: Iterable[Dict[str, Any]],
    ) -> None:
        target.warnings.extend(warnings)

    @staticmethod
    def mark_invalid_if_critical(target: ValidationReport) -> None:
        if SettingsBase.has_critical(target):
            target.is_valid = False

    @staticmethod
    def critical_error_paths(report: ValidationReport) -> List[str]:
        return [
            str(e.get("field_path", ""))
            for e in report.errors
            if e.get("level") == SettingsBase.LEVEL_CRITICAL
        ]

    @abstractmethod
    def validate(self) -> ValidationReport:
        pass

    @abstractmethod
    def apply_defaults(self) -> None:
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        pass

    @staticmethod
    def deep_copy_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        return copy.deepcopy(data)

    @staticmethod
    def ensure_dict_block(root: Dict[str, Any], key: str) -> Dict[str, Any]:
        if not isinstance(root, dict):
            root = {}
        block = root.get(key)
        if not isinstance(block, dict):
            block = {}
            root[key] = block
        return block

    @staticmethod
    def parse_max_workers(value: Any) -> Union[Literal["auto"], int]:
        if value == "auto" or value is None:
            return "auto"
        try:
            return max(int(value), 1)
        except (TypeError, ValueError):
            return "auto"

    @staticmethod
    def normalize_max_workers_inplace(container: Dict[str, Any], key: str) -> None:
        container[key] = SettingsBase.parse_max_workers(container.get(key, "auto"))

    @staticmethod
    def validate_max_workers_field(
        *,
        report: ValidationReport,
        container: Dict[str, Any],
        key: str,
        field_path: str,
        invalid_message: str,
    ) -> Tuple[bool, Union[Literal["auto"], int]]:
        raw = container.get(key, "auto")
        if raw == "auto" or raw is None:
            container[key] = "auto"
            return True, "auto"
        try:
            parsed = max(int(raw), 1)
            container[key] = parsed
            return True, parsed
        except (TypeError, ValueError):
            SettingsBase.add_critical(report, field_path, invalid_message)
            return False, "auto"
