"""Load attribution ``insights`` from ``{output_dir}/analysis/report.json``."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

_EMPTY: Dict[str, Any] = {
    "available": False,
    "report_path": "",
    "insights": None,
}


def load_step_analysis(output_dir: Path) -> Dict[str, Any]:
    """Read persisted or rebuilt ``insights`` for one step output directory."""
    from core.modules.strategy.core.engines.analyzer.consts import (
        ANALYSIS_SUBDIR,
        REPORT_JSON,
    )
    from core.modules.strategy.core.engines.analyzer.insights import build_insights
    from core.modules.strategy.core.services.artifacts.io import ArtifactIO

    report_path = Path(output_dir) / ANALYSIS_SUBDIR / REPORT_JSON
    if not report_path.is_file():
        return dict(_EMPTY)
    try:
        report = ArtifactIO.read_json(report_path)
    except Exception:
        return dict(_EMPTY)
    if not isinstance(report, dict):
        return dict(_EMPTY)

    persisted = report.get("insights")
    if isinstance(persisted, dict) and str(persisted.get("headline") or "").strip():
        insights: Optional[Dict[str, Any]] = dict(persisted)
    else:
        insights = build_insights(report)

    return {
        "available": True,
        "report_path": str(report_path),
        "insights": insights,
    }


def resolve_analysis_for_step(
    strategy_name: str,
    step: str,
    slot: Optional[Dict[str, Any]],
    *,
    workbench_version: int = 0,
) -> Dict[str, Any]:
    """Resolve step ``output_dir`` candidates and load analysis payload."""
    from core.bff.APIs.strategy.helpers.report_hydrate import (
        resolve_simulation_output_dirs,
    )

    sn = str(strategy_name or "").strip()
    if not sn:
        return dict(_EMPTY)

    for output_dir in resolve_simulation_output_dirs(
        sn,
        step=str(step or "").strip(),
        slot=slot if isinstance(slot, dict) else {},
        workbench_version=int(workbench_version or 0),
    ):
        if not output_dir.is_dir():
            continue
        payload = load_step_analysis(output_dir)
        if payload.get("available"):
            return payload
    return dict(_EMPTY)


__all__ = ["load_step_analysis", "resolve_analysis_for_step"]
