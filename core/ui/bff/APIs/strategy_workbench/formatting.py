"""Map stored snapshot rows → FED workbench DTO (``API.md`` V2-01 shape)."""

from __future__ import annotations

from typing import Any, Dict

# Aligns with ``SimulatorResDbCacheService`` report slot keys + UI steps (enum / price / capital).
_STEP_KEYS = ("enum", "price_factor", "capital_allocation")


def _step_status_from_result_report(result_report: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key in _STEP_KEYS:
        if key in result_report and result_report[key] is not None:
            out[key] = {"done": True}
        else:
            out[key] = {"done": False}
    return out


def workbench_snapshot_to_message(row: Dict[str, Any]) -> Dict[str, Any]:
    """``strategy_snapshot`` row → envelope ``message`` payload for GET …/version/latest."""
    sid = int(row.get("snapshot_id") or row.get("version") or 0)
    version_id = f"v{sid}" if sid > 0 else "v0"
    settings = dict(row.get("settings_snapshot") or {})
    result_report = dict(row.get("result_report") or row.get("reports") or {})
    return {
        "version_id": version_id,
        "settings": settings,
        "step_status": _step_status_from_result_report(result_report),
        "result_report": result_report,
    }
