"""Workbench snapshot UI 读模型 — 磁盘层在 Strategy，此处补 result_report hydrate。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    StrategyInfo,
)
from core.modules.strategy.core.services.workbench_snapshots import (
    WorkbenchSnapshots as _CoreSnapshots,
)

from core.bff.APIs.strategy.helpers.report_hydrate import (
    hydrate_workbench_result_report,
)


class WorkbenchSnapshots(_CoreSnapshots):
    """BFF：磁盘 snapshot + UI hydrate。"""

    @classmethod
    def _enrich_row(
        cls,
        strategy_name: str,
        info: StrategyInfo,
        row: Dict[str, Any],
    ) -> Dict[str, Any]:
        out = super()._enrich_row(strategy_name, info, row)
        rr = out.get("result_report") or out.get("reports") or {}
        if isinstance(rr, dict):
            out["result_report"] = hydrate_workbench_result_report(
                strategy_name,
                rr,
                workbench_version=int(out.get("version") or 0),
            )
        return out


__all__ = ["WorkbenchSnapshots"]
