"""价格层战役总结（spa）：去噪后等权账能不能赚 / 是否普遍 / 出场结构。

对照轴来自战役共用副本（core/goal/simulation）；不去噪规则本身当主问题。
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from core.modules.strategy.core.enums import SimulateKind

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

_LAYER = "price_factor"

# 共用副本上：边/结实程度看想法与去噪轴；出场结构优先 goal
_SECTION_KNOB_PREFIXES = {
    "edge": ("core.", "goal.", "simulation."),
    "profit_concentration": ("core.", "goal.", "simulation."),
    "exit_profit": ("goal.", "simulation."),
}

_SECTION_META = (
    (
        "edge",
        "去噪后每个代表机会等权投一笔，整体能不能赚、赚得够不够？",
        ("avg_roi", "win_rate", "total_profit", "payoff_ratio", "roi_p50"),
    ),
    (
        "profit_concentration",
        "利润是不是靠少数几笔 / 少数票撑起来的（是否普遍）？",
        ("top5_trade_profit_share", "top5_stock_profit_share", "avg_roi_without_top5"),
    ),
    (
        "exit_profit",
        "钱从止盈 / 止损 / 到期哪边来？（只描述结构）",
        (
            "take_profit_profit_share",
            "stop_loss_profit_share",
            "expire_profit_share",
        ),
    ),
)


class PriceSummarize(SummarizeBase):
    LAYER = "price_factor"
    KIND = SimulateKind.PRICE_FACTOR

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
        sections = cls._build_sections(gathered=gathered)
        sweep_pack = build_parameter_sweeps(
            gathered,
            layer=_LAYER,
            primary_outcome="avg_roi",
            extra_outcomes=(
                "win_rate",
                "total_profit",
                "payoff_ratio",
                "roi_p50",
            ),
            knob_prefixes=("core.", "goal.", "simulation."),
        )
        base["scope_note"] = _SCOPE_NOTE_CROSS if cross else _SCOPE_NOTE_OAAT
        base["analysis_mode"] = "cross" if cross else "oaat"
        base["sections"] = sections
        base["sweeps"] = sweep_pack.get("sweeps") or []
        base["sensitivity_rank"] = sweep_pack.get("sensitivity_rank") or []
        base["sweep_primary_outcome"] = "avg_roi"
        base["joint_sweeps"] = build_joint_heatmaps(
            gathered,
            layer=_LAYER,
            primary_outcome="avg_roi",
            groups=joint_groups,
        )
        base["upstream_bridge"] = upstream_bridge(gathered, layer=_LAYER)
        base["baseline_version_id"] = ladders.baseline_version_id(
            executed, gathered, layer=_LAYER
        )
        base["headline"] = ""
        return base

    @classmethod
    def _build_sections(
        cls,
        *,
        gathered: Optional[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        rows = ladders.ready_rows(gathered, layer=_LAYER)
        knobs = ladders.ladder_knobs(rows)
        baseline_metrics = ladders.baseline_metrics(rows, layer=_LAYER)
        baseline = ladders.baseline_row(rows)
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

            baseline_facts = _baseline_fact_lines(
                key, baseline_metrics, baseline=baseline
            )
            effect_facts = ladders.facts_from_effects(effects)
            facts = baseline_facts + effect_facts
            conclusion = (
                " ".join(baseline_facts[:2])
                if baseline_facts
                else ladders.conclusion_from_effects(effects)
            )
            if effects and baseline_facts:
                conclusion = (
                    f"{' '.join(baseline_facts[:2])} "
                    f"{ladders.conclusion_from_effects(effects)}"
                ).strip()

            sections[key] = {
                "question": question,
                "outcomes": list(outcomes),
                "effects": effects,
                "facts": facts
                or ["本格没有可用的价格层结果。"],
                "conclusion": conclusion
                or "只有基准格时，先看上方结论；在 attribution 共用 inputs 里加对照轴后再比较。",
                "suggestion": "",
            }
        return sections


def _baseline_fact_lines(
    section: str,
    metrics: Mapping[str, float],
    *,
    baseline: Optional[Mapping[str, Any]],
) -> List[str]:
    if not metrics:
        return []
    lines: List[str] = []
    if section == "edge":
        bits = []
        if "win_rate" in metrics:
            bits.append(
                f"胜率 {CampaignLabels.format_number('win_rate', metrics['win_rate'])}"
            )
        if "avg_roi" in metrics:
            bits.append(
                f"均收益 {CampaignLabels.format_number('avg_roi', metrics['avg_roi'])}"
            )
        if metrics.get("payoff_ratio") is not None:
            bits.append(
                f"盈亏比 {CampaignLabels.format_number('payoff_ratio', metrics['payoff_ratio'])}"
            )
        if metrics.get("roi_p50") is not None:
            bits.append(
                f"ROI中位 {CampaignLabels.format_number('roi_p50', metrics['roi_p50'])}"
            )
        if bits:
            lines.append("去噪后代表样本：" + "；".join(bits) + "。")
        if metrics.get("total_profit") is not None:
            lines.append(
                "等权总盈亏 "
                f"{CampaignLabels.format_number('total_profit', metrics['total_profit'])}"
                "（每笔代表机会投一单位）。"
            )
        n = None
        if baseline is not None:
            block = (baseline.get("layers") or {}).get(_LAYER) or {}
            n = block.get("total_completed_investments")
        if n is None and metrics.get("total_completed_investments") is not None:
            n = metrics.get("total_completed_investments")
        if n is not None:
            lines.append(
                f"完成笔数 {CampaignLabels.format_number('total_completed_investments', n)}。"
            )
    elif section == "profit_concentration":
        if metrics.get("top5_trade_profit_share") is not None:
            lines.append(
                "前 5 笔贡献占比 "
                f"{CampaignLabels.format_number('top5_trade_profit_share', metrics['top5_trade_profit_share'])}"
                "（分母为各笔盈亏绝对值之和）。"
            )
        if metrics.get("top5_stock_profit_share") is not None:
            lines.append(
                "前 5 只票贡献占比 "
                f"{CampaignLabels.format_number('top5_stock_profit_share', metrics['top5_stock_profit_share'])}。"
            )
        if metrics.get("avg_roi_without_top5") is not None:
            lines.append(
                "去掉前 5 笔后均收益 "
                f"{CampaignLabels.format_number('avg_roi_without_top5', metrics['avg_roi_without_top5'])}。"
            )
    elif section == "exit_profit":
        for key, label in (
            ("take_profit_profit_share", "止盈"),
            ("stop_loss_profit_share", "止损"),
            ("expire_profit_share", "到期/过期"),
        ):
            if metrics.get(key) is None:
                continue
            lines.append(
                f"{label}贡献占比 "
                f"{CampaignLabels.format_number(key, metrics[key])}。"
            )
        if any(
            metrics.get(k) is not None
            for k in (
                "take_profit_profit_share",
                "stop_loss_profit_share",
                "expire_profit_share",
            )
        ):
            lines.append(
                "以上只描述出场结构；盈利空间由止盈止损配置决定，本层不代算区间。"
            )
    return lines


__all__ = ["PriceSummarize"]
