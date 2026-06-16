#!/usr/bin/env python3
"""枚举器进度语义：entity_timeline（股票/bundle）与 calendar_slice（开市日/分片）。"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

ENTITY_PROGRESS_MODE_STOCK = "stock"
ENTITY_PROGRESS_MODE_BUNDLE = "bundle"
KNOWN_ENTITY_PROGRESS_MODES = frozenset({ENTITY_PROGRESS_MODE_STOCK, ENTITY_PROGRESS_MODE_BUNDLE})

PROGRESS_AXIS_ENTITY_STOCK = "entity_stock"
PROGRESS_AXIS_ENTITY_BUNDLE = "entity_bundle"
PROGRESS_AXIS_CALENDAR_OPEN_DATE = "calendar_open_date"
PROGRESS_AXIS_CALENDAR_SLICE = "calendar_slice"


def normalize_entity_progress_mode(raw: Any) -> str:
    mode = str(raw or ENTITY_PROGRESS_MODE_STOCK).strip().lower()
    if mode in KNOWN_ENTITY_PROGRESS_MODES:
        return mode
    return ENTITY_PROGRESS_MODE_STOCK


def progress_axis_for_entity_mode(mode: str) -> str:
    if normalize_entity_progress_mode(mode) == ENTITY_PROGRESS_MODE_BUNDLE:
        return PROGRESS_AXIS_ENTITY_BUNDLE
    return PROGRESS_AXIS_ENTITY_STOCK


def progress_axis_for_calendar_mode(mode: str) -> str:
    from core.modules.strategy.engines.simulator.enumerator.calendar_slice.progress import (
        CALENDAR_PROGRESS_MODE_SLICE,
        normalize_calendar_progress_mode,
    )

    if normalize_calendar_progress_mode(mode) == CALENDAR_PROGRESS_MODE_SLICE:
        return PROGRESS_AXIS_CALENDAR_SLICE
    return PROGRESS_AXIS_CALENDAR_OPEN_DATE


def resolve_entity_progress_plan(
    jobs: List[Dict[str, Any]],
    *,
    progress_mode: str,
) -> Dict[str, Any]:
    from core.modules.strategy.engines.simulator.enumerator.dispatch_jobs import (
        count_stocks_in_dispatch_jobs,
    )

    mode = normalize_entity_progress_mode(progress_mode)
    stock_total = count_stocks_in_dispatch_jobs(jobs)
    bundle_total = len(jobs)
    total = bundle_total if mode == ENTITY_PROGRESS_MODE_BUNDLE else stock_total
    return {
        "entity_progress_mode": mode,
        "entity_progress_total": max(1, int(total)),
        "entity_stock_total": int(stock_total),
        "entity_bundle_total": int(bundle_total),
        "progress_axis": progress_axis_for_entity_mode(mode),
    }


def enrich_entity_dispatch_jobs(
    jobs: List[Dict[str, Any]],
    *,
    settings_payload: Dict[str, Any],
    workbench_strategy_name: str | None = None,
    workbench_run_id: str | None = None,
) -> None:
    if not jobs:
        return
    enumerator = settings_payload.get("enumerator") if isinstance(settings_payload, dict) else {}
    plan = resolve_entity_progress_plan(
        jobs,
        progress_mode=(enumerator or {}).get("entity_progress_mode"),
    )
    for row in jobs:
        row.update(plan)
        if workbench_strategy_name:
            row["workbench_strategy_name"] = workbench_strategy_name
        if workbench_run_id:
            row["workbench_run_id"] = workbench_run_id


def enumeration_progress_metadata(jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not jobs:
        return {}
    job = jobs[0]
    if job.get("enumeration_execution_mode") == "calendar_slice":
        mode = str(job.get("calendar_progress_mode") or "open_date")
        return {
            "progress_axis": progress_axis_for_calendar_mode(mode),
            "calendar_progress_mode": mode,
            "enumeration_execution_mode": "calendar_slice",
        }
    mode = str(job.get("entity_progress_mode") or ENTITY_PROGRESS_MODE_STOCK)
    return {
        "progress_axis": progress_axis_for_entity_mode(mode),
        "entity_progress_mode": mode,
        "enumeration_execution_mode": "entity_timeline",
    }


def entity_progress_units_from_execute_report(
    report: Any,
    *,
    progress_mode: str,
) -> Tuple[int, int, int]:
    """entity_timeline：stock=按股计数；bundle=每个 dispatch job 计 1。"""
    from core.modules.strategy.services.execution.enum_job_pipeline import (
        _progress_units_from_execute_report,
    )

    if normalize_entity_progress_mode(progress_mode) == ENTITY_PROGRESS_MODE_BUNDLE:
        ok = 1 if getattr(report, "success", False) else 0
        fail = 0 if ok else 1
        return ok + fail, ok, fail
    return _progress_units_from_execute_report(report)


__all__ = [
    "ENTITY_PROGRESS_MODE_BUNDLE",
    "ENTITY_PROGRESS_MODE_STOCK",
    "KNOWN_ENTITY_PROGRESS_MODES",
    "PROGRESS_AXIS_CALENDAR_OPEN_DATE",
    "PROGRESS_AXIS_CALENDAR_SLICE",
    "PROGRESS_AXIS_ENTITY_BUNDLE",
    "PROGRESS_AXIS_ENTITY_STOCK",
    "enrich_entity_dispatch_jobs",
    "enumeration_progress_metadata",
    "entity_progress_units_from_execute_report",
    "normalize_entity_progress_mode",
    "progress_axis_for_calendar_mode",
    "progress_axis_for_entity_mode",
    "resolve_entity_progress_plan",
]
