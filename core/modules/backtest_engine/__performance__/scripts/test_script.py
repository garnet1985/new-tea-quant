#!/usr/bin/env python3
"""Run BE performance cases.

Default: Strategy enumerate (null fixture) against perf DuckDB.
Optional: ``--idle`` for BE schedule-only baseline.

Requires ``data_gen.py`` + ``db_creation.py`` (DuckDB under ``.workdir/``).
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
_STRATEGY_DIR = _SCRIPTS / "strategies" / "perf_null"
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
from progress import step  # noqa: E402
from workload import (  # noqa: E402
    idle_on_tick,
    idle_on_ticks_complete,
    install_perf_worker_db_overlay,
    io_on_before_task_start,
    io_on_tick,
    io_on_ticks_complete,
    stamp_perf_db_paths,
)

_CASE_ALL = "all"
_STRATEGY_CASES = ("strategy_enum_entity", "strategy_enum_slice")
_DEFAULT_CASES = _STRATEGY_CASES
_IO_CASES = ("io_entity_based", "io_slice_based")
_IDLE_CASES = ("idle_entity_based", "idle_slice_based")
_MODE_BY_CASE = {
    "strategy_enum_entity": "entity_based",
    "strategy_enum_slice": "slice_based",
    # CLI alias: both modes
    "strategy_enumerate": None,
}


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


def _load_fixture_strategy(mode: str):
    """Load scripts/strategies/perf_null and pin execution mode on disk settings.

    ``EnumeratorPipeline`` branches on ``strategy_info.get_execution_mode()``
    (disk settings), not only runtime effective settings — so mode must be set here.
    """
    from copy import deepcopy

    from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
        EnabledStrategyInfo,
        StrategyDraft,
        StrategyInfo,
    )

    if mode not in ("entity_based", "slice_based"):
        raise SystemExit(f"invalid enum mode: {mode}")

    folder = _STRATEGY_DIR.resolve()
    draft = StrategyDraft(
        unique_relative_path=f"perf_null_{mode}",
        strategy_file=folder / "strategy.py",
        settings_file=folder / "settings.py",
    )
    info = StrategyInfo.from_draft(draft)
    if info is None:
        raise SystemExit(
            f"invalid fixture strategy: {folder}; errors={draft.validation_errors()}"
        )
    fields = {k: v for k, v in info.__dict__.items() if not k.startswith("_")}
    settings = deepcopy(fields.get("settings") or {})
    simulation = dict(settings.get("simulation") or {})
    execution = dict(simulation.get("execution") or {})
    execution["mode"] = mode
    simulation["execution"] = execution
    settings["simulation"] = simulation
    meta = dict(settings.get("meta") or {})
    meta["key"] = f"be_perf_null_{mode}"
    settings["meta"] = meta
    fields["settings"] = settings
    fields["key"] = str(meta["key"])
    fields["unique_relative_path"] = f"perf_null_{mode}"
    return EnabledStrategyInfo(**fields)


def _run_strategy_enumerate(
    ids: Sequence[str],
    *,
    db_paths: Dict[str, Any],
    meta: Dict[str, Any],
    case_id: str,
    mode: str,
) -> Dict[str, Any]:
    """Strategy enumerate path (EnumeratorPipeline → BE entity/slice)."""
    from core.modules.strategy.core.engines.enumerator.pipeline import EnumeratorPipeline
    from core.modules.strategy.core.engines.shared.data_class.simulate_session import (
        SimulateSession,
    )
    from core.modules.strategy.core.enums import SimulateKind
    from core.modules.strategy.core.services.entity_loader.global_entity_loader import (
        GlobalEntityCache,
    )
    from core.modules.strategy.core.services.simulation_cache.fingerprints import (
        FingerprintCalculator,
    )

    install_perf_worker_db_overlay(
        {
            "data": str(db_paths.get("data") or ""),
            "tag": str(db_paths.get("tag") or ""),
            "strategy": str(db_paths.get("strategy") or ""),
        }
    )
    strategy = _load_fixture_strategy(mode)
    start = str(meta.get("start_date") or "")
    end = str(meta.get("end_date") or "")
    runtime = {
        "sampling": {
            "use_sampling": True,
            "strategy": "pool",
            "sampling_amount": len(ids),
            "pool": {"stock_ids": list(ids)},
        },
        "simulation": {
            "execution": {
                "start_date": start,
                "end_date": end,
                "mode": mode,
            }
        },
    }
    step(
        "test",
        f"{case_id}: mode={mode} entities={len(ids)} window={start}..{end} "
        f"strategy={_STRATEGY_DIR.name}",
    )
    latest = str(meta.get("end_date") or "") or (
        GlobalEntityCache.get_latest_completed_trading_date()
    )
    fp_res = FingerprintCalculator.calculate_fingerprints(
        strategy,
        runtime,
        list(ids),
        latest,
    )
    ctx = SimulateSession(
        strategy_info=strategy,
        fp_res=fp_res,
        kind=SimulateKind.ENUMERATE,
        steps=[SimulateKind.ENUMERATE],
    )
    t0 = time.perf_counter()
    result = EnumeratorPipeline.run(ctx)
    wall = time.perf_counter() - t0
    ok = bool(result.get("success"))
    step("test", f"{case_id} finished in {wall:.2f}s success={ok}")
    return {
        "case_id": case_id,
        "mode": mode,
        "workload": "strategy_enumerate",
        "wall_time_s": wall,
        "entities": len(ids),
        "entities_driven": len(ids),
        "timeline_points": int(meta.get("open_days") or 0),
        "success": ok,
        "elapsed_seconds": float(result.get("elapsed_seconds") or 0.0),
        "opportunities_count": int(
            result.get("opportunities_count")
            or result.get("total_opportunities")
            or 0
        ),
        "output_dir": result.get("output_dir"),
        "version_id": result.get("version_id"),
        "enum_result": {
            k: result.get(k)
            for k in (
                "success",
                "elapsed_seconds",
                "opportunities_count",
                "total_opportunities",
                "output_dir",
                "version_id",
                "error",
            )
            if k in result
        },
        "warnings": [] if ok else ["enumerate returned success=False"],
        "jobs": None,
        "expected_jobs": None,
        "tick_count": None,
        "expected_ticks": None,
        "load_rows": None,
        "bars_hit": None,
        "load_sec_sum": None,
        "completed_jobs": None,
        "failed_jobs": None,
    }


def _sum_job_result_ints(result, key: str) -> int:
    total = 0
    for report in list(getattr(result, "job_results", None) or []):
        data = getattr(report, "data", None)
        if isinstance(data, dict) and key in data:
            total += int(data.get(key) or 0)
    return total


def _sum_job_result_floats(result, key: str) -> float:
    total = 0.0
    for report in list(getattr(result, "job_results", None) or []):
        data = getattr(report, "data", None)
        if isinstance(data, dict) and key in data:
            total += float(data.get(key) or 0.0)
    return total


def _metrics_from_result(
    *,
    case_id: str,
    mode: str,
    workload: str,
    wall: float,
    result,
    entities: int,
    timeline_points: int,
    expected_jobs: int,
    expected_ticks: int,
    expect_io: bool,
) -> Dict[str, Any]:
    completed = int(getattr(result, "completed_jobs", 0) or 0)
    total_jobs = int(getattr(result, "total_jobs", 0) or 0)
    tick_count = _sum_job_result_ints(result, "tick_count")
    entities_driven = _sum_job_result_ints(result, "entities_in_job")
    load_rows = _sum_job_result_ints(result, "load_rows")
    bars_hit = _sum_job_result_ints(result, "bars_hit")
    load_sec = _sum_job_result_floats(result, "load_sec")
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
    if expect_io:
        if load_rows <= 0:
            warnings.append("load_rows=0 (expected batch preload)")
        expected_bars = entities_driven * timeline_points
        if expected_bars > 0 and bars_hit < max(1, int(expected_bars * 0.95)):
            warnings.append(
                f"bars_hit={bars_hit} << expected≈{expected_bars} "
                "(synthetic data should hit nearly all open days)"
            )
        if entities_driven != entities:
            warnings.append(
                f"entities_driven={entities_driven} != entities={entities}"
            )
    if warnings:
        ok = False
        for w in warnings:
            step("test", f"WARNING {case_id}: {w}")
        reports = list(getattr(result, "job_results", None) or [])
        step(
            "test",
            f"debug {case_id}: job_results={len(reports)} "
            f"failed_jobs={getattr(result, 'failed_jobs', None)} "
            f"elapsed={getattr(result, 'elapsed_seconds', None)}",
        )
        for report in reports[:5]:
            err = getattr(report, "error", None)
            data = getattr(report, "data", None)
            data_err = data.get("error") if isinstance(data, dict) else None
            step(
                "test",
                f"job {getattr(report, 'job_id', '?')}: "
                f"success={getattr(report, 'success', None)} "
                f"error={err!r} data.error={data_err!r} "
                f"data_keys={list(data)[:12] if isinstance(data, dict) else type(data)}",
            )
    return {
        "case_id": case_id,
        "mode": mode,
        "workload": workload,
        "wall_time_s": wall,
        "jobs_submitted_bundle": 1,
        "jobs": total_jobs,
        "expected_jobs": expected_jobs,
        "entities": entities,
        "entities_driven": entities_driven,
        "timeline_points": timeline_points,
        "tick_count": tick_count,
        "expected_ticks": expected_ticks,
        "load_rows": load_rows,
        "bars_hit": bars_hit,
        "load_sec_sum": load_sec,
        "success": ok,
        "completed_jobs": completed,
        "failed_jobs": int(getattr(result, "failed_jobs", 0) or 0),
        "elapsed_seconds": float(getattr(result, "elapsed_seconds", 0.0) or 0.0),
        "warnings": warnings,
    }


def _run_entity(
    ids: Sequence[str],
    timeline: Sequence[str],
    *,
    callbacks,
    entities_per_job: int,
    case_id: str,
    expect_io: bool,
    db_paths: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    from core.modules.backtest_engine import BacktestEngine

    # BE entity planner is bundle-mode: only jobs[0].entity_specified is used.
    jobs = [
        {
            "id": "entity_bundle",
            "payload": {"entity_specified": [{"id": sid} for sid in ids]},
        }
    ]
    if expect_io and db_paths:
        jobs = stamp_perf_db_paths(jobs, db_paths)
    expected_jobs = max(1, math.ceil(len(ids) / max(1, entities_per_job)))
    expected_ticks = expected_jobs * len(timeline)
    workload = "io_preload_asof" if expect_io else "idle"
    step(
        "test",
        f"{case_id}: entities={len(ids)} "
        f"expected_batches≈{expected_jobs} (epj={entities_per_job}) "
        f"timeline={len(timeline)} expected_ticks≈{expected_ticks:,} "
        f"workload={workload}",
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
            "dispatch_probe": False,
            "mb_per_entity_staged": 1.0,
            "duckdb_process_pool_scope": "auto",
        },
        task_name=f"be_perf_{case_id}",
        callbacks=callbacks,
        enable_progress_display=True,
    )
    wall = time.perf_counter() - t0
    step("test", f"{case_id} finished in {wall:.2f}s")
    return _metrics_from_result(
        case_id=case_id,
        mode="entity_based",
        workload=workload,
        wall=wall,
        result=result,
        entities=len(ids),
        timeline_points=len(timeline),
        expected_jobs=expected_jobs,
        expected_ticks=expected_ticks,
        expect_io=expect_io,
    )


def _run_slice(
    ids: Sequence[str],
    timeline: Sequence[str],
    *,
    callbacks,
    case_id: str,
    expect_io: bool,
    db_paths: Optional[Dict[str, Any]] = None,
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
    if expect_io and db_paths:
        jobs = stamp_perf_db_paths(jobs, db_paths)
    expected_jobs = 1
    expected_ticks = len(timeline)
    workload = "io_preload_asof" if expect_io else "idle"
    step(
        "test",
        f"{case_id}: entities={len(ids)} bulk_jobs=1 "
        f"timeline={len(timeline)} expected_ticks={expected_ticks:,} "
        f"workload={workload}",
    )
    t0 = time.perf_counter()
    result = BacktestEngine.slice_based.run(
        jobs,
        start=timeline[0],
        end=timeline[-1],
        timeline=list(timeline),
        performance={
            "max_workers": 1,
            "dispatch_probe": False,
            "duckdb_process_pool_scope": "auto",
        },
        task_name=f"be_perf_{case_id}",
        callbacks=callbacks,
        enable_progress_display=True,
    )
    wall = time.perf_counter() - t0
    step("test", f"{case_id} finished in {wall:.2f}s")
    return _metrics_from_result(
        case_id=case_id,
        mode="slice_based",
        workload=workload,
        wall=wall,
        result=result,
        entities=len(ids),
        timeline_points=len(timeline),
        expected_jobs=expected_jobs,
        expected_ticks=expected_ticks,
        expect_io=expect_io,
    )


def _write_report(case: Dict[str, Any], *, db_entry: dict) -> Path:
    ensure_layout()
    out_dir = RESULTS_DIR / "_local" / str(case["case_id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = read_dataset_meta()
    workload = str(case.get("workload") or "idle")
    if workload == "io_preload_asof":
        desc = (
            f"BE {case['mode']}: on_before_task_start load_batch(daily) + "
            "on_tick in-memory as-of bar lookup (no strategy/tag)"
        )
    else:
        desc = f"BE {case['mode']}: idle on_tick noop (schedule/timeline baseline)"
    report = {
        "case_name": case["case_id"],
        "run_date": utc_now_iso(),
        "module": "modules.backtest_engine",
        "description": desc,
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
    lines = [
        f"# Performance Report — {case['case_id']}",
        "",
        f"- date: {report['run_date']}",
        f"- mode: {case['mode']}",
        f"- workload: {workload}",
        f"- wall_time_s: {case['wall_time_s']:.4f}",
        f"- entities: {case.get('entities')} (driven={case.get('entities_driven')})",
        f"- timeline_points: {case.get('timeline_points')}",
        f"- success: {case.get('success')}",
        f"- db: {report['db'].get('engine')} / {report['db'].get('name')}",
        f"- warnings: {case.get('warnings') or []}",
    ]
    if workload == "strategy_enumerate":
        lines.extend(
            [
                f"- elapsed_seconds: {case.get('elapsed_seconds')}",
                f"- opportunities_count: {case.get('opportunities_count')}",
                f"- output_dir: {case.get('output_dir')}",
                f"- version_id: {case.get('version_id')}",
            ]
        )
    else:
        lines.extend(
            [
                f"- jobs: {case.get('jobs')} / expected {case.get('expected_jobs')}",
                f"- ticks: {case.get('tick_count')} / expected {case.get('expected_ticks')}",
                f"- load_rows: {case.get('load_rows')}",
                f"- bars_hit: {case.get('bars_hit')}",
                f"- load_sec_sum: {case.get('load_sec_sum')}",
            ]
        )
    lines.append("")
    md.write_text("\n".join(lines), encoding="utf-8")
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


def _resolve_cases(case: str, idle: bool) -> List[str]:
    if case == _CASE_ALL:
        return list(_IDLE_CASES if idle else _DEFAULT_CASES)
    if case == "strategy_enumerate":
        return list(_STRATEGY_CASES)
    if case in _STRATEGY_CASES or case in _IDLE_CASES or case in _IO_CASES:
        return [case]
    raise SystemExit(f"unknown case: {case}")


def main(argv: Optional[List[str]] = None) -> int:
    from core.modules.backtest_engine.contracts import RunCallbacks

    p = argparse.ArgumentParser(
        description=(
            "Run BE performance cases "
            "(default: strategy_enum_entity + strategy_enum_slice)"
        )
    )
    p.add_argument(
        "--case",
        choices=[
            "strategy_enum_entity",
            "strategy_enum_slice",
            "strategy_enumerate",
            "io_entity_based",
            "io_slice_based",
            "idle_entity_based",
            "idle_slice_based",
            "all",
        ],
        default="all",
        help="default all = strategy_enum_entity + strategy_enum_slice",
    )
    p.add_argument(
        "--idle",
        action="store_true",
        help="with --case all, run idle schedule baseline instead of strategy enum",
    )
    p.add_argument(
        "--with-io",
        action="store_true",
        help="deprecated no-op (kept for CLI compatibility)",
    )
    p.add_argument("--entities-per-job", type=int, default=5)
    args = p.parse_args(argv)

    if not dataset_files_present():
        raise SystemExit("fake_data missing; run data_gen.py first")

    ids = read_universe()
    timeline = _open_dates()
    if not timeline:
        raise SystemExit("no open dates in fake calendar")

    selected = _resolve_cases(args.case, idle=bool(args.idle))
    meta = read_dataset_meta()
    step(
        "test",
        f"dataset stocks={meta.get('stock_count')} "
        f"open_days={meta.get('open_days')} klines={meta.get('kline_rows')} "
        f"cases={selected}",
    )
    if args.with_io:
        step("test", "--with-io is deprecated; ignored")

    win_start = str(meta.get("start_date") or timeline[0])
    win_end = str(meta.get("end_date") or timeline[-1])
    if timeline[0] < win_start:
        win_start = timeline[0]
    if timeline[-1] > win_end:
        win_end = timeline[-1]
    bounds = _install_perf_timeline_bounds(win_start, win_end)
    step("test", f"timeline bounds {bounds[0]} ~ {bounds[1]} ({len(timeline)} open days)")

    step("test", "attach perf duckdb…")
    db_entry = _attach_perf_duckdb()
    step("test", f"using duckdb {db_entry.get('name')}")

    need_be_callbacks = any(c in _IDLE_CASES or c in _IO_CASES for c in selected)
    idle_callbacks = None
    io_callbacks = None
    if need_be_callbacks:
        idle_callbacks = RunCallbacks(
            on_tick=idle_on_tick,
            on_ticks_complete=idle_on_ticks_complete,
        )
        io_callbacks = RunCallbacks(
            on_before_task_start=io_on_before_task_start,
            on_tick=io_on_tick,
            on_ticks_complete=io_on_ticks_complete,
        )

    cases: List[Dict[str, Any]] = []
    epj = max(1, args.entities_per_job)
    db_paths = db_entry.get("paths") or {}
    for case_id in selected:
        if case_id in _MODE_BY_CASE and _MODE_BY_CASE[case_id]:
            cases.append(
                _run_strategy_enumerate(
                    ids,
                    db_paths=db_paths,
                    meta=meta,
                    case_id=case_id,
                    mode=str(_MODE_BY_CASE[case_id]),
                )
            )
        elif case_id == "io_entity_based":
            cases.append(
                _run_entity(
                    ids,
                    timeline,
                    callbacks=io_callbacks,
                    entities_per_job=epj,
                    case_id=case_id,
                    expect_io=True,
                    db_paths=db_paths,
                )
            )
        elif case_id == "io_slice_based":
            cases.append(
                _run_slice(
                    ids,
                    timeline,
                    callbacks=io_callbacks,
                    case_id=case_id,
                    expect_io=True,
                    db_paths=db_paths,
                )
            )
        elif case_id == "idle_entity_based":
            cases.append(
                _run_entity(
                    ids,
                    timeline,
                    callbacks=idle_callbacks,
                    entities_per_job=epj,
                    case_id=case_id,
                    expect_io=False,
                )
            )
        elif case_id == "idle_slice_based":
            cases.append(
                _run_slice(
                    ids,
                    timeline,
                    callbacks=idle_callbacks,
                    case_id=case_id,
                    expect_io=False,
                )
            )

    for case in cases:
        path = _write_report(case, db_entry=db_entry)
        if case.get("workload") == "strategy_enumerate":
            print(
                f"{case['case_id']}: wall={case['wall_time_s']:.4f}s "
                f"elapsed={case.get('elapsed_seconds')} "
                f"opportunities={case.get('opportunities_count')} "
                f"success={case['success']} report={path}",
                flush=True,
            )
        else:
            print(
                f"{case['case_id']}: wall={case['wall_time_s']:.4f}s "
                f"jobs={case.get('jobs')}/{case.get('expected_jobs')} "
                f"ticks={case.get('tick_count')}/{case.get('expected_ticks')} "
                f"load_rows={case.get('load_rows')} bars_hit={case.get('bars_hit')} "
                f"success={case['success']} report={path}",
                flush=True,
            )
    step("test", "all requested cases finished")
    return 0 if cases and all(c.get("success") for c in cases) else 1


if __name__ == "__main__":
    # ProcessPool spawn re-imports this file as __main__; only the true parent
    # process should run the CLI (workers have name like SpawnProcess-1).
    import multiprocessing as mp

    if mp.current_process().name == "MainProcess":
        raise SystemExit(main())
