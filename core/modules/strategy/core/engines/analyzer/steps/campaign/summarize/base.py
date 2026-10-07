"""把 attribute 结果收成一份战役总结。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Mapping, Optional, Sequence

from core.modules.strategy.core.enums import SimulateKind

from ....consts import SCHEMA_VERSION
from ..labels import CampaignLabels

_SKIP_REASONS = {
    "insufficient_ready_rows": "可对照的回测太少。",
    "insufficient_layer_rows": "这一层没有可对照的数字（可能还没跑到这一步）。",
    "no_numeric_outcomes": "这一层没有可对照的数字。",
    "outcome_not_varying": "这项指标在各次回测之间没有变化。",
    "no_varying_knobs": "各次回测的参数取值相同，看不出差别。",
}


class SummarizeBase:
    """整理参数对照为报告主体。子类声明本层；叙事口径走 AttributeStep。"""

    LAYER: ClassVar[str] = ""
    KIND: ClassVar[SimulateKind] = SimulateKind.PORTFOLIO

    @classmethod
    def run(
        cls,
        attributed: Mapping[str, Any],
        *,
        layer: str = "",
        folder: Any = None,
        gathered: Optional[Mapping[str, Any]] = None,
        executed: Optional[Mapping[str, Any]] = None,
        joint_groups: Sequence[Sequence[str]] = (),
    ) -> Dict[str, Any]:
        del folder, gathered, executed  # 子类（如枚举）可选用
        focus = str(layer or cls.LAYER or "").strip()
        return {
            "schema_version": SCHEMA_VERSION,
            "status": str(attributed.get("status") or "skipped"),
            "n": int(attributed.get("n") or 0),
            "layer": focus,
            "generated_at": datetime.now().isoformat(),
            "headline": "",
            "highlights": [],
            "hints": cls._hints(attributed),
            "varying_knobs": list(attributed.get("varying_knobs") or []),
            "contributions": attributed.get("contributions") or {},
        }

    @classmethod
    def _hints(cls, attributed: Mapping[str, Any]) -> List[str]:
        hints: List[str] = []
        n = int(attributed.get("n") or 0)
        status = str(attributed.get("status") or "skipped")
        reason = str(attributed.get("reason") or "")
        if reason in _SKIP_REASONS:
            hints.append(_SKIP_REASONS[reason])
        varying = [str(item) for item in (attributed.get("varying_knobs") or [])]
        presence = _chapter(attributed, "presence")
        sensitivity = _chapter(attributed, "sensitivity")
        one_count = int(presence.get("one_at_a_time_count") or 0) + int(
            sensitivity.get("one_at_a_time_count") or 0
        )
        joint_count = int(presence.get("joint_count") or 0) + int(
            sensitivity.get("joint_count") or 0
        )
        if joint_count and not one_count:
            hints.append("有些回测一次改了多个参数，贡献度拆不开，只能看相关方向。")
        elif len(varying) >= 2 and not one_count:
            names = "、".join(CampaignLabels.knob_label(item) for item in varying[:4])
            hints.append(
                f"对照表里变过 {names}。相关是把所有回测混在一起算的，不是只改了一个参数。"
            )
        if n > 0 and n < 5:
            hints.append(f"只有 {n} 次回测，只看方向，数量太少谈不上统计。")
        layers = attributed.get("layers") or {}
        if isinstance(layers, dict):
            for layer_name, block in layers.items():
                if not isinstance(block, dict) or block.get("status") != "skipped":
                    continue
                note = _SKIP_REASONS.get(str(block.get("reason") or ""))
                if note:
                    hints.append(f"{CampaignLabels.layer_label(str(layer_name))}：{note}")
        if not varying and status != "skipped":
            hints.append("各次回测的参数取值相同，对照看不出差别。")
        return hints


def _chapter(attributed: Mapping[str, Any], name: str) -> Dict[str, Any]:
    block = attributed.get("contributions")
    if not isinstance(block, dict):
        return {}
    nested = block.get(name)
    return nested if isinstance(nested, dict) else {}

