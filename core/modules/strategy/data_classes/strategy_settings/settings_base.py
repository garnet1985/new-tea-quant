#!/usr/bin/env python3
"""
策略 settings 公共基类与校验结果。

单条 **error / warning** 不单独建类，统一为 ``dict``：

- ``level``: ``"critical"`` / ``"warning"``（与 ``SettingsBase.LEVEL_*`` 常量一致）
- ``field_path``: str
- ``message``: str
- ``suggested_fix``: 可选 str

汇总为 **``ValidationReport``**（仅容器）。所有规则性操作放在 **``SettingsBase``** 的静态方法上。
"""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class ValidationReport:
    """一次校验汇总：``errors`` / ``warnings`` 为上述结构的 dict 列表。"""

    is_valid: bool = True
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)

    def has_critical_errors(self) -> bool:
        """是否存在 Critical（委托 ``SettingsBase.has_critical``）。"""
        return SettingsBase.has_critical(self)

    def is_usable(self) -> bool:
        return SettingsBase.is_usable(self)

    def log_warnings(self, logger) -> None:
        SettingsBase.log_warnings(self, logger)

    def raise_if_critical(self) -> None:
        SettingsBase.raise_if_critical(self)


class SettingsBase(ABC):
    """策略 settings 章节或顶层的统一接口。"""

    LEVEL_CRITICAL = "critical"
    LEVEL_WARNING = "warning"

    # --- 校验结果：静态工厂与规则 ---

    @staticmethod
    def new_validation() -> ValidationReport:
        """空的成功报告（可随后追加 error/warning）。"""
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
        """与历史语义一致：``is_valid`` 为真且无 Critical error。"""
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

    # --- 子类契约 ---

    @abstractmethod
    def validate(self) -> ValidationReport:
        """完整校验，写入 ``ValidationReport``。"""

    @abstractmethod
    def apply_defaults(self) -> None:
        """最小可用结构 + 默认值 + 解析收敛，仅此入口。"""

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        权威、已解析的 settings 片段（或整包），结构对齐 ``settings_example``。

        实现须返回 **深拷贝**（或等价的新 dict 树），不得返回内部可变引用。
        """

    @staticmethod
    def deep_copy_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        return copy.deepcopy(data)
