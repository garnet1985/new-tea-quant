#!/usr/bin/env python3
"""Calendar slice enumerator flow implementation (Reader / Compute v2)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.progress import (
    filter_open_dates_in_range,
    normalize_calendar_progress_mode,
    resolve_calendar_progress_plan,
)
from core.modules.strategy.engines.simulator.enumerator.shared.progress_axis import (
    progress_axis_for_calendar_mode,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.orchestrator import (
    load_stock_infos_for_ids,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.slice_plan import (
    SLICE_STEPS_AUTO_ESTIMATE,
    build_calendar_slice_dispatch_job,
)
from core.modules.strategy.engines.simulator.enumerator.shared.services import (
    EnumeratorSharedServices,
)


class CalendarSlicedEnumeratorServices(EnumeratorSharedServices):
    def build_jobs(
        self,
        *,
        strategy_name: str,
        settings_payload: Dict[str, Any],
        output_dir: Any,
        worker_ref: Dict[str, str],
        stock_ids: Optional[List[str]] = None,
        entities_per_job: int = 1,
    ) -> List[Dict[str, Any]]:
        _ = entities_per_job
        target_stock_ids = stock_ids if stock_ids is not None else self.stock_list
        settings_view = StrategySettingsView.from_dict(settings_payload)
        if settings_view.simulation_settings.execution_mode != "calendar_slice":
            raise ValueError("CalendarSlicedEnumeratorServices 需要 simulation.execution_mode=calendar_slice")
        job = build_calendar_slice_dispatch_job(
            strategy_name=strategy_name,
            settings_payload=settings_payload,
            output_dir=str(output_dir),
            worker_ref=worker_ref,
            stock_ids=list(target_stock_ids),
            start_date=self.start_date,
            end_date=self.end_date,
        )
        return [job]

    def enrich_calendar_dispatch_jobs(
        self,
        jobs: List[Dict[str, Any]],
        *,
        settings_payload: Dict[str, Any],
        calendar_dict: Dict[str, Any],
    ) -> None:
        if not jobs:
            return
        job = jobs[0]
        if job.get("enumeration_execution_mode") != "calendar_slice":
            return
        raw_open = calendar_dict.get("open_dates") if isinstance(calendar_dict, dict) else []
        open_dates = filter_open_dates_in_range(
            raw_open if isinstance(raw_open, list) else [],
            self.start_date,
            self.end_date,
        )
        progress_mode = normalize_calendar_progress_mode(
            (settings_payload.get("enumerator") or {}).get("calendar_progress_mode")
        )
        plan = resolve_calendar_progress_plan(
            open_dates=open_dates,
            slice_open_days=SLICE_STEPS_AUTO_ESTIMATE,
            progress_mode=progress_mode,
        )
        plan["progress_axis"] = progress_axis_for_calendar_mode(plan["calendar_progress_mode"])
        stock_ids = [str(s).strip() for s in (job.get("stock_ids") or []) if str(s).strip()]
        stock_infos = load_stock_infos_for_ids(stock_ids)
        for row in jobs:
            row.update(plan)
            if stock_infos:
                row["stock_infos"] = stock_infos
            if self.workbench_strategy_name:
                row["workbench_strategy_name"] = self.workbench_strategy_name
            if self.workbench_run_id:
                row["workbench_run_id"] = self.workbench_run_id

    def resolve_enum_progress_total(self, jobs: List[Dict[str, Any]]) -> int:
        if jobs and jobs[0].get("enumeration_execution_mode") == "calendar_slice":
            return int(jobs[0].get("calendar_progress_total") or 1)
        return super().resolve_enum_progress_total(jobs)

    def progress_units_from_execute_report(self, report: Any) -> tuple[int, int, int]:
        from core.modules.strategy.services.execution.enum_job_pipeline import (
            calendar_progress_units_from_execute_report,
        )

        return calendar_progress_units_from_execute_report(report)


__all__ = ["CalendarSlicedEnumeratorServices"]
