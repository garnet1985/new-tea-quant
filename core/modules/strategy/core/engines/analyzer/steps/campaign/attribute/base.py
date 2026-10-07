"""战役归因基类：presence / sensitivity / 差分共用；旋钮范围与结局由子类声明。"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from core.modules.analysis import Analysis

from ..contrasts import KnobContrasts
from ..metrics import READY, layer_number

_SKIPPED = {
    "status": "skipped",
    "reason": "insufficient_ready_rows",
    "items": [],
    "one_at_a_time_count": 0,
    "joint_count": 0,
}


class AttributeBase:
    """一层战役归因。子类只声明本层 settings 段、结局与是否做交叉对照。"""

    LAYER: str = ""
    KNOB_PREFIXES: Tuple[str, ...] = ()
    OUTCOMES: Tuple[Tuple[str, str], ...] = ()

    @classmethod
    def accepts_knob(cls, path: Any) -> bool:
        """该路径是否属于本层要看的旋钮。"""
        text = str(path or "").strip()
        if not text:
            return False
        if not cls.KNOB_PREFIXES:
            return True
        for prefix in cls.KNOB_PREFIXES:
            root = prefix[:-1] if prefix.endswith(".") else prefix
            if text == root or text.startswith(prefix):
                return True
        return False

    @classmethod
    def filter_knobs(cls, paths: Sequence[Any]) -> List[str]:
        """留下本层接受的旋钮路径。"""
        out: List[str] = []
        seen = set()
        for path in paths:
            text = str(path or "").strip()
            if not text or text in seen or not cls.accepts_knob(text):
                continue
            seen.add(text)
            out.append(text)
        return out

    @classmethod
    def run(cls, gathered: Mapping[str, Any]) -> Dict[str, Any]:
        """对本层已完成的格子做归因。"""
        rows = [
            row
            for row in gathered.get("rows") or []
            if isinstance(row, dict) and row.get("status") in READY
        ]
        n = len(rows)
        focus = cls.LAYER
        if n < 2:
            return {
                "status": "skipped",
                "reason": "insufficient_ready_rows",
                "n": n,
                "layer": focus,
                "layers": {},
                "contributions": {
                    "presence": dict(_SKIPPED),
                    "sensitivity": dict(_SKIPPED),
                },
            }

        contrasts = KnobContrasts.classify(rows)
        presence_paths = cls.filter_knobs(contrasts.get("presence") or [])
        sensitivity_paths = cls.filter_knobs(contrasts.get("sensitivity") or [])
        presence = cls._presence_chapter(rows, presence_paths)

        sensitivity_rows = [
            row
            for row in rows
            if not any(
                KnobContrasts.is_off((row.get("knobs") or {}).get(path))
                for path in presence_paths
            )
        ]
        varying_knobs = [
            key
            for key in sensitivity_paths
            if _is_varying(_knob_scalars(sensitivity_rows, key))
        ]
        layers = {focus: cls._attribute_layer(sensitivity_rows, varying_knobs)}
        sensitivity = cls._sensitivity_chapter(sensitivity_rows, varying_knobs)
        contributions = {"presence": presence, "sensitivity": sensitivity}
        return {
            "status": _overall_status(layers, contributions),
            "n": n,
            "layer": focus,
            "layers": layers,
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
        compare_keys = cls.filter_knobs(
            _union_keys(row.get("knobs") or {} for row in rows)
        )
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
            seen_on: set = set()
            for row in on_rows:
                knobs = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
                fingerprint = _knob_fingerprint(knobs, compare_keys)
                if fingerprint in seen_on:
                    continue
                seen_on.add(fingerprint)
                changed = [
                    key
                    for key in compare_keys
                    if not KnobContrasts.values_equal(base_knobs.get(key), knobs.get(key))
                ]
                if path not in changed:
                    continue
                kind = "one_at_a_time" if changed == [path] else "joint"
                items.append(
                    {
                        "kind": kind,
                        "version_id": row.get("version_id"),
                        "baseline_version_id": baseline.get("version_id"),
                        "changed": changed,
                        "knob": path,
                        "from": None,
                        "to": knobs.get(path),
                        "deltas": cls._row_deltas(baseline, row),
                    }
                )
        return _chapter_result(items, baselines=baselines)

    @classmethod
    def _sensitivity_chapter(
        cls,
        rows: Sequence[Mapping[str, Any]],
        varying_knobs: Sequence[str],
    ) -> Dict[str, Any]:
        if len(rows) < 2:
            return {
                "status": "skipped",
                "reason": "insufficient_on_rows",
                "items": [],
                "one_at_a_time_count": 0,
                "joint_count": 0,
            }
        return cls._contributions(rows, varying_knobs)

    @classmethod
    def _contributions(
        cls,
        rows: Sequence[Mapping[str, Any]],
        varying_knobs: Sequence[str],
    ) -> Dict[str, Any]:
        if len(rows) < 2:
            return {"status": "skipped", "reason": "insufficient_ready_rows", "items": []}
        baseline = rows[0]
        base_knobs = (
            baseline.get("knobs") if isinstance(baseline.get("knobs"), dict) else {}
        )
        compare_keys = list(varying_knobs) or cls.filter_knobs(
            _union_keys(row.get("knobs") or {} for row in rows)
        )
        items: List[Dict[str, Any]] = []
        for row in rows[1:]:
            knobs = row.get("knobs") if isinstance(row.get("knobs"), dict) else {}
            changed = [
                key
                for key in compare_keys
                if not KnobContrasts.values_equal(base_knobs.get(key), knobs.get(key))
            ]
            if not changed:
                continue
            kind = "one_at_a_time" if len(changed) == 1 else "joint"
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
                    "deltas": cls._row_deltas(baseline, row),
                }
            )
        result = _chapter_result(items)
        result["baseline"] = {
            "version_id": baseline.get("version_id"),
            "knobs": {key: base_knobs.get(key) for key in compare_keys},
        }
        return result

    @classmethod
    def _attribute_layer(
        cls,
        rows: Sequence[Mapping[str, Any]],
        varying_knobs: Sequence[str],
    ) -> Dict[str, Any]:
        del varying_knobs
        layer = cls.LAYER
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
        return {"status": "ok", "n": len(usable), "outcomes": {}}

    @classmethod
    def _row_deltas(
        cls,
        baseline: Mapping[str, Any],
        row: Mapping[str, Any],
    ) -> List[Dict[str, Any]]:
        base_layers = (
            baseline.get("layers") if isinstance(baseline.get("layers"), dict) else {}
        )
        row_layers = row.get("layers") if isinstance(row.get("layers"), dict) else {}
        out: List[Dict[str, Any]] = []
        for layer_name, outcome in cls.OUTCOMES:
            before = layer_number(base_layers, layer_name, outcome)
            after = layer_number(row_layers, layer_name, outcome)
            if before is None or after is None:
                continue
            out.append(
                {
                    "layer": layer_name,
                    "outcome": outcome,
                    "baseline": before,
                    "value": after,
                    "delta": after - before,
                }
            )
        return out


def _chapter_result(
    items: Sequence[Mapping[str, Any]],
    *,
    baselines: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    one_count = sum(1 for item in items if item.get("kind") == "one_at_a_time")
    joint_count = sum(1 for item in items if item.get("kind") == "joint")
    if one_count:
        status = "ok"
    elif joint_count:
        status = "partial"
    else:
        status = "skipped"
    out: Dict[str, Any] = {
        "status": status,
        "items": list(items),
        "one_at_a_time_count": one_count,
        "joint_count": joint_count,
    }
    if baselines is not None:
        out["baselines"] = baselines
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
            text = str(key)
            if text in seen:
                continue
            seen.add(text)
            keys.append(text)
    return keys


def _is_varying(values: Sequence[Any]) -> bool:
    profile = Analysis.Classical.summarize_column(values)
    return (
        profile.get("dtype") == "numeric"
        and profile.get("role") == "varying"
    )


def _knob_fingerprint(
    knobs: Mapping[str, Any],
    keys: Sequence[str],
) -> Tuple[Any, ...]:
    parts: List[Tuple[str, Any]] = []
    for key in keys:
        raw = knobs.get(key)
        if KnobContrasts.is_off(raw):
            parts.append((key, None))
            continue
        scalar = KnobContrasts.scalar(raw)
        if scalar is not None:
            parts.append((key, round(float(scalar), 12)))
        else:
            parts.append((key, repr(raw)))
    return tuple(parts)


def _overall_status(
    layers: Mapping[str, Any],
    contributions: Mapping[str, Any],
) -> str:
    statuses = [
        part.get("status") for part in layers.values() if isinstance(part, dict)
    ]
    for name in ("presence", "sensitivity"):
        chapter = contributions.get(name)
        if isinstance(chapter, dict) and chapter.get("status"):
            statuses.append(chapter.get("status"))
    if any(status == "ok" for status in statuses):
        return "ok" if all(status == "ok" for status in statuses) else "partial"
    return "skipped"
