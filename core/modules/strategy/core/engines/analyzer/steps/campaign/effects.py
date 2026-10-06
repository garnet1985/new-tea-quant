"""战役派生对照：边际、交叉矩形、跨层。不算 ML。"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from core.modules.analysis import Analysis

from .contrasts import KnobContrasts
from .metrics import item_delta, layer_number, outcome_value, part_value

_EQUAL_EPS = 1e-12
_ACCOUNT_FLAT = 0.005
_OPP_FLAT = 2.0
_DEFAULT_OUTCOMES = (
    ("portfolio", "total_return"),
    ("portfolio", "max_drawdown"),
    ("enumerate", "total_opportunities"),
    ("price_factor", "win_rate"),
    ("price_factor", "avg_roi"),
)


class CampaignEffects:
    """战役格子上的派生对照：边际、交叉矩形、跨层。"""

    @classmethod
    def enrich(
        cls,
        rows: Sequence[Mapping[str, Any]],
        varying_knobs: Sequence[str],
        contributions: Mapping[str, Any],
        *,
        grid_rows: Optional[Sequence[Mapping[str, Any]]] = None,
        grid_knobs: Optional[Sequence[str]] = None,
        enable_interactions: bool = True,
        enable_cross_layer: bool = True,
        outcomes: Optional[Sequence[Tuple[str, str]]] = None,
    ) -> Dict[str, Any]:
        scoped = tuple(outcomes) if outcomes else _DEFAULT_OUTCOMES
        out = dict(contributions)
        items = [
            item
            for item in (contributions.get("items") or [])
            if isinstance(item, dict)
        ]
        baseline = contributions.get("baseline")
        if not isinstance(baseline, dict):
            baseline = {}
        out["marginals"] = _build_marginals(rows, items, baseline, scoped)
        if enable_interactions:
            out["interactions"] = _build_interactions(
                grid_rows if grid_rows is not None else rows,
                list(grid_knobs) if grid_knobs is not None else varying_knobs,
                scoped,
            )
        else:
            out["interactions"] = {
                "status": "skipped",
                "reason": "layer_scope",
                "grids": [],
            }
        out["cross_layer"] = (
            _build_cross_layer(items) if enable_cross_layer else []
        )
        return out


def _primary(outcomes: Sequence[Tuple[str, str]]) -> Tuple[str, str]:
    return outcomes[0] if outcomes else ("portfolio", "total_return")


def _build_marginals(
    rows: Sequence[Mapping[str, Any]],
    items: Sequence[Mapping[str, Any]],
    baseline: Mapping[str, Any],
    outcomes: Sequence[Tuple[str, str]],
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
    primary = _primary(outcomes)
    for knob in order:
        levels = _knob_levels(knob, grouped[knob], base_row, rows, outcomes)
        if len(levels) < 2:
            continue
        best = _best_level(levels, primary)
        out.append(
            {
                "knob": knob,
                "levels": levels,
                "best_value": None if best is None else best.get("value"),
                "best_version_id": None if best is None else best.get("version_id"),
                "note": _marginal_note(levels, best, primary),
            }
        )
    return out


def _build_interactions(
    rows: Sequence[Mapping[str, Any]],
    varying_knobs: Sequence[str],
    outcomes: Sequence[Tuple[str, str]],
) -> Dict[str, Any]:
    knobs = [str(key) for key in varying_knobs]
    if len(knobs) < 2 or len(rows) < 4:
        return {"status": "skipped", "reason": "no_rectangle", "grids": []}
    primary = _primary(outcomes)
    grids: List[Dict[str, Any]] = []
    for i, row_knob in enumerate(knobs):
        for col_knob in knobs[i + 1 :]:
            grid = _rectangle(rows, knobs, row_knob, col_knob, primary)
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
        raw.append(
            {
                "knob": knob,
                "from": pick.get("from"),
                "to": pick.get("to"),
                "version_id": pick.get("version_id"),
                "opp": item_delta(pick, "enumerate", "total_opportunities"),
                "acc": item_delta(pick, "portfolio", "total_return"),
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
        out.append(
            {
                "knob": item["knob"],
                "from": item.get("from"),
                "to": item.get("to"),
                "version_id": item.get("version_id"),
                "opportunity": opp_dir,
                "account": acc_dir,
                "verdict": _verdict(opp_dir, acc_dir),
            }
        )
    return out


def _knob_levels(
    knob: str,
    items: Sequence[Mapping[str, Any]],
    base_row: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    outcomes: Sequence[Tuple[str, str]],
) -> List[Dict[str, Any]]:
    base_knobs = base_row.get("knobs") if isinstance(base_row.get("knobs"), dict) else {}
    by_value: Dict[float, Dict[str, Any]] = {}
    base_key = _num_key(base_knobs.get(knob))
    if base_key is not None:
        by_value[base_key] = _level_from_row(
            knob, base_key, base_row, outcomes, is_baseline=True
        )
    for item in items:
        key = _num_key(item.get("to"))
        if key is None or key in by_value:
            continue
        row = _row_by_version(rows, item.get("version_id"))
        if row is None:
            continue
        by_value[key] = _level_from_row(
            knob, key, row, outcomes, is_baseline=False
        )
    ordered = [by_value[key] for key in sorted(by_value)]
    base_outcomes = next(
        (level.get("outcomes") or [] for level in ordered if level.get("is_baseline")),
        None,
    )
    prev_outcomes: Optional[List[Dict[str, Any]]] = None
    for level in ordered:
        outcomes_now = level.get("outcomes") or []
        level["vs_baseline"] = _outcome_delta_list(base_outcomes, outcomes_now)
        level["vs_prev"] = _outcome_delta_list(prev_outcomes, outcomes_now)
        prev_outcomes = outcomes_now
    return ordered


def _level_from_row(
    knob: str,
    value: float,
    row: Mapping[str, Any],
    outcomes: Sequence[Tuple[str, str]],
    *,
    is_baseline: bool,
) -> Dict[str, Any]:
    layers = row.get("layers") if isinstance(row.get("layers"), dict) else {}
    return {
        "knob": knob,
        "value": value,
        "version_id": row.get("version_id"),
        "is_baseline": is_baseline,
        "outcomes": _outcomes_from_layers(layers, outcomes),
    }


def _outcomes_from_layers(
    layers: Mapping[str, Any],
    outcomes: Sequence[Tuple[str, str]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for layer, outcome in outcomes:
        value = layer_number(layers, layer, outcome)
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
        out.append({"layer": layer, "outcome": outcome, "delta": current - previous})
    return out


def _best_level(
    levels: Sequence[Mapping[str, Any]],
    primary: Tuple[str, str],
) -> Optional[Mapping[str, Any]]:
    layer, outcome = primary
    best = None
    best_ret = None
    for level in levels:
        ret = outcome_value(level.get("outcomes") or [], layer, outcome)
        if ret is None:
            continue
        if best_ret is None or ret > best_ret:
            best_ret = ret
            best = level
    return best


def _marginal_note(
    levels: Sequence[Mapping[str, Any]],
    best: Optional[Mapping[str, Any]],
    primary: Tuple[str, str],
) -> str:
    if len(levels) < 3 or best is None:
        return ""
    layer, outcome = primary
    last = levels[-1]
    last_step = part_value(last.get("vs_prev") or [], layer, outcome, field="delta")
    first_step = (
        part_value(levels[1].get("vs_prev") or [], layer, outcome, field="delta")
        if len(levels) >= 2
        else None
    )
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
    primary: Tuple[str, str],
) -> Optional[Dict[str, Any]]:
    others = [key for key in all_knobs if key not in (row_knob, col_knob)]
    groups: Dict[Tuple[Any, ...], List[Mapping[str, Any]]] = {}
    for row in rows:
        knobs = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
        freeze = tuple((key, _level_key(knobs.get(key))) for key in others)
        groups.setdefault(freeze, []).append(row)
    best: Optional[Dict[str, Any]] = None
    for freeze, group in groups.items():
        grid = _filled_grid(group, row_knob, col_knob, freeze, primary)
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
    primary: Tuple[str, str],
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
    layer, outcome = primary
    grid_cells: List[List[Dict[str, Any]]] = []
    best_cell = None
    best_ret = None
    for rk in row_keys:
        line: List[Dict[str, Any]] = []
        for ck in col_keys:
            row = cells[(rk, ck)]
            row_raw, col_raw = originals[(rk, ck)]
            layers = row.get("layers") if isinstance(row.get("layers"), dict) else {}
            score = layer_number(layers, layer, outcome)
            # present / 旧测试仍读 total_return；主结局另存 score
            account = layer_number(layers, "portfolio", "total_return")
            cell = {
                "row_value": row_raw,
                "col_value": col_raw,
                "version_id": row.get("version_id"),
                "total_return": account if account is not None else score,
                "score": score,
            }
            line.append(cell)
            if score is None:
                continue
            if best_ret is None or score > best_ret:
                best_ret = score
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
        acc = item_delta(item, "portfolio", "total_return")
        opp = item_delta(item, "enumerate", "total_opportunities")
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
