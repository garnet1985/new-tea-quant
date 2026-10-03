"""非交叉取值阶梯：最好 / 最差 / 趋势 + 对照表（枚举与价格共用）。"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from ..contrasts import KnobContrasts
from ..labels import CampaignLabels
from ..metrics import READY


def ready_rows(
    gathered: Optional[Mapping[str, Any]],
    *,
    layer: str,
) -> List[Dict[str, Any]]:
    if not isinstance(gathered, Mapping):
        return []
    out: List[Dict[str, Any]] = []
    for row in gathered.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("status") or "") not in READY:
            continue
        block = (row.get("layers") or {}).get(layer)
        if not isinstance(block, dict):
            continue
        out.append(row)
    return out


def baseline_row(rows: Sequence[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    for row in rows:
        overlay = row.get("overlay")
        if isinstance(overlay, dict) and not overlay:
            return row
    return None


def baseline_metrics(
    rows: Sequence[Mapping[str, Any]],
    *,
    layer: str,
) -> Dict[str, float]:
    row = baseline_row(rows)
    if row is None:
        return {}
    block = (row.get("layers") or {}).get(layer)
    if not isinstance(block, Mapping):
        return {}
    out: Dict[str, float] = {}
    for key, value in block.items():
        try:
            out[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def baseline_version_id(
    executed: Optional[Mapping[str, Any]],
    gathered: Optional[Mapping[str, Any]],
    *,
    layer: str,
) -> str:
    if isinstance(executed, Mapping):
        parent = str(executed.get("parent_version_id") or "").strip()
        if parent:
            return parent
    rows = ready_rows(gathered, layer=layer)
    for row in rows:
        overlay = row.get("overlay")
        if isinstance(overlay, dict) and not overlay:
            vid = str(row.get("version_id") or "").strip()
            if vid:
                return vid
    for row in rows:
        vid = str(row.get("version_id") or "").strip()
        if vid and "-" not in vid:
            return vid
    return ""


def is_cross(
    executed: Optional[Mapping[str, Any]],
    gathered: Optional[Mapping[str, Any]],
    *,
    layer: str,
) -> bool:
    if isinstance(executed, Mapping):
        for key in ("family", "mode", "parameter_mode"):
            if str(executed.get(key) or "").strip() == "cross":
                return True
    for row in ready_rows(gathered, layer=layer):
        overlay = row.get("overlay")
        if not isinstance(overlay, dict) or not overlay:
            continue
        if len(KnobContrasts.union_paths([overlay])) > 1:
            return True
    return False


def ladder_knobs(rows: Sequence[Mapping[str, Any]]) -> List[str]:
    order: List[str] = []
    seen: set = set()
    for row in rows:
        knobs = row.get("knobs")
        if not isinstance(knobs, Mapping):
            continue
        for path in knobs:
            text = str(path)
            if text in seen:
                continue
            seen.add(text)
            order.append(text)
    usable: List[str] = []
    for path in order:
        values = {
            value_key((row.get("knobs") or {}).get(path))
            for row in rows
            if row_is_ladder_point(row, path)
        }
        if len(values) >= 2:
            usable.append(path)
    return usable


def row_is_ladder_point(row: Mapping[str, Any], knob: str) -> bool:
    overlay = row.get("overlay")
    if not isinstance(overlay, dict) or not overlay:
        return True
    return KnobContrasts.union_paths([overlay]) == [knob]


def value_ladder(
    rows: Sequence[Mapping[str, Any]],
    *,
    layer: str,
    knob: str,
    outcome: str,
) -> Dict[str, Any]:
    by_key: Dict[Any, Dict[str, Any]] = {}
    baseline = baseline_row(rows)
    baseline_value = None
    if baseline is not None:
        knobs = baseline.get("knobs") if isinstance(baseline.get("knobs"), dict) else {}
        baseline_value = knobs.get(knob)

    for row in rows:
        if not row_is_ladder_point(row, knob):
            continue
        knobs = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
        raw_val = knobs.get(knob)
        key = value_key(raw_val)
        block = (row.get("layers") or {}).get(layer)
        if not isinstance(block, Mapping):
            continue
        try:
            number = float(block.get(outcome))
        except (TypeError, ValueError):
            continue
        if key in by_key:
            continue
        by_key[key] = {
            "value": raw_val,
            "metric": number,
            "version_id": row.get("version_id"),
            "is_baseline": value_key(raw_val) == value_key(baseline_value)
            and baseline is not None,
        }
    levels = list(by_key.values())
    if len(levels) < 2:
        return {"knob": knob, "outcome": outcome, "levels": levels}
    higher_better = CampaignLabels.higher_is_better(outcome)
    reverse = True if higher_better is not False else False
    ranked = sorted(
        levels,
        key=lambda item: float(item["metric"]),
        reverse=reverse,
    )
    return {
        "knob": knob,
        "outcome": outcome,
        "higher_better": higher_better,
        "levels": sort_levels_display(levels),
        "best": ranked[0],
        "worst": ranked[-1],
    }


def sort_levels_display(levels: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    def sort_key(item: Mapping[str, Any]) -> Tuple[int, Any]:
        value = item.get("value")
        if value is None:
            return (0, "")
        scalar = KnobContrasts.scalar(value)
        if scalar is not None:
            return (1, float(scalar))
        return (2, str(value))

    return [dict(item) for item in sorted(levels, key=sort_key)]


def effect_block(
    ladder: Mapping[str, Any],
    *,
    baseline_metric: Optional[float],
) -> Optional[Dict[str, Any]]:
    levels = [dict(item) for item in (ladder.get("levels") or []) if isinstance(item, dict)]
    if len(levels) < 2:
        return None
    knob = str(ladder.get("knob") or "")
    outcome = str(ladder.get("outcome") or "")
    label = CampaignLabels.knob_label(knob)
    outcome_label = CampaignLabels.outcome_label(outcome)
    best = ladder.get("best") if isinstance(ladder.get("best"), dict) else levels[0]
    worst = ladder.get("worst") if isinstance(ladder.get("worst"), dict) else levels[-1]

    table: List[Dict[str, Any]] = []
    for level in levels:
        metric = float(level["metric"])
        delta = None if baseline_metric is None else metric - float(baseline_metric)
        table.append(
            {
                "value": level.get("value"),
                "value_label": CampaignLabels.format_knob(knob, level.get("value")),
                "metric": metric,
                "metric_label": CampaignLabels.format_number(outcome, metric),
                "delta": delta,
                "delta_label": (
                    "当前配置"
                    if level.get("is_baseline")
                    else (
                        CampaignLabels.format_delta(outcome, delta)
                        if delta is not None
                        else "—"
                    )
                ),
                "is_baseline": bool(level.get("is_baseline")),
                "version_id": level.get("version_id"),
            }
        )

    return {
        "knob": knob,
        "knob_label": label,
        "outcome": outcome,
        "outcome_label": outcome_label,
        "title": f"{label} 对「{outcome_label}」的影响",
        "max_line": f"最好情况：{CampaignLabels.format_knob(knob, best.get('value'))}",
        "min_line": f"最差情况：{CampaignLabels.format_knob(knob, worst.get('value'))}",
        "trend_line": trend_line(knob=knob, outcome=outcome, levels=levels),
        "table": table,
        "best": best,
        "worst": worst,
        "levels": levels,
        "higher_better": ladder.get("higher_better"),
    }


def trend_line(
    *,
    knob: str,
    outcome: str,
    levels: Sequence[Mapping[str, Any]],
) -> str:
    outcome_label = CampaignLabels.outcome_label(outcome)
    numeric: List[Tuple[float, float]] = []
    for level in levels:
        scalar = KnobContrasts.scalar(level.get("value"))
        if scalar is None:
            continue
        try:
            numeric.append((float(scalar), float(level["metric"])))
        except (TypeError, ValueError, KeyError):
            continue
    numeric.sort(key=lambda item: item[0])

    if len(numeric) < 2:
        off = next((item for item in levels if item.get("value") is None), None)
        ons = [item for item in levels if item.get("value") is not None]
        if off is not None and len(ons) == 1:
            on = ons[0]
            try:
                delta = float(on["metric"]) - float(off["metric"])
            except (TypeError, ValueError, KeyError):
                return "趋势：只有「未使用」与单一取值，谈不上升降关系。"
            if abs(delta) <= trend_eps(
                outcome, [float(off["metric"]), float(on["metric"])]
            ):
                return f"趋势：启用后，「{outcome_label}」几乎不变。"
            direction = "升高" if delta > 0 else "降低"
            return f"趋势：相对未使用，启用后「{outcome_label}」{direction}。"
        return "趋势：可比较数值档不足，看不出与参数的关系。"

    metrics = [item[1] for item in numeric]
    eps = trend_eps(outcome, metrics)
    non_decreasing = all(
        metrics[i] <= metrics[i + 1] + eps for i in range(len(metrics) - 1)
    )
    non_increasing = all(
        metrics[i] + eps >= metrics[i + 1] for i in range(len(metrics) - 1)
    )
    span = abs(metrics[-1] - metrics[0])
    if span <= eps:
        return f"趋势：参数越大，「{outcome_label}」几乎不变。"
    if non_decreasing and not non_increasing:
        return f"趋势：参数越大，「{outcome_label}」大致越高。"
    if non_increasing and not non_decreasing:
        return f"趋势：参数越大，「{outcome_label}」大致越低。"
    return f"趋势：「{outcome_label}」与参数取值没有明显的单调关系。"


def trend_eps(outcome: str, metrics: Sequence[float]) -> float:
    if not metrics:
        return 1e-9
    peak = max(abs(float(item)) for item in metrics) or 1.0
    last = str(outcome or "").split(".")[-1]
    if last.endswith("ratio") or last.endswith("share") or last in {
        "win_rate",
        "avg_roi",
        "total_return",
        "cv",
        "payoff_ratio",
    }:
        return max(0.005, peak * 1e-6)
    return max(0.5, peak * 1e-6)


def facts_from_effects(effects: Sequence[Mapping[str, Any]]) -> List[str]:
    facts: List[str] = []
    for effect in effects:
        label = str(effect.get("knob_label") or effect.get("knob") or "").strip()
        bits = [
            str(effect.get(key) or "").strip()
            for key in ("max_line", "min_line", "trend_line")
            if str(effect.get(key) or "").strip()
        ]
        if label and bits:
            facts.append(f"{label} — {'；'.join(bits)}")
        elif bits:
            facts.extend(bits)
    return facts


def conclusion_from_effects(effects: Sequence[Mapping[str, Any]]) -> str:
    return " ".join(facts_from_effects(effects))


def knob_allowed(knob: Any, prefixes: Optional[Sequence[str]]) -> bool:
    if not prefixes:
        return True
    text = str(knob or "").strip()
    return any(text.startswith(prefix) for prefix in prefixes)


def value_key(value: Any) -> Any:
    if value is None:
        return ("off",)
    scalar = KnobContrasts.scalar(value)
    if scalar is not None:
        return ("num", round(float(scalar), 8))
    if isinstance(value, Mapping):
        return ("map", repr(sorted(value.items(), key=lambda item: str(item[0]))))
    return ("raw", repr(value))


__all__ = [
    "baseline_metrics",
    "baseline_row",
    "baseline_version_id",
    "conclusion_from_effects",
    "effect_block",
    "facts_from_effects",
    "is_cross",
    "knob_allowed",
    "ladder_knobs",
    "ready_rows",
    "row_is_ladder_point",
    "value_ladder",
]
