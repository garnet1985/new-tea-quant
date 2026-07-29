"""Tag settings 整块入口（与 settings.py section 一一对应）。

消费者: discovery, engines, Tag facade

建模::

    meta, data, calculation, tag_definitions

不建模（留 raw）::

    is_enabled, core
"""

from .validation_report import ValidationReport
from .settings_base import SettingsBase
from .meta_settings import MetaSettings
from .data_settings import DataSettings
from .calculation_settings import (
    CalculationPeriod,
    CalculationSettings,
    ExecutionSettings,
)
from .tag_definition_settings import TagDefinitionItem, TagDefinitionSettings
from .tag_settings import TagSettings

__all__ = [
    "ValidationReport",
    "SettingsBase",
    "MetaSettings",
    "DataSettings",
    "CalculationPeriod",
    "CalculationSettings",
    "ExecutionSettings",
    "TagDefinitionItem",
    "TagDefinitionSettings",
    "TagSettings",
]
