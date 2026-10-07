"""稀疏 execute_fp 覆盖。dict 留下兄弟键，list 整段替换，None 关掉该位置。"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

from core.infra.utils import Utils
from core.modules.strategy.core.engines.shared.services.strategy_settings.execute_fp_whitelist import (
    EXECUTE_SETTINGS_FIELDS,
    NON_EXECUTE_SETTINGS_FIELDS,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.settings_base import (
    SettingsBase,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.validation_report import (
    ValidationReport,
)


@dataclass
class SettingsOverlay(SettingsBase):
    """一格 overlay：只含要动的 execute_fp 位置。"""

    raw_settings: Dict[str, Any]

    def __post_init__(self) -> None:
        self.raw_settings = copy.deepcopy(self.raw_settings)

    @classmethod
    def from_dict(cls, settings: Mapping[str, Any]) -> "SettingsOverlay":
        """从字典构造覆盖行。"""
        if not isinstance(settings, Mapping):
            raise ValueError("overlay 行须为 dict")
        return cls(raw_settings=dict(settings))

    def apply_defaults(self) -> None:
        """覆盖行没有可补的缺省。"""
        return

    def validate(self) -> ValidationReport:
        """校验覆盖行。"""
        report = SettingsBase.new_validation()
        if not self.raw_settings:
            SettingsBase.add_critical(
                report,
                "",
                "overlay 不能为空",
                suggested_fix="至少写一个 execute_fp 块，例如 core / goal",
            )
            return report
        for key in self.raw_settings:
            if key in NON_EXECUTE_SETTINGS_FIELDS or key not in EXECUTE_SETTINGS_FIELDS:
                SettingsBase.add_critical(
                    report,
                    key,
                    f"overlay 只允许 execute_fp 白名单块，不能写 {key!r}",
                    suggested_fix=f"允许 {sorted(EXECUTE_SETTINGS_FIELDS)}",
                )
        return report

    def to_dict(self) -> Dict[str, Any]:
        """导出覆盖字典。"""
        return copy.deepcopy(self.raw_settings)

    def merge_onto(self, snapshot: StrategySettings) -> StrategySettings:
        """快照 ⊕ 本行 → 再走普通 Run 的 to_usable。"""
        report = self.validate()
        if not report.is_usable():
            raise ValueError(StrategySettings.format_validation_error(report))
        _assert_list_items_complete(snapshot.raw_settings, self.raw_settings)
        merged = Utils.types.deep_merge(
            dict(snapshot.raw_settings),
            dict(self.raw_settings),
        )
        return StrategySettings.to_usable(merged)


def _assert_list_items_complete(snapshot: Any, overlay: Any, path: str = "") -> None:
    if not isinstance(overlay, Mapping):
        return
    snap_map = snapshot if isinstance(snapshot, Mapping) else {}
    for key, ov_val in overlay.items():
        here = f"{path}.{key}" if path else str(key)
        snap_val = snap_map.get(key) if isinstance(snap_map, Mapping) else None
        if isinstance(ov_val, list):
            _assert_replaced_list(here, snap_val, ov_val)
            continue
        if isinstance(ov_val, Mapping) and isinstance(snap_val, Mapping):
            _assert_list_items_complete(snap_val, ov_val, here)


def _assert_replaced_list(path: str, snapshot_list: Any, overlay_list: List[Any]) -> None:
    if not isinstance(snapshot_list, list):
        return
    for i, item in enumerate(overlay_list):
        if i >= len(snapshot_list):
            break
        template = snapshot_list[i]
        if not isinstance(template, Mapping):
            continue
        if not isinstance(item, Mapping):
            raise ValueError(f"{path}[{i}] 须为 dict，且字段写全")
        missing = [k for k in template.keys() if k not in item]
        if missing:
            raise ValueError(
                f"{path}[{i}] 必须写全该档字段，缺 {missing}；"
                "list 整段替换，不能只改 ratio 继承旧的 close_invest"
            )
