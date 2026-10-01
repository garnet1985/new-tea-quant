"""把战役表交给 ``modules.analysis``（table in → struct out）。

一格一行：旋钮列 vs 三层摘要列。不跑单 version 的 FactorAnalysisPipeline。
战役格子很少，贡献度 / 敏感度用相对基准差分，不用 OLS / XGB。
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from core.modules.analysis import Analysis

from .contrasts import KnobContrasts
from .effects import CampaignEffects

_READY = frozenset({"hit", "simulated"})
_LAYERS = ("enumerate", "price_factor", "portfolio")
_CONTRIBUTION_OUTCOMES = (
    ("portfolio", "total_return"),
    ("portfolio", "max_drawdown"),
    ("enumerate", "total_opportunities"),
    ("price_factor", "win_rate"),
    ("price_factor", "avg_roi"),
)
_SKIPPED_CHAPTER = {
    "status": "skipped",
    "reason": "insufficient_ready_rows",
    "items": [],
    "one_at_a_time_count": 0,
    "joint_count": 0,
}


class AttributeStep:
    """战役归因：有/无贡献度 + 取值敏感度 + 旋钮相关 / 分桶。"""

    @classmethod
    def run(cls, gathered: Mapping[str, Any]) -> Dict[str, Any]:
        rows = [
            row
            for row in gathered.get("rows") or []
            if isinstance(row, dict) and row.get("status") in _READY
        ]
        n = len(rows)
        if n < 2:
            return {
                "status": "skipped",
                "reason": "insufficient_ready_rows",
                "n": n,
                "knobs": {},
                "layers": {},
                "contributions": {
                    "presence": dict(_SKIPPED_CHAPTER),
                    "sensitivity": dict(_SKIPPED_CHAPTER),
                },
            }

        contrasts = KnobContrasts.classify(rows)
        presence_paths = list(contrasts.get("presence") or [])
        sensitivity_paths = list(contrasts.get("sensitivity") or [])
        presence = cls._presence_chapter(rows, presence_paths)

        sensitivity_rows = [
            row
            for row in rows
            if not any(
                KnobContrasts.is_off((row.get("knobs") or {}).get(path))
                for path in presence_paths
            )
        ]
        knob_keys = _union_keys(row.get("knobs") or {} for row in rows)
        knob_profiles = {
            key: Analysis.Classical.summarize_column(_knob_scalars(rows, key))
            for key in knob_keys
        }
        varying_knobs = [
            key
            for key in sensitivity_paths
            if _is_numeric_series(_knob_scalars(sensitivity_rows, key))
            and Analysis.Classical.summarize_column(
                _knob_scalars(sensitivity_rows, key)
            ).get("role")
            == "varying"
        ]

        layers: Dict[str, Any] = {}
        for layer in _LAYERS:
            layers[layer] = cls._attribute_layer(
                sensitivity_rows, layer, varying_knobs
            )

        grid_knobs = list(dict.fromkeys([*presence_paths, *sensitivity_paths]))
        sensitivity = cls._sensitivity_chapter(
            sensitivity_rows,
            varying_knobs,
            grid_rows=rows,
            grid_knobs=grid_knobs,
        )
        contributions = {
            "presence": presence,
            "sensitivity": sensitivity,
        }
        return {
            "status": _overall_status(layers, contributions),
            "n": n,
            "knobs": knob_profiles,
            "varying_knobs": varying_knobs,
            "presence_paths": presence_paths,
            "sensitivity_paths": sensitivity_paths,
            "contributions": contributions,
        }

    @classmethod
    def _presence_chapter(
        cls,
        rows: Sequence[Mapping[str, Any]],
        presence_paths: Sequence[str],
    ) -> Dict[str, Any]:
        if not presence_paths:
            return {
                "status": "skipped",
                "reason": "no_presence_paths",
                "items": [],
                "one_at_a_time_count": 0,
                "joint_count": 0,
            }
        compare_keys = _union_keys(row.get("knobs") or {} for row in rows)
        items: List[Dict[str, Any]] = []
        baselines: Dict[str, Any] = {}
        for path in presence_paths:
            off_rows = [
                row
                for row in rows
                if KnobContrasts.is_off((row.get("knobs") or {}).get(path))
            ]
            on_rows = [
                row
                for row in rows
                if not KnobContrasts.is_off((row.get("knobs") or {}).get(path))
            ]
            if not off_rows or not on_rows:
                continue
            baseline = off_rows[0]
            base_knobs = (
                baseline.get("knobs") if isinstance(baseline.get("knobs"), dict) else {}
            )
            baselines[path] = {
                "version_id": baseline.get("version_id"),
                "knobs": {key: base_knobs.get(key) for key in compare_keys},
            }
            for row in on_rows:
                knobs = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
                changed = [
                    key
                    for key in compare_keys
                    if not KnobContrasts.values_equal(base_knobs.get(key), knobs.get(key))
                ]
                if path not in changed:
                    continue
                if changed == [path]:
                    kind = "one_at_a_time"
                else:
                    kind = "joint"
                items.append(
                    {
                        "kind": kind,
                        "version_id": row.get("version_id"),
                        "baseline_version_id": baseline.get("version_id"),
                        "changed": changed,
                        "knob": path,
                        "from": None,
                        "to": knobs.get(path),
                        "deltas": _row_deltas(baseline, row),
                    }
                )
        one_count = sum(1 for item in items if item.get("kind") == "one_at_a_time")
        joint_count = sum(1 for item in items if item.get("kind") == "joint")
        if one_count:
            status = "ok"
        elif joint_count:
            status = "partial"
        else:
            status = "skipped"
        return {
            "status": status,
            "baselines": baselines,
            "items": items,
            "one_at_a_time_count": one_count,
            "joint_count": joint_count,
        }

    @classmethod
    def _sensitivity_chapter(
        cls,
        rows: Sequence[Mapping[str, Any]],
        varying_knobs: Sequence[str],
        *,
        grid_rows: Optional[Sequence[Mapping[str, Any]]] = None,
        grid_knobs: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        skipped = {
            "status": "skipped",
            "reason": "insufficient_on_rows",
            "items": [],
            "one_at_a_time_count": 0,
            "joint_count": 0,
        }
        contributions = (
            cls._contributions(rows, varying_knobs)
            if len(rows) >= 2
            else skipped
        )
        grid = grid_rows if grid_rows is not None else rows
        knobs = list(grid_knobs) if grid_knobs is not None else varying_knobs
        if len(rows) < 2 and (len(grid) < 4 or len(knobs) < 2):
            return contributions
        return CampaignEffects.enrich(
            rows,
            varying_knobs,
            contributions,
            grid_rows=grid,
            grid_knobs=knobs,
        )

    @classmethod
    def _contributions(
        cls,
        rows: Sequence[Mapping[str, Any]],
        varying_knobs: Sequence[str],
    ) -> Dict[str, Any]:
        if len(rows) < 2:
            return {
                "status": "skipped",
                "reason": "insufficient_ready_rows",
                "items": [],
            }
        baseline = rows[0]
        base_knobs = (
            baseline.get("knobs") if isinstance(baseline.get("knobs"), dict) else {}
        )
        compare_keys = list(varying_knobs) or _union_keys(
            row.get("knobs") or {} for row in rows
        )
        items: List[Dict[str, Any]] = []
        for row in rows[1:]:
            knobs = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
            changed = [
                key
                for key in compare_keys
                if not KnobContrasts.values_equal(base_knobs.get(key), knobs.get(key))
            ]
            if len(changed) == 1:
                kind = "one_at_a_time"
            elif changed:
                kind = "joint"
            else:
                kind = "unchanged"
            knob = changed[0] if len(changed) == 1 else None
            items.append(
                {
                    "kind": kind,
                    "version_id": row.get("version_id"),
                    "baseline_version_id": baseline.get("version_id"),
                    "changed": changed,
                    "knob": knob,
                    "from": base_knobs.get(knob) if knob is not None else None,
                    "to": knobs.get(knob) if knob is not None else None,
                    "deltas": _row_deltas(baseline, row),
                }
            )
        one_count = sum(1 for item in items if item.get("kind") == "one_at_a_time")
        joint_count = sum(1 for item in items if item.get("kind") == "joint")
        if one_count:
            status = "ok"
        elif joint_count:
            status = "partial"
        else:
            status = "skipped"
        return {
            "status": status,
            "baseline": {
                "version_id": baseline.get("version_id"),
                "knobs": {key: base_knobs.get(key) for key in compare_keys},
            },
            "items": items,
            "one_at_a_time_count": one_count,
            "joint_count": joint_count,
        }

    @classmethod
    def _attribute_layer(
        cls,
        rows: Sequence[Mapping[str, Any]],
        layer: str,
        varying_knobs: Sequence[str],
    ) -> Dict[str, Any]:
        usable = [
            row
            for row in rows
            if isinstance((row.get("layers") or {}).get(layer), dict)
        ]
        if len(usable) < 2:
            return {
                "status": "skipped",
                "reason": "insufficient_layer_rows",
                "n": len(usable),
                "outcomes": {},
            }

        sample = usable[0].get("layers", {}).get(layer) or {}
        outcome_keys = [
            key
            for key in sample.keys()
            if _is_numeric_series(_series(usable, "layers", key, layer=layer))
        ]
        if not outcome_keys:
            return {
                "status": "skipped",
                "reason": "no_numeric_outcomes",
                "n": len(usable),
                "outcomes": {},
            }

        outcomes: Dict[str, Any] = {}
        for outcome in outcome_keys:
            outcomes[outcome] = cls._attribute_outcome(
                usable, layer, outcome, varying_knobs
            )

        statuses = [
            part.get("status")
            for part in outcomes.values()
            if isinstance(part, dict)
        ]
        if any(s == "ok" for s in statuses):
            status = "ok" if all(s == "ok" for s in statuses) else "partial"
        else:
            status = "skipped"
        return {
            "status": status,
            "n": len(usable),
            "outcomes": outcomes,
        }

    @classmethod
    def _attribute_outcome(
        cls,
        rows: Sequence[Mapping[str, Any]],
        layer: str,
        outcome: str,
        varying_knobs: Sequence[str],
    ) -> Dict[str, Any]:
        y_raw = _series(rows, "layers", outcome, layer=layer)
        profile = Analysis.Classical.summarize_column(y_raw)
        if profile.get("role") != "varying" or profile.get("dtype") != "numeric":
            return {
                "status": "skipped",
                "reason": "outcome_not_varying",
                "profile": profile,
                "fields": {},
            }
        if not varying_knobs:
            return {
                "status": "skipped",
                "reason": "no_varying_knobs",
                "profile": profile,
                "fields": {},
            }

        fields: Dict[str, Any] = {}
        for knob in varying_knobs:
            x_raw = _knob_scalars(rows, knob)
            xs, ys = _aligned_numeric(x_raw, y_raw)
            wins = [value > 0.0 for value in ys]
            fields[knob] = {
                "n": len(xs),
                "correlation": Analysis.Classical.spearman_correlation(xs, ys),
                "buckets": Analysis.Classical.quantile_buckets(xs, ys, wins),
            }

        field_ok = any(
            (part.get("correlation") or {}).get("status") == "ok"
            for part in fields.values()
        )
        return {
            "status": "ok" if field_ok else "skipped",
            "profile": profile,
            "fields": fields,
        }


def _series(
    rows: Sequence[Mapping[str, Any]],
    group: str,
    key: str,
    *,
    layer: Optional[str] = None,
) -> List[Any]:
    out: List[Any] = []
    for row in rows:
        if group == "knobs":
            out.append(_knob_scalar(row, key))
            continue
        layers = row.get("layers") or {}
        block = layers.get(layer) if layer else None
        out.append(block.get(key) if isinstance(block, dict) else None)
    return out


def _knob_scalar(row: Mapping[str, Any], key: str) -> Optional[float]:
    block = row.get("knobs") or {}
    raw = block.get(key) if isinstance(block, dict) else None
    if KnobContrasts.is_off(raw):
        return None
    return KnobContrasts.scalar(raw)


def _knob_scalars(rows: Sequence[Mapping[str, Any]], key: str) -> List[Any]:
    return [_knob_scalar(row, key) for row in rows]


def _union_keys(blocks: Sequence[Any]) -> List[str]:
    keys: List[str] = []
    seen = set()
    for block in blocks:
        if not isinstance(block, dict):
            continue
        for key in block:
            if key in seen:
                continue
            seen.add(key)
            keys.append(str(key))
    return keys


def _is_numeric_series(values: Sequence[Any]) -> bool:
    profile = Analysis.Classical.summarize_column(values)
    return profile.get("dtype") == "numeric"


def _aligned_numeric(
    xs: Sequence[Any],
    ys: Sequence[Any],
) -> Tuple[List[float], List[float]]:
    out_x: List[float] = []
    out_y: List[float] = []
    for x, y in zip(xs, ys):
        cx = Analysis.Classical.coerce_float(x)
        cy = Analysis.Classical.coerce_float(y)
        if cx is None or cy is None:
            continue
        out_x.append(cx)
        out_y.append(cy)
    return out_x, out_y


def _row_deltas(
    baseline: Mapping[str, Any],
    row: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    base_layers = (
        baseline.get("layers") if isinstance(baseline.get("layers"), dict) else {}
    )
    row_layers = row.get("layers") if isinstance(row.get("layers"), dict) else {}
    out: List[Dict[str, Any]] = []
    for layer, outcome in _CONTRIBUTION_OUTCOMES:
        before = _layer_number(base_layers, layer, outcome)
        after = _layer_number(row_layers, layer, outcome)
        if before is None or after is None:
            continue
        out.append(
            {
                "layer": layer,
                "outcome": outcome,
                "baseline": before,
                "value": after,
                "delta": after - before,
            }
        )
    return out


def _layer_number(
    layers: Mapping[str, Any],
    layer: str,
    outcome: str,
) -> Optional[float]:
    block = layers.get(layer)
    if not isinstance(block, dict):
        return None
    return Analysis.Classical.coerce_float(block.get(outcome))


def _overall_status(
    layers: Mapping[str, Any],
    contributions: Mapping[str, Any],
) -> str:
    statuses = [
        part.get("status")
        for part in layers.values()
        if isinstance(part, dict)
    ]
    for name in ("presence", "sensitivity"):
        chapter = contributions.get(name)
        if isinstance(chapter, dict) and chapter.get("status"):
            statuses.append(chapter.get("status"))
    if any(status == "ok" for status in statuses):
        return "ok" if all(status == "ok" for status in statuses) else "partial"
    return "skipped"
