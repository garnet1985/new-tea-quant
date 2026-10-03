"""组合层战役总结（soa）：仓位参数扫描曲线 + 敏感度排名。"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence

from core.modules.strategy.core.enums import SimulateKind

from .base import SummarizeBase
from . import value_ladders as ladders
from .bridge import upstream_bridge
from .joint_sweeps import build_joint_heatmaps
from .sweeps import build_parameter_sweeps

_SCOPE_NOTE_OAAT = (
    "单因素扫描：每次只改一个参数，其余保持当前配置；"
    "看曲线与敏感度排名决定该调多少。"
)
_SCOPE_NOTE_CROSS = "联合/交叉扫描：多个参数同时变化时的共同影响。"

_LAYER = "portfolio"


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
            knob_prefixes=("portfolio.", "core.", "goal."),
        )
        base["scope_note"] = _SCOPE_NOTE_CROSS if cross else _SCOPE_NOTE_OAAT
        base["analysis_mode"] = "cross" if cross else "oaat"
        base["sections"] = {}
        base["sweeps"] = sweep_pack.get("sweeps") or []
        base["sensitivity_rank"] = sweep_pack.get("sensitivity_rank") or []
        base["sweep_primary_outcome"] = "total_return"
        base["joint_sweeps"] = build_joint_heatmaps(
            gathered,
            layer=_LAYER,
            primary_outcome="total_return",
            groups=joint_groups,
        )
        base["upstream_bridge"] = upstream_bridge(gathered, layer=_LAYER)
        base["baseline_version_id"] = ladders.baseline_version_id(
            executed, gathered, layer=_LAYER
        )
        base["headline"] = ""
        return base
