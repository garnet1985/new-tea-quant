"""Tag settings 外层代理（与各 settings section 一一对应）。

消费者: discovery, engines, Tag facade

本文件:
- TagSettings: meta/data/calculation/tag_definitions + is_enabled/core
  边界: 负责 settings 对象化与校验；不负责磁盘 discovery 或引擎执行
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, FrozenSet, List

from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.tag.core.enums import TagTargetType, TagUpdateMode

from .calculation_settings import CalculationPeriod, CalculationSettings
from .data_settings import DataSettings
from .meta_settings import MetaSettings
from .settings_base import SettingsBase
from .tag_definition_settings import TagDefinitionItem, TagDefinitionSettings
from .validation_report import ValidationReport


@dataclass
class TagSettings:
    """Tag settings proxy。

    内层子类与 settings section 一一对应。
    """

    # Tag 暂无 simulation fingerprint；预留字段集合供后续 cache 使用
    FINGERPRINT_FIELDS: ClassVar[FrozenSet[str]] = frozenset(
        {
            "core",
            "data",
            "calculation",
            "tag_definitions",
        }
    )

    NON_FINGERPRINT_FIELDS: ClassVar[FrozenSet[str]] = frozenset(
        {
            "meta",
            "is_enabled",
        }
    )

    raw_settings: Dict[str, Any]
    _validated: bool = field(default=False, repr=False)
    _tag_key: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw_settings", copy.deepcopy(self.raw_settings))
        object.__setattr__(self, "meta", MetaSettings(raw_settings=self.raw_settings))
        object.__setattr__(self, "data", DataSettings(raw_settings=self.raw_settings))
        object.__setattr__(
            self, "calculation", CalculationSettings(raw_settings=self.raw_settings)
        )
        object.__setattr__(
            self,
            "tag_definitions",
            TagDefinitionSettings(raw_settings=self.raw_settings),
        )

    @classmethod
    def from_dict(
        cls,
        settings: Dict[str, Any],
        *,
        tag_key: str = "",
    ) -> "TagSettings":
        """从 userspace settings dict 构建；``tag_key`` 用于补齐 meta.key / name。"""
        instance = cls(raw_settings=copy.deepcopy(settings or {}))
        key = str(tag_key or "").strip()
        if key:
            object.__setattr__(instance, "_tag_key", key)
            instance.meta.ensure_key(key)
            instance.raw_settings["name"] = key
        return instance

    @property
    def is_enabled(self) -> bool:
        return bool(self.raw_settings.get("is_enabled", False))

    @property
    def key(self) -> str:
        return self.meta.key

    @property
    def name(self) -> str:
        """系统 scenario 名（目录相对路径 / tag_key）。"""
        return str(self.raw_settings.get("name") or self._tag_key or self.meta.key).strip()

    @property
    def display_name(self) -> str:
        return self.meta.display_name or self.name

    @property
    def core(self) -> Dict[str, Any]:
        block = self.raw_settings.get("core")
        return dict(block) if isinstance(block, dict) else {}

    @property
    def execution_mode(self) -> str:
        self.calculation.apply_defaults()
        raw = self.calculation.mode
        if not raw:
            raise ValueError(
                f"settings.calculation.execution.mode 必填"
                f"（{BacktestMode.ENTITY_BASED.value} | {BacktestMode.SLICE_BASED.value}）"
            )
        return BacktestMode.normalize(raw)

    @property
    def start_date(self) -> str:
        return self.calculation.start_date

    @property
    def end_date(self) -> str:
        return self.calculation.end_date

    @property
    def update_mode(self) -> str:
        return self.calculation.effective_update_mode()

    @property
    def recompute(self) -> bool:
        return self.calculation.recompute

    @property
    def is_entity_based(self) -> bool:
        return self.execution_mode == BacktestMode.ENTITY_BASED.value

    @property
    def is_slice_based(self) -> bool:
        return self.execution_mode == BacktestMode.SLICE_BASED.value

    @property
    def tag_target_type(self) -> str:
        return str(
            self.raw_settings.get("tag_target_type") or TagTargetType.ENTITY_BASED.value
        ).strip().lower()

    @property
    def attach_to_data_key(self) -> str:
        return self.data.attach_to_data_key

    @property
    def target_entity_type(self) -> str:
        return self.data.target_entity_type

    def resolve_period(self) -> CalculationPeriod:
        return self.calculation.resolve_period()

    def definition_items(self) -> List[TagDefinitionItem]:
        return self.tag_definitions.items()

    def apply_defaults(self) -> None:
        if "is_enabled" not in self.raw_settings:
            self.raw_settings["is_enabled"] = False
        if self._tag_key:
            self.meta.ensure_key(self._tag_key)
            self.raw_settings.setdefault("name", self._tag_key)
        self.raw_settings.setdefault("tag_target_type", TagTargetType.ENTITY_BASED.value)
        self.raw_settings.setdefault("core", {})
        self.meta.apply_defaults()
        self.data.apply_defaults()
        self.calculation.apply_defaults()
        self.tag_definitions.apply_defaults()

        # 派生字段（引擎可读；不要求 userspace 手写）
        self.raw_settings["attach_to_data_key"] = self.data.attach_to_data_key
        self.raw_settings["target_entity"] = {"type": self.data.target_entity_type}
        self.raw_settings["update_mode"] = self.calculation.effective_update_mode()
        self.raw_settings["recompute"] = self.calculation.recompute
        self.raw_settings["execution_mode"] = self.calculation.normalized_mode()
        self.raw_settings["start_date"] = self.calculation.start_date
        self.raw_settings["end_date"] = self.calculation.end_date
        self.raw_settings["incremental_required_records_before_as_of_date"] = (
            self.data.min_required_records
        )
        meta = self.raw_settings.setdefault("meta", {})
        if isinstance(meta, dict):
            meta["attach_to_data_key"] = self.data.attach_to_data_key

    def validate(self) -> ValidationReport:
        report = ValidationReport(is_valid=True)
        self.apply_defaults()

        if not isinstance(self.raw_settings.get("is_enabled"), bool):
            SettingsBase.add_warning(
                report,
                "is_enabled",
                "is_enabled should be bool",
                suggested_fix="Set is_enabled to true or false",
            )

        if self.raw_settings.get("performance") is not None:
            SettingsBase.add_warning(
                report,
                "performance",
                "performance is ignored; use worker.json job_pipeline.tag",
            )
            self.raw_settings.pop("performance", None)

        for sub in (
            self.meta,
            self.data,
            self.calculation,
            self.tag_definitions,
        ):
            sub_report = sub.validate()
            report.errors.extend(sub_report.errors)
            report.warnings.extend(sub_report.warnings)
            if not sub_report.is_valid:
                report.is_valid = False

        # incremental 下 min_required_records 须显式存在（可为 0）
        if self.update_mode == TagUpdateMode.INCREMENTAL.value:
            data_block = self.raw_settings.get("data")
            if isinstance(data_block, dict) and "min_required_records" not in data_block:
                SettingsBase.add_critical(
                    report,
                    "data.min_required_records",
                    "incremental mode requires data.min_required_records",
                )

        self._validated = report.is_usable()
        return report

    def is_valid(self) -> bool:
        return bool(self._validated)

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        out = copy.deepcopy(self.raw_settings)
        out["is_enabled"] = self.is_enabled
        out["meta"] = self.meta.to_dict()
        if self.core:
            out["core"] = self.core
        else:
            out.setdefault("core", {})
        out["data"] = self.data.to_dict()
        # data.required in to_dict is extras-only in userspace shape; keep expanded
        # declarations for engine via issue_declarations on DataSettings when needed.
        decls = self.data.issue_declarations()
        out["data"]["required"] = decls
        out["data"]["base"] = decls[0] if decls else out["data"].get("base")
        out["calculation"] = self.calculation.to_dict()
        out["tag_definitions"] = self.tag_definitions.to_dict()
        out.pop("performance", None)
        out.setdefault("run_options", {})
        return out


__all__ = ["TagSettings"]
