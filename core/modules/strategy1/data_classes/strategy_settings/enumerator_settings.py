#!/usr/bin/env python3
"""
策略 ``enumerator`` 配置块（对应 ``settings_example`` 第 6) 节）。

持有整包 ``settings`` 的引用，以便在校验时一并检查 ``goal``（枚举器依赖）；
``enumerator`` 子树本身负责默认值与字段合法性。
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, Literal, Union

from .goal_settings import StrategyGoalSettings
from .settings_base import SettingsBase, ValidationReport

logger = logging.getLogger(__name__)


@dataclass
class StrategyEnumeratorSettings(SettingsBase):
    """
    枚举器相关配置。

    - ``raw_settings``：完整策略 settings 字典（与 ``StrategySettings.raw_settings`` 可为同一引用）
    - ``enumerator``：通过属性访问 ``raw_settings["enumerator"]``
    """

    raw_settings: Dict[str, Any]
    _missing_use_sampling_at_load: bool = field(default=False, repr=False)
    _enumerator_validated: bool = field(default=False, repr=False)

    @property
    def enumerator(self) -> Dict[str, Any]:
        block = self.raw_settings.get("enumerator")
        if not isinstance(block, dict):
            block = {}
            self.raw_settings["enumerator"] = block
        return block

    @property
    def strategy_name(self) -> str:
        return str(self.raw_settings.get("name", "unknown") or "unknown")

    @classmethod
    def from_strategy_root(cls, root: Dict[str, Any]) -> StrategyEnumeratorSettings:
        """挂载 ``enumerator``；缺省或非 dict 时写入 ``{}``。"""
        if not isinstance(root, dict):
            root = {}
        block = root.get("enumerator")
        missing_use_sampling = not isinstance(block, dict) or "use_sampling" not in block
        if not isinstance(block, dict):
            block = {}
            root["enumerator"] = block
        return cls(raw_settings=root, _missing_use_sampling_at_load=missing_use_sampling)

    @classmethod
    def from_base_settings(cls, base_settings: "StrategySettings") -> StrategyEnumeratorSettings:
        """从顶层 ``StrategySettings`` 创建（共享 ``raw_settings`` 引用）。"""
        return cls.from_strategy_root(base_settings.raw_settings)

    def apply_defaults(self) -> None:
        """与 ``settings_example`` 中 ``enumerator`` 默认值对齐。"""
        e = self.enumerator
        if "use_sampling" not in e:
            e["use_sampling"] = False
        if "max_test_versions" not in e:
            e["max_test_versions"] = 10
        if "max_output_versions" not in e:
            e["max_output_versions"] = 3
        if "max_workers" not in e:
            e["max_workers"] = "auto"
        if "is_verbose" not in e:
            e["is_verbose"] = False
        if "memory_budget_mb" not in e:
            e["memory_budget_mb"] = "auto"
        if "warmup_batch_size" not in e:
            e["warmup_batch_size"] = "auto"
        if "min_batch_size" not in e:
            e["min_batch_size"] = "auto"
        if "max_batch_size" not in e:
            e["max_batch_size"] = "auto"
        if "monitor_interval" not in e:
            e["monitor_interval"] = 5

    def validate(self) -> ValidationReport:
        """
        校验枚举器块 + ``goal``（随整包 ``StrategySettings.validate()`` 在发现阶段调用）。

        先 ``apply_defaults``，再 ``StrategyGoalSettings.validate_goal_dict``，
        最后检查 ``max_*`` / ``max_workers`` 等类型。
        """
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

        if self._missing_use_sampling_at_load:
            SettingsBase.add_warning(
                result,
                "enumerator.use_sampling",
                "use_sampling 未配置，已默认 False（全量枚举，结果保存在 output/ 目录）",
                suggested_fix='在 settings.py 的 enumerator 中添加 "use_sampling": True 以启用采样枚举',
            )

        self._validate_numeric_fields(result)

        SettingsBase.log_warnings(result, logger)
        self._enumerator_validated = True
        return result

    def _validate_numeric_fields(self, result: ValidationReport) -> None:
        e = self.enumerator

        for key, default in (("max_test_versions", 10), ("max_output_versions", 3)):
            val = e.get(key, default)
            try:
                n = int(val)
                if n < 1:
                    raise ValueError
                e[key] = n
            except (TypeError, ValueError):
                SettingsBase.add_critical(
                    result,
                    f"enumerator.{key}",
                    f"enumerator.{key} 必须为正整数",
                    suggested_fix=f'设为例如 "{key}": 10',
                )

        mw = e.get("max_workers", "auto")
        if mw == "auto" or mw is None:
            e["max_workers"] = "auto"
        else:
            try:
                e["max_workers"] = max(int(mw), 1)
            except (TypeError, ValueError):
                SettingsBase.add_critical(
                    result,
                    "enumerator.max_workers",
                    'enumerator.max_workers 须为 "auto" 或正整数',
                    suggested_fix='设为 "auto" 或例如 4',
                )

        mi = e.get("monitor_interval", 5)
        try:
            e["monitor_interval"] = max(int(mi), 1)
        except (TypeError, ValueError):
            SettingsBase.add_warning(
                result,
                "enumerator.monitor_interval",
                "monitor_interval 非法，已回退为 5",
                suggested_fix="设为不小于 1 的整数",
            )
            e["monitor_interval"] = 5

    def to_dict(self) -> Dict[str, Any]:
        return self.deep_copy_dict(dict(self.enumerator))

    # --- 便捷访问（读 ``enumerator``，已含默认值）---

    @property
    def use_sampling(self) -> bool:
        return bool(self.enumerator.get("use_sampling", False))

    @property
    def max_test_versions(self) -> int:
        try:
            return max(int(self.enumerator.get("max_test_versions", 10)), 1)
        except (TypeError, ValueError):
            return 10

    @property
    def max_output_versions(self) -> int:
        try:
            return max(int(self.enumerator.get("max_output_versions", 3)), 1)
        except (TypeError, ValueError):
            return 3

    @property
    def max_workers(self) -> Union[Literal["auto"], int]:
        mw = self.enumerator.get("max_workers", "auto")
        if mw == "auto" or mw is None:
            return "auto"
        try:
            return max(int(mw), 1)
        except (TypeError, ValueError):
            return "auto"

    @property
    def is_verbose(self) -> bool:
        return bool(self.enumerator.get("is_verbose", False))


EnumeratorSettings = StrategyEnumeratorSettings
