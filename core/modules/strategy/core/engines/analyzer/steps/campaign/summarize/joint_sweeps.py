"""联合扫描热力图：用配置组或由多轴 overlay 推断；格点可复用 oaat/基准行。"""
from __future__ import annotations

import itertools
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from ..contrasts import KnobContrasts
from ..labels import CampaignLabels
from . import value_ladders as ladders


def build_joint_heatmaps(
    gathered: Optional[Mapping[str, Any]],
    *,
    layer: str,
    primary_outcome: str,
    groups: Sequence[Sequence[str]] = (),
) -> List[Dict[str, Any]]:
    """把多轴联合扫描收成热力图。"""
    rows = ladders.ready_rows(gathered, layer=layer)
    resolved_groups = [tuple(group) for group in groups if len(group) >= 2]
    if not resolved_groups:
        resolved_groups = _infer_groups(rows)

    out: List[Dict[str, Any]] = []
    for knobs in resolved_groups:
        if len(knobs) > 3:
            continue
        block = _one_heatmap(
            rows,
            layer=layer,
            knobs=knobs,
            primary_outcome=primary_outcome,
        )
        if block is not None:
            out.append(block)
    return out


def _infer_groups(rows: Sequence[Mapping[str, Any]]) -> List[Tuple[str, ...]]:
    seen: Dict[Tuple[str, ...], int] = {}
    for row in rows:
        overlay = row.get("overlay")
        if not isinstance(overlay, dict) or not overlay:
            continue
        paths = tuple(KnobContrasts.union_paths([overlay]))
        if 2 <= len(paths) <= 3:
            seen[paths] = seen.get(paths, 0) + 1
    return list(seen.keys())


def _one_heatmap(
    rows: Sequence[Mapping[str, Any]],
    *,
    layer: str,
    knobs: Sequence[str],
    primary_outcome: str,
) -> Optional[Dict[str, Any]]:
    level_lists: List[List[Any]] = []
    for path in knobs:
        values: List[Any] = []
        seen: set = set()
        for row in rows:
            knobs_map = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
            if path not in knobs_map:
                continue
            raw = knobs_map.get(path)
            key = ladders.value_key(raw)
            if key in seen:
                continue
            seen.add(key)
            values.append(raw)
        if len(values) < 2:
            return None
        level_lists.append(_sort_values(values))

    lookup = _row_lookup(rows, layer=layer, knobs=knobs, primary_outcome=primary_outcome)
    cells: List[Dict[str, Any]] = []
    for combo in itertools.product(*level_lists):
        key = tuple(ladders.value_key(item) for item in combo)
        hit = lookup.get(key)
        if hit is None:
            continue
        values = {path: value for path, value in zip(knobs, combo)}
        cells.append(
            {
                "values": values,
                "value_labels": {
                    path: CampaignLabels.format_knob(path, values.get(path))
                    for path in knobs
                },
                "metric": hit["metric"],
                "metric_label": hit["metric_label"],
                "version_id": hit.get("version_id"),
            }
        )
    if len(cells) < 4:
        return None

    higher_better = CampaignLabels.higher_is_better(primary_outcome)
    reverse = True if higher_better is not False else False
    ranked = sorted(cells, key=lambda item: float(item["metric"]), reverse=reverse)
    best = ranked[0]
    worst = ranked[-1]
    payload: Dict[str, Any] = {
        "knobs": list(knobs),
        "knob_labels": [CampaignLabels.knob_label(path) for path in knobs],
        "primary_outcome": primary_outcome,
        "primary_outcome_label": CampaignLabels.outcome_label(primary_outcome),
        "higher_better": higher_better,
        "cells": cells,
        "best": best,
        "worst": worst,
        "advice": (
            "联合扫描（样本内）：在 "
            + " × ".join(CampaignLabels.knob_label(p) for p in knobs)
            + f" 组合中，「{CampaignLabels.outcome_label(primary_outcome)}」较好的约 "
            + " / ".join(
                f"{CampaignLabels.knob_label(p)}={best['value_labels'].get(p)}"
                for p in knobs
            )
            + f"（{best.get('metric_label')}）。"
        ),
    }
    if len(knobs) == 2:
        grid = _matrix_2d(cells, knobs[0], knobs[1], primary_outcome)
        if grid is not None:
            payload["grid"] = grid
    return payload


