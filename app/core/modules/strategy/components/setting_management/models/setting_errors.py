#!/usr/bin/env python3
"""
设置错误类型定义

定义设置验证过程中的错误级别和错误信息
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class SettingErrorLevel(Enum):
    """设置错误级别"""
    CRITICAL = "critical"  # 必须修复，停止运行
    WARNING = "warning"    # 可以继续，但需要告知用户


@dataclass
class SettingError:
    """设置错误"""
    level: SettingErrorLevel
    field_path: str  # 例如：data.base_price_source
    message: str
    suggested_fix: Optional[str] = None  # 建议修复方法


@dataclass
class SettingValidationResult:
    """设置验证结果"""
    is_valid: bool
    errors: List[SettingError] = field(default_factory=list)
    warnings: List[SettingError] = field(default_factory=list)
    
    def has_critical_errors(self) -> bool:
        """是否有严重错误"""
        return any(e.level == SettingErrorLevel.CRITICAL for e in self.errors)
    
    def raise_if_critical(self) -> None:
        """如果有严重错误，抛出异常"""
        if self.has_critical_errors():
            error_messages = [
                f"[{e.field_path}] {e.message}"
                + (f"\n  建议修复：{e.suggested_fix}" if e.suggested_fix else "")
                for e in self.errors
                if e.level == SettingErrorLevel.CRITICAL
            ]
            raise ValueError(
                f"设置验证失败（Critical）：\n" + "\n".join(error_messages)
            )
    
    def log_warnings(self, logger) -> None:
        """记录警告信息"""
        if self.warnings:
            for warning in self.warnings:
                logger.warning(
                    f"[设置警告] {warning.field_path}: {warning.message}"
                    + (f" (建议：{warning.suggested_fix})" if warning.suggested_fix else "")
                )
