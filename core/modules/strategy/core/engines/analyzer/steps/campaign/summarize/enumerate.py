"""枚举层战役总结（sea）：非交叉时按旋钮讲取值阶梯（最多/最少/趋势/对照表）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore

from ..gather.enum_exits import after_take_profit_probe, baseline_exit_diagnosis
from ..labels import CampaignLabels
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

_LAYER = "enumerate"

_SECTION_KNOB_PREFIXES = {
    "opportunity": ("core.", "data.", "sampling."),
    "stock_distribution": ("core.", "data.", "sampling."),
    "dispersion": ("core.", "data.", "sampling."),
    "exit_quality": ("goal.",),
}

_SECTION_META = (
    (
        "opportunity",
        "各个参数是如何影响回测找到的机会总数？",
        ("total_opportunities",),
    ),
    (
        "stock_distribution",
        "各个参数是如何影响机会的在股票间的分布？",
        ("trigger_ratio", "top_bucket_ratio"),
    ),
    (
        "dispersion",
        "各个参数是如何影响单只票的所有机会在回测区间的分散度？",
        ("cv",),
    ),
    (
        "exit_quality",
        "止损与止盈的不同取值是如何影响股票亏损与盈利的比例？",
        ("stop_loss_ratio", "take_profit_ratio"),
    ),
)


class EnumerateSummarize(SummarizeBase):
    LAYER = "enumerate"
    KIND = SimulateKind.ENUMERATE

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
        root = Path(folder) if folder is not None else None
        baseline_vid = ladders.baseline_version_id(
            executed, gathered, layer=_LAYER
        )
        cross = ladders.is_cross(executed, gathered, layer=_LAYER)
        sections = cls._build_sections(
            gathered=gathered,
            folder=root,
            baseline_vid=baseline_vid,
        )
        sweep_pack = build_parameter_sweeps(
            gathered,
            layer=_LAYER,
            primary_outcome="total_opportunities",
            extra_outcomes=("trigger_ratio", "top_bucket_ratio", "cv"),
            knob_prefixes=("core.", "goal.", "data.", "sampling."),
        )
        base["scope_note"] = _SCOPE_NOTE_CROSS if cross else _SCOPE_NOTE_OAAT
        base["analysis_mode"] = "cross" if cross else "oaat"
        base["sections"] = sections
        base["sweeps"] = sweep_pack.get("sweeps") or []
        base["sensitivity_rank"] = sweep_pack.get("sensitivity_rank") or []
        base["sweep_primary_outcome"] = "total_opportunities"
        base["joint_sweeps"] = build_joint_heatmaps(
            gathered,
            layer=_LAYER,
            primary_outcome="total_opportunities",
            groups=joint_groups,
        )
        base["upstream_bridge"] = upstream_bridge(gathered, layer=_LAYER)
        base["baseline_version_id"] = baseline_vid
        base["headline"] = ""
        return base

    @classmethod
    def _build_sections(
        cls,
        *,
        gathered: Optional[Mapping[str, Any]],
        folder: Optional[Path],
        baseline_vid: str,
    ) -> Dict[str, Any]:
        rows = ladders.ready_rows(gathered, layer=_LAYER)
        knobs = ladders.ladder_knobs(rows)
        baseline_metrics = ladders.baseline_metrics(rows, layer=_LAYER)
        sections: Dict[str, Any] = {}
        for key, question, outcomes in _SECTION_META:
            prefixes = _SECTION_KNOB_PREFIXES.get(key) or ()
            section_knobs = [
                path for path in knobs if ladders.knob_allowed(path, prefixes)
            ]
            effects: List[Dict[str, Any]] = []
            for outcome in outcomes:
                for knob in section_knobs:
                    ladder = ladders.value_ladder(
                        rows, layer=_LAYER, knob=knob, outcome=outcome
                    )
                    if len(ladder.get("levels") or []) < 2:
                        continue
                    effect = ladders.effect_block(
                        ladder,
                        baseline_metric=baseline_metrics.get(outcome),
                    )
                    if effect:
                        effects.append(effect)
            sections[key] = {
                "question": question,
                "outcomes": list(outcomes),
                "effects": effects,
                "facts": ladders.facts_from_effects(effects),
                "conclusion": ladders.conclusion_from_effects(effects),
                "suggestion": "",
            }

        exit_sec = sections["exit_quality"]
        if folder is not None and baseline_vid:
            diagnosis = baseline_exit_diagnosis(folder, baseline_vid)
            exit_sec["baseline"] = diagnosis
            extra = _exit_fact_lines(diagnosis)
            if extra:
                exit_sec["facts"] = list(exit_sec.get("facts") or []) + extra
            if diagnosis.get("high_stop_loss_stocks"):
                base_c = str(exit_sec.get("conclusion") or "").rstrip("。")
                note = "止损在当前策略配置下集中在少数票或少数月份"
                if note not in base_c:
                    exit_sec["conclusion"] = (
                        f"{base_c}；{note}。" if base_c else f"{note}。"
                    )

        settings = _effective_settings(folder, baseline_vid) if folder else None
        if folder is not None and baseline_vid:
            after = after_take_profit_probe(folder, baseline_vid, settings)
            if after.get("available"):
                sections["after_take_profit"] = {
                    "question": "止盈后面还有没有涨（仅当分档或动态止盈真跑过）",
                    "effects": [],
                    "facts": list(after.get("facts") or []),
                    "conclusion": str(
                        after.get("conclusion") or after.get("reason") or ""
                    ),
                    "suggestion": "",
                    "available": True,
                    "detail": after,
                }

        for key, section in sections.items():
            if key == "after_take_profit":
                continue
            if not (section.get("effects") or []):
                section["facts"] = ["本格没有可用的参数取值对照（或指标未变化）。"]
                section["conclusion"] = "只有基准格时，不能比较取值好坏。"
                section["suggestion"] = ""
        return sections


def _effective_settings(
    folder: Optional[Path], version_id: str
) -> Optional[Dict[str, Any]]:
    if folder is None or not version_id:
        return None
    try:
        disk = VersionMetaStore.read_effective_settings(
            ArtifactStore.simulations_root(folder), version_id
        )
    except Exception:
        return None
    return disk if isinstance(disk, dict) else None


def _exit_fact_lines(diagnosis: Mapping[str, Any]) -> List[str]:
    lines: List[str] = []
    stocks = diagnosis.get("high_stop_loss_stocks") or []
    if isinstance(stocks, list) and stocks:
        bits = []
        for item in stocks[:3]:
            if not isinstance(item, dict):
                continue
            name = item.get("stock_name") or item.get("entity_id")
            ratio = item.get("stop_loss_ratio")
            bits.append(
                f"{name} 止损"
                f"{CampaignLabels.format_number('stop_loss_ratio', ratio)}"
                f"（{item.get('stop_loss')}/{item.get('n')}）"
            )
        if bits:
            lines.append("止损偏高的票：" + "；".join(bits) + "。")
    months = diagnosis.get("stop_loss_by_month") or []
    if isinstance(months, list) and months:
        bits = []
        for item in months[:3]:
            if not isinstance(item, dict):
                continue
            bits.append(
                f"{item.get('month')} "
                f"{CampaignLabels.format_number('stop_loss_ratio', item.get('stop_loss_ratio'))}"
            )
        if bits:
            lines.append("止损偏高的月份：" + "；".join(bits) + "。")
    return lines


__all__ = ["EnumerateSummarize"]
