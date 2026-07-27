"""Map stored snapshot rows → FED workbench DTO (``API.md`` V2-01 shape)."""

from __future__ import annotations

from typing import Any, Dict

from core.modules.strategy_legacy.launcher.workbench_execution_panel import (
    build_execution_panel_from_result_report,
)

# Aligns with ``SimulatorResDbCacheService`` report slot keys + UI steps (enum / price / capital).
_STEP_KEYS = ("enum", "price_factor", "portfolio")


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
    sid = int(row.get("version") or 0)
    # 无持久化快照（冷启动合成行 ``sid==0``）时约定 ``version_id`` 为空串，前端不展示工作台/目录栏。
    version_id = f"v{sid}" if sid > 0 else ""
    settings = dict(row.get("settings_snapshot") or {})
    result_report = dict(row.get("result_report") or {})
    return {
        "version_id": version_id,
        "settings": settings,
        "step_status": _step_status_from_result_report(result_report),
        "result_report": result_report,
        "execution_panel": build_execution_panel_from_result_report(result_report),
    }
