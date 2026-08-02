#!/usr/bin/env python3
"""Run BE idle performance cases (entity_based / slice_based).

Requires ``data_gen.py`` + ``db_creation.py`` (DuckDB under ``.workdir/``).
Work is driven by ``RunCallbacks.on_tick`` (BE has no public ``execute_fn``).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_SCRIPTS = Path(__file__).resolve().parent
_REPO = _SCRIPTS.parents[4]  # .../scripts → repo root
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from common import (  # noqa: E402
    CSV_CALENDAR,
    FAKE_DATA_DIR,
    RESULTS_DIR,
    active_duckdb_entry,
    dataset_files_present,
    ensure_layout,
    read_dataset_meta,
    read_universe,
    utc_now_iso,
)
from progress import Progress, step  # noqa: E402


def _open_dates() -> List[str]:
    path = FAKE_DATA_DIR / CSV_CALENDAR
    rows = list(csv.DictReader(path.open("r", encoding="utf-8")))
    return [r["cal_date"] for r in rows if str(r.get("is_open")) in ("1", "1.0")]


def _attach_perf_duckdb() -> Dict[str, Any]:
    from core.infra.db import Db
    from core.modules.data_manager import DataManager

    entry = active_duckdb_entry()
    if not entry:
        raise SystemExit("no perf duckdb; run db_creation.py first")
    paths = entry.get("paths") or {}
    cfg = Db.duckdb.overlay_domain_paths(
        data=paths.get("data"),
        tag=paths.get("tag"),
        strategy=paths.get("strategy"),
    )
    Db.manager.reset_default()
    db = Db.manager.create(cfg, is_verbose=False)
    db.initialize()
    Db.manager.set_default(db)
    DataManager.reset_instance()
    DataManager(db=db, is_verbose=False)
    return entry


def _idle_on_tick(ctx, point: str, index: int) -> None:
    _ = (ctx, point, index)


def _idle_on_ticks_complete(ctx, timeline) -> Dict[str, Any]:
    """Return per-job tick/entity counts so ProcessPool runs stay measurable."""
    points = list(getattr(timeline, "points", None) or [])
    payload = getattr(ctx, "payload", None) or {}
    entities = payload.get("entities_count")
    if entities is None:
        ents = payload.get("entity_specified") or payload.get("entity_ids") or []
        entities = len(ents) if isinstance(ents, list) else 0
    return {
        "tick_count": len(points),
        "entities_in_job": int(entities or 0),
    }


def _sum_job_result_ints(result, key: str) -> int:
    total = 0
    for report in list(getattr(result, "job_results", None) or []):
        data = getattr(report, "data", None)
        if isinstance(data, dict) and key in data:
            total += int(data.get(key) or 0)
    return total


def _metrics_from_result(
    *,
    case_id: str,
    mode: str,
    wall: float,
    result,
    entities: int,
    timeline_points: int,
    expected_jobs: int,
    expected_ticks: int,
) -> Dict[str, Any]:
    completed = int(getattr(result, "completed_jobs", 0) or 0)
    total_jobs = int(getattr(result, "total_jobs", 0) or 0)
    tick_count = _sum_job_result_ints(result, "tick_count")
    entities_driven = _sum_job_result_ints(result, "entities_in_job")
    ok = bool(getattr(result, "success", False))
    warnings: List[str] = []
    if total_jobs != expected_jobs:
        warnings.append(
            f"total_jobs={total_jobs} != expected_jobs={expected_jobs}"
        )
    if completed != expected_jobs:
        warnings.append(
            f"completed_jobs={completed} != expected_jobs={expected_jobs}"
        )
    if tick_count != expected_ticks:
        warnings.append(
            f"tick_count={tick_count} != expected_ticks={expected_ticks}"
        )
    if warnings:
        ok = False
        for w in warnings:
            step("test", f"WARNING {case_id}: {w}")
    return {
        "case_id": case_id,
        "mode": mode,
        "wall_time_s": wall,
        "jobs_submitted_bundle": 1,
        "jobs": total_jobs,
        "expected_jobs": expected_jobs,
        "entities": entities,
        "entities_driven": entities_driven,
        "timeline_points": timeline_points,
        "tick_count": tick_count,
        "expected_ticks": expected_ticks,
        "success": ok,
        "completed_jobs": completed,
        "failed_jobs": int(getattr(result, "failed_jobs", 0) or 0),
        "elapsed_seconds": float(getattr(result, "elapsed_seconds", 0.0) or 0.0),
        "warnings": warnings,
    }


def _preflight_io(ids: Sequence[str], start: str, end: str) -> Dict[str, Any]:
    """Load daily klines in the main process (DuckDB file lock blocks worker reopen)."""
    from core.modules.data_manager import DataManager

    dm = DataManager.get_instance()
    if dm is None:
        raise SystemExit("DataManager missing after duckdb attach")
    step(
        "test",
        f"io_preflight load_raw for {len(ids)} entities "
        f"window={start}..{end}",
    )
    prog = Progress("test/io_preflight", len(ids), unit="entities")
    t0 = time.perf_counter()
    total_rows = 0
    for sid in ids:
        rows = dm.stock.kline.load_raw(sid, "daily", start, end) or []
        total_rows += len(rows)
        prog.update(1)
    prog.finish(extra=f"rows={total_rows:,}")
    return {
        "io_preflight_s": time.perf_counter() - t0,
        "io_preflight_rows": total_rows,
        "io_preflight_entities": len(ids),
    }


def _run_entity(
    ids: Sequence[str],
    timeline: Sequence[str],
    *,
    callbacks,
    entities_per_job: int,
) -> Dict[str, Any]:
    from core.modules.backtest_engine import BacktestEngine

    # BE entity planner is bundle-mode: only jobs[0].entity_specified is used,
    # then split by entities_per_job. Do NOT pre-split into many jobs.
    jobs = [
        {
            "id": "entity_bundle",
            "payload": {"entity_specified": [{"id": sid} for sid in ids]},
        }
    ]
    expected_jobs = max(1, math.ceil(len(ids) / max(1, entities_per_job)))
    expected_ticks = expected_jobs * len(timeline)
    step(
        "test",
        f"idle_entity_based: entities={len(ids)} "
        f"expected_batches≈{expected_jobs} (epj={entities_per_job}) "
        f"timeline={len(timeline)} expected_ticks≈{expected_ticks:,}",
    )
    t0 = time.perf_counter()
    result = BacktestEngine.entity_based.run(
        jobs,
        start=timeline[0],
        end=timeline[-1],
        timeline=list(timeline),
        performance={
            "max_workers": 1,
            "entities_per_job": entities_per_job,
            "force_main_process": True,
            "dispatch_probe": False,
            "mb_per_entity_staged": 1.0,
        },
        task_name="be_perf_idle_entity",
        callbacks=callbacks,
        enable_progress_display=True,
    )
    wall = time.perf_counter() - t0
    step("test", f"idle_entity_based finished in {wall:.2f}s")
    return _metrics_from_result(
        case_id="idle_entity_based",
        mode="entity_based",
        wall=wall,
        result=result,
        entities=len(ids),
        timeline_points=len(timeline),
        expected_jobs=expected_jobs,
        expected_ticks=expected_ticks,
    )


def _run_slice(
    ids: Sequence[str],
    timeline: Sequence[str],
    *,
    callbacks,
) -> Dict[str, Any]:
    from core.modules.backtest_engine import BacktestEngine

    jobs = [
        {
            "id": "slice_bulk",
            "payload": {
                "entity_ids": list(ids),
                "timeline_point_count": len(timeline),
            },
        }
    ]
    # Idle TimelineWorkerExecute drives the full axis once per bulk job.
    # It does NOT multiply by entity count; slice plan slices are for business
    # execute_fn, not this idle path. So ~timeline_points ticks is expected.
    expected_jobs = 1
    expected_ticks = len(timeline)
    step(
        "test",
        f"idle_slice_based: entities={len(ids)} bulk_jobs=1 "
        f"timeline={len(timeline)} expected_ticks={expected_ticks:,} "
        "(idle path = one full Timeline.drive, not per-entity)",
    )
    t0 = time.perf_counter()
    result = BacktestEngine.slice_based.run(
        jobs,
        start=timeline[0],
        end=timeline[-1],
        timeline=list(timeline),
        performance={
            "max_workers": 1,
            "force_main_process": True,
            "dispatch_probe": False,
        },
        task_name="be_perf_idle_slice",
        callbacks=callbacks,
        enable_progress_display=True,
    )
    wall = time.perf_counter() - t0
    step("test", f"idle_slice_based finished in {wall:.2f}s")
    return _metrics_from_result(
        case_id="idle_slice_based",
        mode="slice_based",
        wall=wall,
        result=result,
        entities=len(ids),
        timeline_points=len(timeline),
        expected_jobs=expected_jobs,
        expected_ticks=expected_ticks,
    )


def _write_report(case: Dict[str, Any], *, with_io: bool, db_entry: dict) -> Path:
    ensure_layout()
    out_dir = RESULTS_DIR / "_local" / str(case["case_id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = read_dataset_meta()
    report = {
        "case_name": case["case_id"],
        "run_date": utc_now_iso(),
        "module": "modules.backtest_engine",
        "description": (
            f"BE idle {case['mode']}; "
            + ("on_tick loads daily klines" if with_io else "on_tick noop")
        ),
        "dataset": meta,
        "db": {
            "engine": db_entry.get("engine"),
            "name": db_entry.get("name"),
            "paths": db_entry.get("paths"),
        },
        "metrics": case,
    }
    (out_dir / "metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    md = out_dir / "REPORT.md"
    md.write_text(
        "\n".join(
            [
                f"# Performance Report — {case['case_id']}",
                "",
                f"- date: {report['run_date']}",
                f"- mode: {case['mode']}",
                f"- wall_time_s: {case['wall_time_s']:.4f}",
                f"- entities: {case.get('entities')} (driven={case.get('entities_driven')})",
                f"- jobs: {case.get('jobs')} / expected {case.get('expected_jobs')}",
                f"- ticks: {case.get('tick_count')} / expected {case.get('expected_ticks')}",
                f"- timeline_points: {case.get('timeline_points')}",
                f"- success: {case.get('success')}",
                f"- with_io: {with_io}",
                f"- db: {report['db'].get('engine')} / {report['db'].get('name')}",
                f"- warnings: {case.get('warnings') or []}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return md


def _install_perf_timeline_bounds(start: str, end: str):
    """Perf synthetic windows are outside userspace data.json; loosen BE check."""
    from core.modules.backtest_engine.core.timeline.timeline import Timeline

    bound = (str(start), str(end))

    @classmethod  # type: ignore[misc]
    def _perf_system_bounds(cls, *, market: str = "SSE"):
        _ = market
        return bound

    Timeline.system_bounds = _perf_system_bounds  # type: ignore[method-assign]
    return bound


def main(argv: Optional[List[str]] = None) -> int:
    from core.modules.backtest_engine.contracts import RunCallbacks

    p = argparse.ArgumentParser(description="Run BE idle performance cases")
    p.add_argument(
        "--case",
        choices=["idle_entity_based", "idle_slice_based", "all"],
        default="all",
    )
    p.add_argument(
        "--with-io",
        action="store_true",
        help="on first tick per job, load daily klines for job entities",
    )
    p.add_argument("--entities-per-job", type=int, default=5)
    args = p.parse_args(argv)

    if not dataset_files_present():
        raise SystemExit("fake_data missing; run data_gen.py first")

    ids = read_universe()
    timeline = _open_dates()
    if not timeline:
        raise SystemExit("no open dates in fake calendar")

    meta = read_dataset_meta()
    step(
        "test",
        f"dataset stocks={meta.get('stock_count')} "
        f"open_days={meta.get('open_days')} klines={meta.get('kline_rows')} "
        f"case={args.case} with_io={args.with_io}",
    )
    win_start = str(meta.get("start_date") or timeline[0])
    win_end = str(meta.get("end_date") or timeline[-1])
    # cover open-day axis even if meta uses calendar ends
    if timeline[0] < win_start:
        win_start = timeline[0]
    if timeline[-1] > win_end:
        win_end = timeline[-1]
    bounds = _install_perf_timeline_bounds(win_start, win_end)
    step("test", f"timeline bounds {bounds[0]} ~ {bounds[1]} ({len(timeline)} open days)")

    step("test", "attach perf duckdb…")
    db_entry = _attach_perf_duckdb()
    step("test", f"using duckdb {db_entry.get('name')}")
    io_stats: Dict[str, Any] = {}
    if args.with_io:
        io_stats = _preflight_io(ids, timeline[0], timeline[-1])
        print(
            f"io_preflight: {io_stats['io_preflight_s']:.4f}s "
            f"rows={io_stats['io_preflight_rows']}",
            flush=True,
        )
    # Idle = schedule/timeline wall only; does NOT read the 1.3M kline rows unless --with-io.
    callbacks = RunCallbacks(
        on_tick=_idle_on_tick,
        on_ticks_complete=_idle_on_ticks_complete,
    )
    step(
        "test",
        "note: idle on_tick is noop — wall time is scheduler/timeline cost, "
        "not market-data IO (use --with-io for IO preflight)",
    )

    cases = []
    if args.case in ("idle_entity_based", "all"):
        cases.append(
            _run_entity(
                ids,
                timeline,
                callbacks=callbacks,
                entities_per_job=max(1, args.entities_per_job),
            )
        )
    if args.case in ("idle_slice_based", "all"):
        cases.append(_run_slice(ids, timeline, callbacks=callbacks))

    for case in cases:
        case.update(io_stats)
        path = _write_report(case, with_io=args.with_io, db_entry=db_entry)
        print(
            f"{case['case_id']}: wall={case['wall_time_s']:.4f}s "
            f"jobs={case.get('jobs')}/{case.get('expected_jobs')} "
            f"ticks={case.get('tick_count')}/{case.get('expected_ticks')} "
            f"success={case['success']} report={path}",
            flush=True,
        )
    step("test", "all requested cases finished")
    return 0 if all(c.get("success") for c in cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
