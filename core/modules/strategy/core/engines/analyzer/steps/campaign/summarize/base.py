"""把 attribute 结果收成一份战役总结。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Mapping, Optional, Sequence

from core.modules.strategy.core.enums import SimulateKind

from ....consts import SCHEMA_VERSION
from ..attribute import AttributeStep
from ..labels import CampaignLabels
from ..metrics import item_delta, outcome_value

_LAYER_RANK = {"portfolio": 0, "price_factor": 1, "enumerate": 2}

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
        highlights = cls._highlights(attributed, layer=focus)
        return {
            "schema_version": SCHEMA_VERSION,
            "status": str(attributed.get("status") or "skipped"),
            "n": int(attributed.get("n") or 0),
            "layer": focus,
            "generated_at": datetime.now().isoformat(),
            "headline": cls._headline(attributed, highlights, layer=focus),
            "highlights": highlights,
            "hints": cls._hints(attributed, highlights),
            "varying_knobs": list(attributed.get("varying_knobs") or []),
            "contributions": attributed.get("contributions") or {},
        }

    @classmethod
    def _headline(
        cls,
        attributed: Mapping[str, Any],
        highlights: Sequence[Mapping[str, Any]],
        *,
        layer: str = "",
    ) -> str:
        status = str(attributed.get("status") or "skipped")
        n = int(attributed.get("n") or 0)
        reason = str(attributed.get("reason") or "")
        if reason == "insufficient_ready_rows" or n < 2:
            if n <= 0:
                return "没有可对照的回测。"
            return f"只有 {n} 次回测有结果，还不够对照。"
        if AttributeStep.for_layer(layer).ENABLE_INTERACTIONS:
            top_grid = _headline_interaction(attributed)
            if top_grid is not None:
                return top_grid
        top_presence = _best_oat(_chapter(attributed, "presence"), layer=layer)
        if top_presence is not None:
            return _oat_line(top_presence)
        top_marginal = _headline_marginal(attributed, layer=layer)
        if top_marginal is not None:
            return top_marginal
        top_contrib = _best_oat(_chapter(attributed, "sensitivity"), layer=layer)
        if top_contrib is not None:
            return f"相对基准回测，{_oat_line(top_contrib)}"
        if status == "skipped":
            return "这次参数没有变化，无法对照。"
        if not highlights:
            return f"对照了 {n} 次回测，参数与结果之间没有清楚的方向。"
        top = highlights[0]
        rho = CampaignLabels.maybe_float(top.get("rho")) or 0.0
        knob = CampaignLabels.knob_label(top.get("knob"))
        outcome = CampaignLabels.outcome_label(top.get("outcome"))
        knob_path = str(top.get("knob") or "")
        signed = -rho if "stop_loss" in knob_path else rho
        phrase = CampaignLabels.direction_phrase(str(top.get("outcome") or ""), signed)
        if "stop_loss" in knob_path:
            return f"止损越深，{outcome}{phrase}。"
        return f"{knob}越大，{outcome}{phrase}。"

    @classmethod
    def _highlights(
        cls,
        attributed: Mapping[str, Any],
        *,
        layer: str = "",
    ) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        layers = attributed.get("layers") or {}
        if not isinstance(layers, dict):
            return []
        focus = str(layer or "").strip()
        for layer_name, layer_block in layers.items():
            if focus and str(layer_name) != focus:
                continue
            if not isinstance(layer_block, dict):
                continue
            outcomes = layer_block.get("outcomes") or {}
            if not isinstance(outcomes, dict):
                continue
            for outcome, outcome_block in outcomes.items():
                if not isinstance(outcome_block, dict):
                    continue
                fields = outcome_block.get("fields") or {}
                if not isinstance(fields, dict):
                    continue
                for knob, field in fields.items():
                    if not isinstance(field, dict):
                        continue
                    corr = field.get("correlation") or {}
                    if corr.get("status") != "ok":
                        continue
                    rho = CampaignLabels.maybe_float(corr.get("rho"))
                    if rho is None:
                        continue
                    rows.append(
                        {
                            "layer": str(layer_name),
                            "outcome": str(outcome),
                            "knob": str(knob),
                            "rho": rho,
                        }
                    )
        rows.sort(
            key=lambda item: (
                _LAYER_RANK.get(str(item.get("layer")), 9),
                -abs(float(item["rho"])),
            )
        )
        return rows[:5]

    @classmethod
    def _hints(
        cls,
        attributed: Mapping[str, Any],
        highlights: Sequence[Mapping[str, Any]],
    ) -> List[str]:
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
        if status in ("ok", "partial") and highlights and not one_count:
            hints.append("相关不是因果。换一段行情未必如此。")
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


def _oat_line(item: Mapping[str, Any]) -> str:
    knob = CampaignLabels.knob_label(item.get("knob"))
    from_text = CampaignLabels.format_knob(item.get("knob"), item.get("from"))
    to_text = CampaignLabels.format_knob(item.get("knob"), item.get("to"))
    result = CampaignLabels.outcome_label(item.get("outcome"))
    delta_text = CampaignLabels.format_delta(item.get("outcome"), item.get("delta"))
    return f"把{knob}从 {from_text} 改为 {to_text}，{result} {delta_text}。"


def _best_oat(
    chapter: Mapping[str, Any],
    *,
    layer: str = "",
) -> Optional[Dict[str, Any]]:
    items = [
        item
        for item in (chapter.get("items") or [])
        if isinstance(item, dict) and item.get("kind") == "one_at_a_time"
    ]
    return _best_delta_item(items, layer=layer)


def _headline_outcomes(layer: str = "") -> Sequence[tuple]:
    return AttributeStep.for_layer(layer).OUTCOMES


def _best_delta_item(
    items: Sequence[Mapping[str, Any]],
    *,
    layer: str = "",
) -> Optional[Dict[str, Any]]:
    for layer_name, outcome in _headline_outcomes(layer):
        best: Optional[Dict[str, Any]] = None
        best_abs = -1.0
        for item in items:
            delta = item_delta(item, layer_name, outcome)
            if delta is None:
                continue
            magnitude = abs(delta)
            if magnitude <= 1e-12 or magnitude < best_abs:
                continue
            best_abs = magnitude
            best = {
                "knob": item.get("knob"),
                "from": item.get("from"),
                "to": item.get("to"),
                "layer": layer_name,
                "outcome": outcome,
                "delta": delta,
                "version_id": item.get("version_id"),
            }
        if best is not None:
            return best
    return None


def _headline_interaction(attributed: Mapping[str, Any]) -> Optional[str]:
    block = _chapter(attributed, "sensitivity").get("interactions")
    if not isinstance(block, dict) or str(block.get("status") or "") != "ok":
        return None
    grids = [grid for grid in (block.get("grids") or []) if isinstance(grid, dict)]
    if not grids:
        return None
    grid = grids[0]
    best = grid.get("best") if isinstance(grid.get("best"), dict) else {}
    ret = CampaignLabels.maybe_float(best.get("total_return"))
    if ret is None:
        return None
    row_knob = str(grid.get("row_knob") or "")
    col_knob = str(grid.get("col_knob") or "")
    return (
        f"{CampaignLabels.knob_label(row_knob)} "
        f"{CampaignLabels.format_knob(row_knob, best.get('row_value'))} × "
        f"{CampaignLabels.knob_label(col_knob)} "
        f"{CampaignLabels.format_knob(col_knob, best.get('col_value'))} "
        f"时账户收益最好（{CampaignLabels.format_number('total_return', ret)}）。"
    )


def _headline_marginal(
    attributed: Mapping[str, Any],
    *,
    layer: str = "",
) -> Optional[str]:
    contrib = _chapter(attributed, "sensitivity")
    outcomes = list(_headline_outcomes(layer))
    if not outcomes:
        return None
    primary_layer, primary_outcome = outcomes[0]
    picked = None
    best_span = -1.0
    for block in contrib.get("marginals") or []:
        if not isinstance(block, dict):
            continue
        levels = [item for item in (block.get("levels") or []) if isinstance(item, dict)]
        base = next((item for item in levels if item.get("is_baseline")), None)
        champ = _level_by_value(levels, block.get("best_value"))
        if base is None or champ is None:
            continue
        base_ret = outcome_value(base.get("outcomes") or [], primary_layer, primary_outcome)
        champ_ret = outcome_value(
            champ.get("outcomes") or [], primary_layer, primary_outcome
        )
        if base_ret is None or champ_ret is None:
            continue
        span = abs(champ_ret - base_ret)
        if span <= 1e-12 or span < best_span:
            continue
        best_span = span
        picked = (block, base, champ, champ_ret - base_ret)
    if picked is None:
        return None
    block, base, champ, delta = picked
    knob = CampaignLabels.knob_label(block.get("knob"))
    from_text = CampaignLabels.format_number(block.get("knob"), base.get("value"))
    to_text = CampaignLabels.format_number(block.get("knob"), champ.get("value"))
    label = CampaignLabels.outcome_label(primary_outcome)
    delta_text = CampaignLabels.format_delta(primary_outcome, delta)
    if str(block.get("note") or "") == "pullback":
        return (
            f"相对基准回测，{knob}取 {to_text} 时{label}最好（{delta_text}）；"
            "再增大该参数，这项指标会回落。"
        )
    return (
        f"相对基准回测，把{knob}从 {from_text} 改为 {to_text}，"
        f"{label} {delta_text}。"
    )


def _level_by_value(
    levels: Sequence[Mapping[str, Any]],
    value: Any,
) -> Optional[Mapping[str, Any]]:
    target = CampaignLabels.maybe_float(value)
    if target is None:
        return None
    for item in levels:
        current = CampaignLabels.maybe_float(item.get("value"))
        if current is None:
            continue
        if abs(current - target) < 1e-12:
            return item
    return None
