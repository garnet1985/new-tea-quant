#!/usr/bin/env python3
"""
策略 settings 数据类入口（与 ``models.strategy_settings`` 字典视图区分）。

对外主要使用 ``BaseSettings``：加载原始 dict、``validate_base_settings`` / ``is_valid``。
"""

from .base_settings import BaseSettings
from .setting_errors import SettingError, SettingErrorLevel, SettingValidationResult

__all__ = [
    "BaseSettings",
    "SettingError",
    "SettingErrorLevel",
    "SettingValidationResult",
]
