#!/usr/bin/env python3
"""Enumerator settings data class."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Dict
from typing import TYPE_CHECKING

from core.modules.strategy.engines.shared.data_classes.strategy_settings.goal_settings import (
    StrategyGoalSettings,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.settings_base import (
    SettingsBase,
    ValidationReport,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
        StrategySettings,
    )


@dataclass
class StrategyEnumeratorSettings(SettingsBase):
    raw_settings: Dict[str, Any]
    _enumerator_validated: bool = field(default=False, repr=False)

    @property
    def enumerator(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "enumerator")

    @property
    def strategy_name(self) -> str:
        return str(self.raw_settings.get("name", "unknown") or "unknown")

    @classmethod
    def from_strategy_root(cls, root: Dict[str, Any]) -> "StrategyEnumeratorSettings":
        if not isinstance(root, dict):
            root = {}
        SettingsBase.ensure_dict_block(root, "enumerator")
        return cls(raw_settings=root)

    @classmethod
    def from_base_settings(cls, base_settings: StrategySettings) -> "StrategyEnumeratorSettings":
        return cls.from_strategy_root(base_settings.raw_settings)

    def apply_defaults(self) -> None:
        self.enumerator.setdefault("is_verbose", False)

    def validate(self) -> ValidationReport:
        from core.modules.strategy.engines.shared.worker_settings_keys import (
            ENUMERATOR_STRATEGY_DISPATCH_KEYS,
        )

        result = SettingsBase.new_validation()
        self.apply_defaults()

        goal_config = self.raw_settings.get("goal")
        if not isinstance(goal_config, dict):
            goal_config = {}
        goal_result = StrategyGoalSettings.validate_goal_dict(
            goal_config, self.strategy_name, "goal"
        )
        result.errors.extend(goal_result.errors)
        result.warnings.extend(goal_result.warnings)
        if not goal_result.is_valid:
            result.is_valid = False

        SettingsBase.warn_ignored_pipeline_pool_keys(
            result, self.enumerator, field_prefix="enumerator"
        )
        SettingsBase.warn_ignored_dispatch_keys(
            result,
            self.enumerator,
            field_prefix="enumerator",
            keys=ENUMERATOR_STRATEGY_DISPATCH_KEYS,
        )
        cs = self.enumerator.get("calendar_slice")
        if isinstance(cs, dict) and cs:
            SettingsBase.add_warning(
                result,
                "enumerator.calendar_slice",
                "忽略 calendar_slice：Reader/preload 性能参数由 worker.json "
                "job_pipeline.enumerator.calendar_slice 决定",
            )
        SettingsBase.log_warnings(result, logger)
        self._enumerator_validated = True
        return result

    def to_dict(self) -> Dict[str, Any]:
        from core.modules.strategy.engines.shared.worker_settings_keys import (
            ENUMERATOR_STRATEGY_CALENDAR_SLICE_KEYS,
            ENUMERATOR_STRATEGY_DISPATCH_KEYS,
        )

        out = self.deep_copy_dict(dict(self.enumerator))
        SettingsBase.strip_ignored_pipeline_pool_keys(out)
        SettingsBase.strip_ignored_dispatch_keys(out, ENUMERATOR_STRATEGY_DISPATCH_KEYS)
        SettingsBase.strip_ignored_dispatch_keys(out, ENUMERATOR_STRATEGY_CALENDAR_SLICE_KEYS)
        return out

    @property
    def use_sampling(self) -> bool:
        s = self.raw_settings.get("sampling")
        if isinstance(s, dict):
            return bool(s.get("use_sampling", False))
        return False

    @property
    def is_verbose(self) -> bool:
        return bool(self.enumerator.get("is_verbose", False))


__all__ = ["StrategyEnumeratorSettings"]
