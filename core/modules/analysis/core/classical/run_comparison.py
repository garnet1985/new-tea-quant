"""Compare decision-space summaries between two attribution runs."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def compare_run_summaries(
    current: Dict[str, Any],
    baseline: Dict[str, Any],
) -> Dict[str, Any]:
    current_version_id = str(current.get("version_id") or "")
    baseline_version_id = str(baseline.get("version_id") or "")
    if not current_version_id or not baseline_version_id:
        return {
            "status": "skipped",
            "reason": "missing_version_id",
            "current_version_id": current_version_id or None,
            "baseline_version_id": baseline_version_id or None,
        }

    current_space = current.get("decision_space") or {}
    baseline_space = baseline.get("decision_space") or {}
    settings_diff = _diff_settings(
        current_space.get("declared_core") or {},
        baseline_space.get("declared_core") or {},
    )
    capture_diff = _diff_capture(
        current_space.get("capture") or {},
        baseline_space.get("capture") or {},
    )
    coverage_diff = _diff_coverage(
        current.get("coverage") or {},
        baseline.get("coverage") or {},
    )

    return {
        "status": "ok",
        "current_version_id": current_version_id,
        "baseline_version_id": baseline_version_id,
        "settings_diff": settings_diff,
        "capture_diff": capture_diff,
        "coverage_diff": coverage_diff,
        "has_meaningful_diff": bool(settings_diff or capture_diff or coverage_diff),
    }


def _diff_settings(
    current: Dict[str, Any],
    baseline: Dict[str, Any],
) -> List[Dict[str, Any]]:
    keys = sorted(set(current) | set(baseline))
    out: List[Dict[str, Any]] = []
    for key in keys:
        current_entry = current.get(key) if isinstance(current.get(key), dict) else {}
        baseline_entry = baseline.get(key) if isinstance(baseline.get(key), dict) else {}
        current_value = current_entry.get("value")
        baseline_value = baseline_entry.get("value")
        if current_value == baseline_value:
            continue
        out.append(
            {
                "key": key,
                "current": current_value,
                "baseline": baseline_value,
                "role": current_entry.get("role") or baseline_entry.get("role"),
            }
        )
    return out


def _diff_capture(
    current: Dict[str, Any],
    baseline: Dict[str, Any],
) -> List[Dict[str, Any]]:
    keys = sorted(set(current) | set(baseline))
    out: List[Dict[str, Any]] = []
    for key in keys:
        current_entry = current.get(key) if isinstance(current.get(key), dict) else {}
        baseline_entry = baseline.get(key) if isinstance(baseline.get(key), dict) else {}
        if not current_entry and not baseline_entry:
            continue
        diff = _diff_capture_entry(key, current_entry, baseline_entry)
        if diff is not None:
            out.append(diff)
    return out


def _diff_capture_entry(
    key: str,
    current: Dict[str, Any],
    baseline: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    current_role = current.get("role")
    baseline_role = baseline.get("role")
    if current_role != baseline_role:
        return {
            "key": key,
            "kind": "role_changed",
            "current_role": current_role,
            "baseline_role": baseline_role,
        }

    if current_role == "constant":
        current_value = current.get("value")
        baseline_value = baseline.get("value")
        if current_value == baseline_value:
            return None
        return {
            "key": key,
            "kind": "constant_value_changed",
            "current": current_value,
            "baseline": baseline_value,
        }

    if current_role == "varying":
        current_range = {
            "min": current.get("min"),
            "max": current.get("max"),
            "count": current.get("count"),
            "unique_count": current.get("unique_count"),
        }
        baseline_range = {
            "min": baseline.get("min"),
            "max": baseline.get("max"),
            "count": baseline.get("count"),
            "unique_count": baseline.get("unique_count"),
        }
        if current_range == baseline_range:
            return None
        return {
            "key": key,
            "kind": "varying_range_changed",
            "current": current_range,
            "baseline": baseline_range,
        }

    if not current or not baseline:
        return {
            "key": key,
            "kind": "presence_changed",
            "current_role": current_role,
            "baseline_role": baseline_role,
        }
    return None


def _diff_coverage(
    current: Dict[str, Any],
    baseline: Dict[str, Any],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    keys = sorted(set(current) | set(baseline))
    for key in keys:
        current_value = current.get(key)
        baseline_value = baseline.get(key)
        if current_value == baseline_value:
            continue
        out.append(
            {
                "key": key,
                "current": current_value,
                "baseline": baseline_value,
            }
        )
    return out


__all__ = ["compare_run_summaries"]
