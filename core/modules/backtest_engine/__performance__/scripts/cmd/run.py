#!/usr/bin/env python3
"""Run one BE performance baseline strategy (entity_based XOR slice_based).

Uses fixed fixtures under ``scripts/test_strategies/be_perf_{entity,slice}/``.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_CMD = Path(__file__).resolve().parent
if str(_CMD) not in sys.path:
    sys.path.insert(0, str(_CMD))

from common import (  # noqa: E402
    RESULTS_DIR,
    active_duckdb_entry,
    ensure_layout,
    open_dates_from_meta,
    read_dataset_meta,
    repo_root,
    strategy_dir_for_mode,
    universe_ids_from_meta,
    utc_now_iso,
)
from progress import step  # noqa: E402
from workload import install_perf_worker_db_overlay  # noqa: E402

_REPO = repo_root()
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_CASE_BY_MODE = {
    "entity_based": "be_perf_entity",
    "slice_based": "be_perf_slice",
}


def _attach_perf_duckdb() -> Dict[str, Any]:
    from core.infra.db import Db
    from core.modules.data_manager import DataManager

    entry = active_duckdb_entry()
    if not entry:
        raise SystemExit("no perf duckdb; run db_creation.py first (direct seed)")
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


def _load_baseline_strategy(mode: str):
    """Load fixed test_strategies/be_perf_{entity,slice} (mode baked into settings)."""
    from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
        EnabledStrategyInfo,
        StrategyDraft,
        StrategyInfo,
    )

    folder = strategy_dir_for_mode(mode)
    draft = StrategyDraft(
        unique_relative_path=folder.name,
        strategy_file=folder / "strategy.py",
        settings_file=folder / "settings.py",
    )
    info = StrategyInfo.from_draft(draft)
    if info is None:
        raise SystemExit(
            f"invalid baseline strategy: {folder}; errors={draft.validation_errors()}"
        )
    fields = {k: v for k, v in info.__dict__.items() if not k.startswith("_")}
    return EnabledStrategyInfo(**fields)


def _extract_slice_runtime(result: Dict[str, Any]) -> Dict[str, Any]:
    plan = result.get("calendar_slice_runtime_plan")
    if not isinstance(plan, dict) or not plan:
        return {}
    return {
        "per_entity_load_count": int(plan.get("per_entity_load_count") or 0),
        "formal_slices_completed": int(plan.get("formal_slices_completed") or 0),
        "reader_workers": int(plan.get("reader_workers") or 0),
        "queue_depth": int(plan.get("queue_depth") or 0),
        "slice_samples": list(plan.get("slice_samples") or []),
    }


def _run_one(
    ids: Sequence[str],
    *,
    db_paths: Dict[str, Any],
    meta: Dict[str, Any],
    mode: str,
) -> Dict[str, Any]:
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

    case_id = _CASE_BY_MODE[mode]
    folder = strategy_dir_for_mode(mode)
    install_perf_worker_db_overlay(
        {
            "data": str(db_paths.get("data") or ""),
            "tag": str(db_paths.get("tag") or ""),
            "strategy": str(db_paths.get("strategy") or ""),
        }
    )
    strategy = _load_baseline_strategy(mode)
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
        f"strategy={folder.name}",
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
    slice_runtime = _extract_slice_runtime(result) if mode == "slice_based" else {}
    warnings: List[str] = []
    if not ok:
        warnings.append("enumerate returned success=False")
    if mode == "slice_based":
        loads = int(slice_runtime.get("per_entity_load_count") or 0)
        slices = int(slice_runtime.get("formal_slices_completed") or 0)
        if loads <= 0:
            warnings.append(
                "slice per_entity_load_count=0 (expected ≥1 formal window loads)"
            )
        if slices > 0 and loads < slices:
            warnings.append(
                f"per_entity_load_count={loads} < formal_slices_completed={slices}"
            )
        if loads <= 0:
            ok = False
    step(
        "test",
        f"{case_id} finished in {wall:.2f}s success={ok}"
        + (
            f" loads={slice_runtime.get('per_entity_load_count')} "
            f"slices={slice_runtime.get('formal_slices_completed')} "
            f"readers={slice_runtime.get('reader_workers')} "
            f"queue={slice_runtime.get('queue_depth')}"
            if slice_runtime
            else ""
        ),
    )
    return {
        "case_id": case_id,
        "mode": mode,
        "strategy": folder.name,
        "workload": "strategy_baseline",
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
        "total_jobs": int(result.get("total_jobs") or 0),
        "completed_jobs": int(result.get("completed_jobs") or 0),
        "failed_jobs": int(result.get("failed_jobs") or 0),
        "slice_runtime": slice_runtime or None,
        "warnings": warnings,
    }


def _write_report(case: Dict[str, Any], *, db_entry: dict) -> Path:
    ensure_layout()
    out_dir = RESULTS_DIR / "_local" / str(case["case_id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = read_dataset_meta()
    mode = str(case.get("mode") or "")
    if mode == "slice_based":
        desc = (
            "Baseline be_perf_slice → EnumeratorPipeline → BE slice_based "
            "(SliceOrchestrator)"
        )
    else:
        desc = (
            "Baseline be_perf_entity → EnumeratorPipeline → BE entity_based "
            "(full-window load)"
        )
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
    lines = [
        f"# Performance Report — {case['case_id']}",
        "",
        f"- date: {report['run_date']}",
        f"- mode: {case['mode']}",
        f"- strategy: {case.get('strategy')}",
        f"- wall_time_s: {case['wall_time_s']:.4f}",
        f"- elapsed_seconds: {case.get('elapsed_seconds')}",
        f"- entities: {case.get('entities')}",
        f"- timeline_points: {case.get('timeline_points')}",
        f"- opportunities_count: {case.get('opportunities_count')}",
        f"- jobs: {case.get('completed_jobs')}/{case.get('total_jobs')} "
        f"(failed={case.get('failed_jobs')})",
        f"- success: {case.get('success')}",
        f"- output_dir: {case.get('output_dir')}",
        f"- version_id: {case.get('version_id')}",
        f"- db: {report['db'].get('engine')} / {report['db'].get('name')}",
        f"- warnings: {case.get('warnings') or []}",
    ]
    sr = case.get("slice_runtime") or {}
    if sr:
        lines.extend(
            [
                f"- per_entity_load_count: {sr.get('per_entity_load_count')}",
                f"- formal_slices_completed: {sr.get('formal_slices_completed')}",
                f"- reader_workers: {sr.get('reader_workers')}",
                f"- queue_depth: {sr.get('queue_depth')}",
            ]
        )
    lines.append("")
    (out_dir / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    return out_dir / "REPORT.md"


def _install_perf_timeline_bounds(start: str, end: str):
    from core.modules.backtest_engine.core.timeline.timeline import Timeline

    bound = (str(start), str(end))

    @classmethod  # type: ignore[misc]
    def _perf_system_bounds(cls, *, market: str = "SSE"):
        _ = market
        return bound

    Timeline.system_bounds = _perf_system_bounds  # type: ignore[method-assign]
    return bound


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Run one fixed BE performance baseline strategy"
    )
    p.add_argument(
        "mode",
        choices=["entity_based", "slice_based"],
        help="BE mode / baseline strategy to run",
    )
    args = p.parse_args(argv)
    mode = str(args.mode)

    entry_probe = active_duckdb_entry()
    if not entry_probe:
        raise SystemExit("no perf duckdb; run db_creation.py first (direct seed)")

    meta = read_dataset_meta()
    if not meta:
        raise SystemExit("perf duckdb has no dataset meta; re-run db_creation.py")
    ids = universe_ids_from_meta(meta)
    timeline = open_dates_from_meta(meta)
    if not timeline:
        raise SystemExit("no open dates for dataset window")

    step(
        "test",
        f"dataset stocks={meta.get('stock_count')} "
        f"open_days={meta.get('open_days')} klines={meta.get('kline_rows')} "
        f"mode={mode}",
    )

    win_start = str(meta.get("start_date") or timeline[0])
    win_end = str(meta.get("end_date") or timeline[-1])
    if timeline[0] < win_start:
        win_start = timeline[0]
    if timeline[-1] > win_end:
        win_end = timeline[-1]
    bounds = _install_perf_timeline_bounds(win_start, win_end)
    step(
        "test",
        f"timeline bounds {bounds[0]} ~ {bounds[1]} ({len(timeline)} open days)",
    )

    step("test", "attach perf duckdb…")
    db_entry = _attach_perf_duckdb()
    step("test", f"using duckdb {db_entry.get('name')}")

    case = _run_one(
        ids,
        db_paths=db_entry.get("paths") or {},
        meta=meta,
        mode=mode,
    )
    path = _write_report(case, db_entry=db_entry)
    extra = ""
    sr = case.get("slice_runtime") or {}
    if sr:
        extra = (
            f" loads={sr.get('per_entity_load_count')}"
            f" slices={sr.get('formal_slices_completed')}"
            f" readers={sr.get('reader_workers')}"
            f" queue={sr.get('queue_depth')}"
        )
    print(
        f"{case['case_id']}: wall={case['wall_time_s']:.4f}s "
        f"elapsed={case.get('elapsed_seconds')} "
        f"opportunities={case.get('opportunities_count')} "
        f"success={case['success']}{extra} report={path}",
        flush=True,
    )
    return 0 if case.get("success") else 1


if __name__ == "__main__":
    import multiprocessing as mp

    if mp.current_process().name == "MainProcess":
        raise SystemExit(main())
