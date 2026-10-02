"""把 attribute 结果收成一份战役总结（不是 N 次 Analyzer.run）。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ...consts import SCHEMA_VERSION
from .labels import CampaignLabels

_CONTRIB_HEADLINE_OUTCOMES = (
    ("portfolio", "total_return"),
    ("portfolio", "max_drawdown"),
    ("enumerate", "total_opportunities"),
)

_LAYER_RANK = {"portfolio": 0, "price_factor": 1, "enumerate": 2}

_SKIP_REASONS = {
    "insufficient_ready_rows": "对照的格子太少。",
    "insufficient_layer_rows": "这一层没有对照数字（可能没跑到这一步）。",
    "no_numeric_outcomes": "这一层没有可对照的数字。",
    "outcome_not_varying": "这项指标在各格之间没有变化。",
    "no_varying_knobs": "各格旋钮取值相同，看不出差别。",
}


class SummarizeStep:
    """整理旋钮对照为报告主体。"""

    @classmethod
    def run(cls, attributed: Mapping[str, Any]) -> Dict[str, Any]:
        status = str(attributed.get("status") or "skipped")
        highlights = cls._highlights(attributed)
        return {
            "schema_version": SCHEMA_VERSION,
            "status": status,
            "n": int(attributed.get("n") or 0),
            "generated_at": datetime.now().isoformat(),
            "headline": cls._headline(attributed, highlights),
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
    ) -> str:
        status = str(attributed.get("status") or "skipped")
        n = int(attributed.get("n") or 0)
        reason = str(attributed.get("reason") or "")
        if reason == "insufficient_ready_rows" or n < 2:
            if n <= 0:
                return "没有可对照的回测。"
            return f"只有 {n} 套回测有结果，还不够对照。"
        top_grid = _headline_interaction(attributed)
        if top_grid is not None:
            return top_grid
        top_presence = _top_presence_contribution(attributed)
        if top_presence is not None:
            knob = CampaignLabels.knob_label(top_presence.get("knob"))
            to_text = CampaignLabels.format_knob(
                top_presence.get("knob"), top_presence.get("to")
            )
            result = CampaignLabels.outcome_label(top_presence.get("outcome"))
            delta_text = CampaignLabels.format_delta(
                top_presence.get("outcome"), top_presence.get("delta")
            )
            return f"相对关掉{knob}，打开到 {to_text} 时{result} {delta_text}。"
        top_marginal = _headline_marginal(attributed)
        if top_marginal is not None:
            return top_marginal
        top_contrib = _top_contribution(attributed)
        if top_contrib is not None:
            knob = CampaignLabels.knob_label(top_contrib.get("knob"))
            from_text = CampaignLabels.format_knob(top_contrib.get("knob"), top_contrib.get("from"))
            to_text = CampaignLabels.format_knob(top_contrib.get("knob"), top_contrib.get("to"))
            result = CampaignLabels.outcome_label(top_contrib.get("outcome"))
            delta_text = CampaignLabels.format_delta(
                top_contrib.get("outcome"), top_contrib.get("delta")
            )
            return (
                f"相对基准，把{knob}从 {from_text} 调到 {to_text}，"
                f"{result} {delta_text}。"
            )
        if status == "skipped":
            return "这次旋钮没有变化，无法对照。"
        if not highlights:
            return f"对照了 {n} 套设置，旋钮和结果之间没有清楚的方向。"
        top = highlights[0]
        rho = CampaignLabels.maybe_float(top.get("rho")) or 0.0
        knob = CampaignLabels.knob_label(top.get("knob"))
        outcome = CampaignLabels.outcome_label(top.get("outcome"))
        phrase = CampaignLabels.direction_phrase(str(top.get("outcome") or ""), rho)
        knob_path = str(top.get("knob") or "")
        if "stop_loss" in knob_path:
            phrase = CampaignLabels.direction_phrase(str(top.get("outcome") or ""), -rho)
            return f"止损越深，{outcome}{phrase}。"
        return f"{knob}越大，{outcome}{phrase}。"

    @classmethod
    def _highlights(cls, attributed: Mapping[str, Any]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        layers = attributed.get("layers") or {}
        if not isinstance(layers, dict):
            return []
        for layer, layer_block in layers.items():
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
                            "layer": str(layer),
                            "outcome": str(outcome),
                            "knob": str(knob),
                            "rho": rho,
                            "p_value": corr.get("p_value"),
                            "n": corr.get("n"),
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
        if presence.get("one_at_a_time_count") and sensitivity.get("one_at_a_time_count"):
            hints.append("同一份报告两章：参数贡献度是有/无，参数敏感度是取值变化。")
        if presence.get("one_at_a_time_count"):
            hints.append("贡献度的基准是关掉该项的那一格；一次只动这一项，才能算到它头上。")
        elif sensitivity.get("one_at_a_time_count"):
            baseline = (
                sensitivity.get("baseline")
                if isinstance(sensitivity.get("baseline"), dict)
                else {}
            )
            vid = str(baseline.get("version_id") or "").strip()
            base_label = f"v{vid}" if vid else "开着的第一套"
            hints.append(
                f"敏感度是相对基准 {base_label} 的差分："
                "一次只动一个旋钮，才能算到这个因子头上。"
            )
        elif joint_count:
            hints.append("每套同时动了多个旋钮，贡献度拆不开，只剩相关方向。")
        elif len(varying) >= 2:
            names = "、".join(CampaignLabels.knob_label(item) for item in varying[:4])
            hints.append(
                f"这张表里变过 {names}。请按行看哪一列在动；"
                "相关是把所有行混在一起算的，不是「只动了这一个」。"
            )
        if n > 0 and n < 5:
            hints.append(f"只有 {n} 套，只看方向，格数太少谈不上统计。")
        if status in ("ok", "partial") and highlights and not one_count:
            hints.append("相关不是因果。换一段行情未必如此。")
        layers = attributed.get("layers") or {}
        if isinstance(layers, dict):
            for layer, block in layers.items():
                if not isinstance(block, dict):
                    continue
                if block.get("status") != "skipped":
                    continue
                layer_reason = str(block.get("reason") or "")
                note = _SKIP_REASONS.get(layer_reason)
                if note:
                    hints.append(f"{CampaignLabels.layer_label(str(layer))}：{note}")
        if not varying and status != "skipped":
            hints.append("各套旋钮取值相同，对照看不出差别。")
        return hints


def _chapter(attributed: Mapping[str, Any], name: str) -> Dict[str, Any]:
    block = attributed.get("contributions")
    if not isinstance(block, dict):
        return {}
    nested = block.get(name)
    if isinstance(nested, dict):
        return nested
    if name == "sensitivity":
        return block
    return {}


def _contribution_items(attributed: Mapping[str, Any]) -> List[Dict[str, Any]]:
    block = _chapter(attributed, "sensitivity")
    items: List[Dict[str, Any]] = []
    for item in block.get("items") or []:
        if isinstance(item, dict) and item.get("kind") == "one_at_a_time":
            items.append(item)
    return items


def _delta_of(
    item: Mapping[str, Any],
    layer: str,
    outcome: str,
) -> Optional[float]:
    for part in item.get("deltas") or []:
        if not isinstance(part, dict):
            continue
        if str(part.get("layer") or "") != layer:
            continue
        if str(part.get("outcome") or "") != outcome:
            continue
        return CampaignLabels.maybe_float(part.get("delta"))
    return None


def _top_presence_contribution(attributed: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    block = _chapter(attributed, "presence")
    items: List[Dict[str, Any]] = []
    for item in block.get("items") or []:
        if isinstance(item, dict) and item.get("kind") == "one_at_a_time":
            items.append(item)
    return _best_delta_item(items)


def _top_contribution(attributed: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    return _best_delta_item(_contribution_items(attributed))


def _best_delta_item(items: Sequence[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    for layer, outcome in _CONTRIB_HEADLINE_OUTCOMES:
        best: Optional[Dict[str, Any]] = None
        best_abs = -1.0
        for item in items:
            delta = _delta_of(item, layer, outcome)
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
                "layer": layer,
                "outcome": outcome,
                "delta": delta,
                "version_id": item.get("version_id"),
            }
        if best is not None:
            return best
    return None


def _headline_interaction(attributed: Mapping[str, Any]) -> Optional[str]:
    contrib = _chapter(attributed, "sensitivity")
    block = contrib.get("interactions")
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


def _headline_marginal(attributed: Mapping[str, Any]) -> Optional[str]:
    contrib = _chapter(attributed, "sensitivity")
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
        base_ret = _outcome_value(base.get("outcomes") or [], "portfolio", "total_return")
        champ_ret = _outcome_value(champ.get("outcomes") or [], "portfolio", "total_return")
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
    delta_text = CampaignLabels.format_delta("total_return", delta)
    if str(block.get("note") or "") == "pullback":
        return (
            f"相对基准，{knob}放到 {to_text} 时账户收益最好（{delta_text}）；"
            "再往上调会回落。"
        )
    return (
        f"相对基准，把{knob}从 {from_text} 调到 {to_text}，"
        f"账户收益 {delta_text}。"
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


def _outcome_value(parts: Sequence[Any], layer: str, outcome: str) -> Optional[float]:
    for part in parts:
        if not isinstance(part, dict):
            continue
        if str(part.get("layer") or "") != layer:
            continue
        if str(part.get("outcome") or "") != outcome:
            continue
        return CampaignLabels.maybe_float(part.get("value"))
    return None
