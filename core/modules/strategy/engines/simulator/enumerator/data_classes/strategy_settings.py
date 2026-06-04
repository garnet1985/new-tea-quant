#!/usr/bin/env python3
"""Enumerator settings data class."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, Literal, Union
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
        e = self.enumerator
        e.setdefault("max_workers", "auto")
        e.setdefault("is_verbose", False)
        e.setdefault("memory_budget_mb", "auto")
        e.setdefault("warmup_batch_size", "auto")
        e.setdefault("min_batch_size", "auto")
        e.setdefault("max_batch_size", "auto")
        e.setdefault("monitor_interval", 5)
        e.setdefault("entities_per_job", "auto")
        e.setdefault("dispatch_probe", True)
        e.setdefault("memory_floor_mb", "auto")

    def validate(self) -> ValidationReport:
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

        self._validate_numeric_fields(result)
        SettingsBase.log_warnings(result, logger)
        self._enumerator_validated = True
        return result

    def _validate_numeric_fields(self, result: ValidationReport) -> None:
        e = self.enumerator
        SettingsBase.validate_max_workers_field(
            report=result,
            container=e,
            key="max_workers",
            field_path="enumerator.max_workers",
            invalid_message='enumerator.max_workers 须为 "auto" 或正整数',
        )

        mi = e.get("monitor_interval", 5)
        try:
            e["monitor_interval"] = max(int(mi), 1)
        except (TypeError, ValueError):
            SettingsBase.add_warning(result, "enumerator.monitor_interval", "monitor_interval 非法，已回退 5")
            e["monitor_interval"] = 5

        epj = e.get("entities_per_job", "auto")
        if epj in (None, "", "auto"):
            e["entities_per_job"] = "auto"
        else:
            try:
                e["entities_per_job"] = max(1, int(epj))
            except (TypeError, ValueError):
                SettingsBase.add_warning(
                    result,
                    "enumerator.entities_per_job",
                    'entities_per_job 须为 "auto" 或正整数，已回退 auto',
                )
                e["entities_per_job"] = "auto"

    def to_dict(self) -> Dict[str, Any]:
        return self.deep_copy_dict(dict(self.enumerator))

    @property
    def use_sampling(self) -> bool:
        s = self.raw_settings.get("sampling")
        if isinstance(s, dict):
            return bool(s.get("use_sampling", False))
        return False

    @property
    def max_workers(self) -> Union[Literal["auto"], int]:
        return SettingsBase.parse_max_workers(self.enumerator.get("max_workers", "auto"))

    @property
    def is_verbose(self) -> bool:
        return bool(self.enumerator.get("is_verbose", False))


__all__ = ["StrategyEnumeratorSettings"]
