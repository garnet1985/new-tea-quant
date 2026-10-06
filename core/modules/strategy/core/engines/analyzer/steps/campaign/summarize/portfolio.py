"""组合层战役总结（soa）：仓位参数扫描曲线 + 敏感度排名。"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence

from core.modules.strategy.core.enums import SimulateKind

from .base import SummarizeBase
from . import value_ladders as ladders
from .bridge import upstream_bridge
from .joint_sweeps import build_joint_heatmaps
from .sweeps import build_parameter_sweeps

_SCOPE_NOTE = (
    "本层只归因资金分配（槽位、单票上限、分配方式）。"
    "策略参数是否普遍能赚钱，看上一层价格报告；"
    "这里看这些分配设置有没有让账户抓住价格层里能赚钱的机会。"
)
_SCOPE_NOTE_SKIPPED_STRATEGY = "信号、过滤、止盈止损的对照不在本层排名。"

_LAYER = "portfolio"
_ALLOCATION_PREFIX = "portfolio."


class PortfolioSummarize(SummarizeBase):
    LAYER = "portfolio"
    KIND = SimulateKind.PORTFOLIO

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
        base = super().run(attributed, layer=layer or cls.LAYER)
        cross = ladders.is_cross(executed, gathered, layer=_LAYER)
        sweep_pack = build_parameter_sweeps(
            gathered,
            layer=_LAYER,
            primary_outcome="total_return",
            extra_outcomes=(
                "max_drawdown",
                "win_rate",
                "capital_utilization_ratio_pct",
            ),
            knob_prefixes=(_ALLOCATION_PREFIX,),
        )
        rows = ladders.ready_rows(gathered, layer=_LAYER)
        strategy_axes = [
            path
            for path in ladders.ladder_knobs(rows)
            if not str(path).startswith(_ALLOCATION_PREFIX)
        ]
        note = _SCOPE_NOTE
        if strategy_axes:
            note = f"{note}{_SCOPE_NOTE_SKIPPED_STRATEGY}"
        base["scope_note"] = note
        base["analysis_mode"] = "cross" if cross else "oaat"
        base["sections"] = {}
        base["sweeps"] = sweep_pack.get("sweeps") or []
        base["sensitivity_rank"] = sweep_pack.get("sensitivity_rank") or []
        base["sweep_primary_outcome"] = "total_return"
        joints = build_joint_heatmaps(
            gathered,
            layer=_LAYER,
            primary_outcome="total_return",
            groups=joint_groups,
        )
        base["joint_sweeps"] = [
            block
            for block in joints
            if block
            and all(
                str(path).startswith(_ALLOCATION_PREFIX)
                for path in (block.get("knobs") or [])
            )
        ]
        base["upstream_bridge"] = upstream_bridge(gathered, layer=_LAYER)
        base["baseline_version_id"] = ladders.baseline_version_id(
            executed, gathered, layer=_LAYER
        )
        base["headline"] = ""
        return base
