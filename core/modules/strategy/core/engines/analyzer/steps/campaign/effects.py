"""战役格子上的派生对照：边际、交叉矩形、跨层。不算 ML。"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from core.modules.analysis import Analysis

from .contrasts import KnobContrasts

_EQUAL_EPS = 1e-12
_ACCOUNT_FLAT = 0.005
_OPP_FLAT = 2.0
_PRICE_FLAT = 0.005
_OUTCOMES = (
    ("portfolio", "total_return"),
    ("portfolio", "max_drawdown"),
    ("enumerate", "total_opportunities"),
    ("price_factor", "win_rate"),
    ("price_factor", "avg_roi"),
)


class CampaignEffects:
    """战役格子上的派生对照：边际、交叉矩形、跨层。不算 ML。"""

    @classmethod
    def enrich(
        cls,
        rows: Sequence[Mapping[str, Any]],
        varying_knobs: Sequence[str],
        contributions: Mapping[str, Any],
    ) -> Dict[str, Any]:
        out = dict(contributions)
        items = [
            item
            for item in (contributions.get("items") or [])
            if isinstance(item, dict)
        ]
        baseline = contributions.get("baseline")
        if not isinstance(baseline, dict):
            baseline = {}
        out["marginals"] = _build_marginals(rows, items, baseline)
        out["interactions"] = _build_interactions(rows, varying_knobs)
        out["cross_layer"] = _build_cross_layer(items)
        return out


def _build_marginals(
    rows: Sequence[Mapping[str, Any]],
    items: Sequence[Mapping[str, Any]],
    baseline: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    base_row = _row_by_version(rows, baseline.get("version_id"))
    if base_row is None and rows:
        base_row = rows[0]
    if base_row is None:
        return []
    grouped: Dict[str, List[Mapping[str, Any]]] = {}
    order: List[str] = []
    for item in items:
        if item.get("kind") != "one_at_a_time":
            continue
        knob = str(item.get("knob") or "")
        if not knob:
            continue
        if knob not in grouped:
            grouped[knob] = []
            order.append(knob)
        grouped[knob].append(item)
    out: List[Dict[str, Any]] = []
    for knob in order:
        levels = _knob_levels(knob, grouped[knob], base_row, rows)
        if len(levels) < 2:
            continue
        best = _best_level(levels)
        out.append(
            {
                "knob": knob,
                "levels": levels,
                "best_value": None if best is None else best.get("value"),
                "best_version_id": None if best is None else best.get("version_id"),
                "note": _marginal_note(levels, best),
            }
        )
    return out


def _build_interactions(
    rows: Sequence[Mapping[str, Any]],
    varying_knobs: Sequence[str],
) -> Dict[str, Any]:
    knobs = [str(key) for key in varying_knobs]
    if len(knobs) < 2 or len(rows) < 4:
        return {"status": "skipped", "reason": "no_rectangle", "grids": []}
    grids: List[Dict[str, Any]] = []
    for i, row_knob in enumerate(knobs):
        for col_knob in knobs[i + 1 :]:
            grid = _rectangle(rows, knobs, row_knob, col_knob)
            if grid is not None:
                grids.append(grid)
    if not grids:
        return {"status": "skipped", "reason": "no_rectangle", "grids": []}
    grids.sort(key=lambda item: int(item.get("n_cells") or 0), reverse=True)
    return {"status": "ok", "grids": grids[:1]}


def _build_cross_layer(items: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = {}
    order: List[str] = []
    for item in items:
        if item.get("kind") != "one_at_a_time":
            continue
        knob = str(item.get("knob") or "")
        if not knob:
            continue
        if knob not in grouped:
            grouped[knob] = []
            order.append(knob)
        grouped[knob].append(item)
    raw: List[Dict[str, Any]] = []
    for knob in order:
        pick = _pick_cross_item(grouped[knob])
        if pick is None:
            continue
        opp = _delta_of(pick, "enumerate", "total_opportunities")
        acc = _delta_of(pick, "portfolio", "total_return")
        price = _delta_of(pick, "price_factor", "avg_roi")
        if price is None:
            price = _delta_of(pick, "price_factor", "win_rate")
        raw.append(
            {
                "knob": knob,
                "from": pick.get("from"),
                "to": pick.get("to"),
                "version_id": pick.get("version_id"),
                "opp": opp,
                "acc": acc,
                "price": price,
            }
        )
    max_acc = 0.0
    for item in raw:
        acc = item.get("acc")
        if acc is not None:
            max_acc = max(max_acc, abs(float(acc)))
    acc_flat = max(_ACCOUNT_FLAT, 0.05 * max_acc)
    out: List[Dict[str, Any]] = []
    for item in raw:
        opp_dir = _direction(item.get("opp"), _OPP_FLAT)
        acc_dir = _direction(item.get("acc"), acc_flat)
        price_dir = (
            "missing"
            if item.get("price") is None
            else _direction(item.get("price"), _PRICE_FLAT)
        )
        out.append(
            {
                "knob": item["knob"],
                "from": item.get("from"),
                "to": item.get("to"),
                "version_id": item.get("version_id"),
                "opportunity": opp_dir,
                "account": acc_dir,
                "price": price_dir,
                "verdict": _verdict(opp_dir, acc_dir),
            }
        )
    return out


def _knob_levels(
    knob: str,
    items: Sequence[Mapping[str, Any]],
    base_row: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    base_knobs = base_row.get("knobs") if isinstance(base_row.get("knobs"), dict) else {}
    by_value: Dict[float, Dict[str, Any]] = {}
    base_key = _num_key(base_knobs.get(knob))
    if base_key is not None:
        by_value[base_key] = _level_from_row(
            knob, base_key, base_row, is_baseline=True
        )
    for item in items:
        key = _num_key(item.get("to"))
        if key is None or key in by_value:
            continue
        row = _row_by_version(rows, item.get("version_id"))
        if row is None:
            continue
        by_value[key] = _level_from_row(knob, key, row, is_baseline=False)
    ordered = [by_value[key] for key in sorted(by_value)]
    prev_outcomes: Optional[List[Dict[str, Any]]] = None
    base_outcomes = None
    for level in ordered:
        if level.get("is_baseline"):
            base_outcomes = level.get("outcomes") or []
            break
    for level in ordered:
        outcomes = level.get("outcomes") or []
        level["vs_baseline"] = _outcome_delta_list(base_outcomes, outcomes)
        level["vs_prev"] = _outcome_delta_list(prev_outcomes, outcomes)
        prev_outcomes = outcomes
    return ordered


def _level_from_row(
    knob: str,
    value: float,
    row: Mapping[str, Any],
    *,
    is_baseline: bool,
) -> Dict[str, Any]:
    layers = row.get("layers") if isinstance(row.get("layers"), dict) else {}
    return _level_from_payload(
        knob, value, row.get("version_id"), layers, is_baseline=is_baseline
    )


def _level_from_payload(
    knob: str,
    value: float,
    version_id: Any,
    layers: Mapping[str, Any],
    *,
    is_baseline: bool,
) -> Dict[str, Any]:
    return {
        "knob": knob,
        "value": value,
        "version_id": version_id,
        "is_baseline": is_baseline,
        "outcomes": _outcomes_from_layers(layers),
    }


def _outcomes_from_layers(layers: Mapping[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for layer, outcome in _OUTCOMES:
        value = _layer_number(layers, layer, outcome)
        if value is None:
            continue
        out.append({"layer": layer, "outcome": outcome, "value": value})
    return out


def _outcome_delta_list(
    before: Optional[Sequence[Mapping[str, Any]]],
    after: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    if before is None:
        return []
    before_map = {
        (str(part.get("layer")), str(part.get("outcome"))): Analysis.Classical.coerce_float(
            part.get("value")
        )
        for part in before
        if isinstance(part, dict)
    }
    out: List[Dict[str, Any]] = []
    for part in after:
        layer = str(part.get("layer") or "")
        outcome = str(part.get("outcome") or "")
        current = Analysis.Classical.coerce_float(part.get("value"))
        previous = before_map.get((layer, outcome))
        if current is None or previous is None:
            continue
        out.append(
            {
                "layer": layer,
                "outcome": outcome,
                "delta": current - previous,
            }
        )
    return out


def _best_level(levels: Sequence[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    best = None
    best_ret = None
    for level in levels:
        ret = _level_outcome(level, "portfolio", "total_return")
        if ret is None:
            continue
        if best_ret is None or ret > best_ret:
            best_ret = ret
            best = level
    return best


def _marginal_note(
    levels: Sequence[Mapping[str, Any]],
    best: Optional[Mapping[str, Any]],
) -> str:
    if len(levels) < 3 or best is None:
        return ""
    last = levels[-1]
    last_step = _list_delta(last.get("vs_prev") or [], "portfolio", "total_return")
    first_step = None
    if len(levels) >= 2:
        first_step = _list_delta(levels[1].get("vs_prev") or [], "portfolio", "total_return")
    last_value = _num_key(last.get("value"))
    best_value = _num_key(best.get("value"))
    if last_value is None or best_value is None:
        return ""
    if abs(last_value - best_value) < _EQUAL_EPS:
        return ""
    if first_step is None or first_step <= _ACCOUNT_FLAT:
        return ""
    if last_step is None:
        return ""
    if last_step < -_ACCOUNT_FLAT or last_step < 0.5 * first_step:
        return "pullback"
    return ""


def _rectangle(
    rows: Sequence[Mapping[str, Any]],
    all_knobs: Sequence[str],
    row_knob: str,
    col_knob: str,
) -> Optional[Dict[str, Any]]:
    others = [key for key in all_knobs if key not in (row_knob, col_knob)]
    groups: Dict[Tuple[Any, ...], List[Mapping[str, Any]]] = {}
    for row in rows:
        knobs = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
        freeze = tuple((key, _level_key(knobs.get(key))) for key in others)
        groups.setdefault(freeze, []).append(row)
    best: Optional[Dict[str, Any]] = None
    for freeze, group in groups.items():
        grid = _filled_grid(group, row_knob, col_knob, freeze)
        if grid is None:
            continue
        if best is None or int(grid.get("n_cells") or 0) > int(best.get("n_cells") or 0):
            best = grid
    return best


def _filled_grid(
    rows: Sequence[Mapping[str, Any]],
    row_knob: str,
    col_knob: str,
    freeze: Sequence[Tuple[str, Any]],
) -> Optional[Dict[str, Any]]:
    cells: Dict[Tuple[Any, Any], Mapping[str, Any]] = {}
    originals: Dict[Tuple[Any, Any], Tuple[Any, Any]] = {}
    for row in rows:
        knobs = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
        row_raw = knobs.get(row_knob)
        col_raw = knobs.get(col_knob)
        row_key = _level_key(row_raw)
        col_key = _level_key(col_raw)
        if row_key is None or col_key is None:
            return None
        key = (row_key, col_key)
        if key in cells:
            return None
        cells[key] = row
        originals[key] = (row_raw, col_raw)
    row_keys = sorted({item[0] for item in cells})
    col_keys = sorted({item[1] for item in cells})
    if len(row_keys) < 2 or len(col_keys) < 2:
        return None
    if len(cells) != len(row_keys) * len(col_keys):
        return None
    for rk in row_keys:
        for ck in col_keys:
            if (rk, ck) not in cells:
                return None
    grid_cells: List[List[Dict[str, Any]]] = []
    best_cell = None
    best_ret = None
    for rk in row_keys:
        line: List[Dict[str, Any]] = []
        for ck in col_keys:
            row = cells[(rk, ck)]
            row_raw, col_raw = originals[(rk, ck)]
            ret = _layer_number(
                row.get("layers") if isinstance(row.get("layers"), dict) else {},
                "portfolio",
                "total_return",
            )
            cell = {
                "row_value": row_raw,
                "col_value": col_raw,
                "version_id": row.get("version_id"),
                "total_return": ret,
            }
            line.append(cell)
            if ret is None:
                continue
            if best_ret is None or ret > best_ret:
                best_ret = ret
                best_cell = cell
        grid_cells.append(line)
    held = {key: value for key, value in freeze if value is not None}
    return {
        "row_knob": row_knob,
        "col_knob": col_knob,
        "row_values": [originals[(rk, col_keys[0])][0] for rk in row_keys],
        "col_values": [originals[(row_keys[0], ck)][1] for ck in col_keys],
        "held": held,
        "cells": grid_cells,
        "n_cells": len(cells),
        "best": None
        if best_cell is None
        else {
            "row_value": best_cell.get("row_value"),
            "col_value": best_cell.get("col_value"),
            "version_id": best_cell.get("version_id"),
            "total_return": best_cell.get("total_return"),
        },
    }


def _pick_cross_item(
    items: Sequence[Mapping[str, Any]],
) -> Optional[Mapping[str, Any]]:
    best = None
    best_abs = -1.0
    for item in items:
        acc = _delta_of(item, "portfolio", "total_return")
        opp = _delta_of(item, "enumerate", "total_opportunities")
        score = 0.0
        if acc is not None:
            score = max(score, abs(acc))
        if opp is not None:
            score = max(score, abs(opp) / 1000.0)
        if best is None or score > best_abs:
            best_abs = score
            best = item
    return best


def _verdict(opportunity: str, account: str) -> str:
    if opportunity == "up" and account == "up":
        return "aligned"
    if opportunity == "up" and account in ("flat", "down"):
        return "finds_not_pays"
    if opportunity == "flat" and account == "up":
        return "pays_not_finds"
    if opportunity == "down" and account == "up":
        return "filter"
    if opportunity == "down" and account == "down":
        return "worse"
    if opportunity == "flat" and account == "down":
        return "hurts"
    return "idle"


def _direction(delta: Optional[float], flat: float) -> str:
    if delta is None:
        return "missing"
    if abs(delta) < flat:
        return "flat"
    return "up" if delta > 0 else "down"


def _delta_of(
    item: Mapping[str, Any],
    layer: str,
    outcome: str,
) -> Optional[float]:
    return _list_delta(item.get("deltas") or [], layer, outcome)


def _list_delta(parts: Sequence[Any], layer: str, outcome: str) -> Optional[float]:
    for part in parts:
        if not isinstance(part, dict):
            continue
        if str(part.get("layer") or "") != layer:
            continue
        if str(part.get("outcome") or "") != outcome:
            continue
        return Analysis.Classical.coerce_float(part.get("delta"))
    return None


def _level_outcome(
    level: Mapping[str, Any],
    layer: str,
    outcome: str,
) -> Optional[float]:
    for part in level.get("outcomes") or []:
        if not isinstance(part, dict):
            continue
        if str(part.get("layer") or "") != layer:
            continue
        if str(part.get("outcome") or "") != outcome:
            continue
        return Analysis.Classical.coerce_float(part.get("value"))
    return None


def _row_by_version(
    rows: Sequence[Mapping[str, Any]],
    version_id: Any,
) -> Optional[Mapping[str, Any]]:
    vid = str(version_id or "").strip()
    if not vid:
        return None
    for row in rows:
        if str(row.get("version_id") or "").strip() == vid:
            return row
    return None


def _layer_number(
    layers: Mapping[str, Any],
    layer: str,
    outcome: str,
) -> Optional[float]:
    block = layers.get(layer)
    if not isinstance(block, dict):
        return None
    return Analysis.Classical.coerce_float(block.get(outcome))


def _level_key(value: Any) -> Optional[Tuple[Any, ...]]:
    if KnobContrasts.is_off(value):
        return ("off",)
    number = KnobContrasts.scalar(value)
    if number is None:
        return None
    return ("num", round(float(number), 10))


def _num_key(value: Any) -> Optional[float]:
    number = KnobContrasts.scalar(value)
    if number is None:
        return None
    return round(float(number), 10)
