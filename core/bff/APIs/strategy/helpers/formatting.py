"""Map stored snapshot rows → FED workbench DTO (``API.md`` V2-01 shape)."""

from __future__ import annotations

from typing import Any, Dict

from .execution_panel import build_execution_panel_from_result_report

_STEP_KEYS = ("enum", "price_factor", "portfolio")


def _step_status_from_result_report(result_report: Dict[str, Any]) -> Dict[str, Any]:
    rr = dict(result_report or {})
    out: Dict[str, Any] = {}
    for key in _STEP_KEYS:
        if key in rr and rr[key] is not None:
            out[key] = {"done": True}
        else:
            out[key] = {"done": False}
    return out


def _normalize_step_status(
    raw: Any,
    result_report: Dict[str, Any],
) -> Dict[str, Any]:
    """步进器认产物/registry 槽，不认报告正文是否 hydrate 成功。"""
    if isinstance(raw, dict) and any(key in raw for key in _STEP_KEYS):
        out: Dict[str, Any] = {}
        for key in _STEP_KEYS:
            entry = raw.get(key)
            if isinstance(entry, dict):
                out[key] = {"done": bool(entry.get("done"))}
            else:
                out[key] = {"done": False}
        return out
    return _step_status_from_result_report(result_report)


def workbench_snapshot_to_message(row: Dict[str, Any]) -> Dict[str, Any]:
    """``strategy_snapshot`` row → envelope ``message`` payload for GET …/version/latest."""
    sid = int(row.get("version") or 0)
    version_id = f"v{sid}" if sid > 0 else ""
    settings = dict(row.get("settings_snapshot") or {})
    disk_settings = dict(row.get("disk_settings") or settings)
    effective_settings = dict(row.get("effective_settings") or {})
    result_report = dict(row.get("result_report") or {})
    return {
        "version_id": version_id,
        "settings": settings,
        "disk_settings": disk_settings,
        "effective_settings": effective_settings,
        "execute_settings": dict(row.get("execute_settings") or {}),
        "settings_rev": str(row.get("settings_rev") or ""),
        "step_status": _normalize_step_status(row.get("step_status"), result_report),
        "result_report": result_report,
        "execution_panel": build_execution_panel_from_result_report(result_report),
        "env_invalid": bool(row.get("env_invalid")),
        "pinned": bool(row.get("pinned")),
    }
