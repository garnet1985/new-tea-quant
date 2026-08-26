"""Load BFF/UI attribution payload from step output directories."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from core.modules.strategy.core.services.artifacts.io import ArtifactIO

from ..steps.report import InsightBuilder
from ..support.output_dirs import SimulationOutputDirs
from ..support.paths import AnalyzerPaths

_EMPTY: Dict[str, Any] = {
    "available": False,
    "report_path": "",
    "insights": None,
}


class StepAnalysisPayload:
    @classmethod
    def from_output_dir(cls, output_dir: Path) -> Dict[str, Any]:
        report_path = AnalyzerPaths.report_json(Path(output_dir))
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
            insights = InsightBuilder.build(report)

        return {
            "available": True,
            "report_path": str(report_path),
            "insights": insights,
        }

    @classmethod
    def resolve_for_step(
        cls,
        strategy_name: str,
        step: str,
        slot: Optional[Dict[str, Any]],
        *,
        workbench_version: int = 0,
    ) -> Dict[str, Any]:
        sn = str(strategy_name or "").strip()
        if not sn:
            return dict(_EMPTY)

        for output_dir in SimulationOutputDirs.resolve(
            sn,
            step=str(step or "").strip(),
            slot=slot if isinstance(slot, dict) else {},
            workbench_version=int(workbench_version or 0),
        ):
            if not output_dir.is_dir():
                continue
            payload = cls.from_output_dir(output_dir)
            if payload.get("available"):
                return payload
        return dict(_EMPTY)