def _row_lookup(
    rows: Sequence[Mapping[str, Any]],
    *,
    layer: str,
    knobs: Sequence[str],
    primary_outcome: str,
) -> Dict[Tuple[Any, ...], Dict[str, Any]]:
    out: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
    score: Dict[Tuple[Any, ...], int] = {}
    knob_set = set(knobs)
    # 优先用联合 overlay 行，其次单轴，最后基准
    ordered = sorted(
        rows,
        key=lambda row: len(
            [
                path
                for path in KnobContrasts.union_paths(
                    [row.get("overlay") if isinstance(row.get("overlay"), dict) else {}]
                )
                if path in knob_set
            ]
        ),
        reverse=True,
    )
    for row in ordered:
        knobs_map = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
        if any(path not in knobs_map for path in knobs):
            continue
        block = (row.get("layers") or {}).get(layer)
        if not isinstance(block, Mapping):
            continue
        try:
            metric = float(block.get(primary_outcome))
        except (TypeError, ValueError):
            continue
        key = tuple(ladders.value_key(knobs_map.get(path)) for path in knobs)
        overlay = row.get("overlay") if isinstance(row.get("overlay"), dict) else {}
        specificity = len(
            [path for path in KnobContrasts.union_paths([overlay]) if path in knob_set]
        )
        if key in out and score.get(key, -1) >= specificity:
            continue
        out[key] = {
            "metric": metric,
            "metric_label": CampaignLabels.format_number(primary_outcome, metric),
            "version_id": row.get("version_id"),
        }
        score[key] = specificity
    return out


def _matrix_2d(
    cells: Sequence[Mapping[str, Any]],
    row_knob: str,
    col_knob: str,
    primary_outcome: str,
) -> Optional[Dict[str, Any]]:
    row_vals: List[Any] = []
    col_vals: List[Any] = []
    seen_r: set = set()
    seen_c: set = set()
    lookup: Dict[Tuple[Any, Any], Mapping[str, Any]] = {}
    for cell in cells:
        values = cell.get("values") if isinstance(cell.get("values"), dict) else {}
        rv = values.get(row_knob)
        cv = values.get(col_knob)
        rk = ladders.value_key(rv)
        ck = ladders.value_key(cv)
        if rk not in seen_r:
            seen_r.add(rk)
            row_vals.append(rv)
        if ck not in seen_c:
            seen_c.add(ck)
            col_vals.append(cv)
        lookup[(rk, ck)] = cell

    row_vals = _sort_values(row_vals)
    col_vals = _sort_values(col_vals)
    matrix: List[List[Optional[float]]] = []
    label_matrix: List[List[str]] = []
    for rv in row_vals:
        metric_row: List[Optional[float]] = []
        label_row: List[str] = []
        for cv in col_vals:
            cell = lookup.get((ladders.value_key(rv), ladders.value_key(cv)))
            if cell is None:
                metric_row.append(None)
                label_row.append("—")
            else:
                metric_row.append(float(cell["metric"]))
                label_row.append(str(cell.get("metric_label") or "—"))
        matrix.append(metric_row)
        label_matrix.append(label_row)

    return {
        "row_knob": row_knob,
        "col_knob": col_knob,
        "row_knob_label": CampaignLabels.knob_label(row_knob),
        "col_knob_label": CampaignLabels.knob_label(col_knob),
        "row_labels": [
            CampaignLabels.format_knob(row_knob, value) for value in row_vals
        ],
        "col_labels": [
            CampaignLabels.format_knob(col_knob, value) for value in col_vals
        ],
        "matrix": matrix,
        "label_matrix": label_matrix,
        "primary_outcome": primary_outcome,
    }


def _sort_values(values: Sequence[Any]) -> List[Any]:
    def key(item: Any) -> Tuple[int, Any]:
        if item is None:
            return (2, "")
        number = KnobContrasts.scalar(item)
        if number is not None:
            return (0, float(number))
        return (1, repr(item))

    return sorted(values, key=key)


__all__ = ["build_joint_heatmaps"]
