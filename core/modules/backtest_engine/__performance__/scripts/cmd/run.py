#!/usr/bin/env python3
"""Run one BE performance baseline strategy (entity_based XOR slice_based).

Uses fixed fixtures under ``scripts/test_strategies/{entity_based,slice_based}/``.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

_CMD = Path(__file__).resolve().parent
if str(_CMD) not in sys.path:
    sys.path.insert(0, str(_CMD))

from common import (  # noqa: E402
    active_perf_entry,
    be_module_version,
    collect_perf_versions,
    ensure_layout,
    open_dates_from_meta,
    read_dataset_meta,
    report_engine_dirname,
    report_out_dir,
    repo_root,
    scale_stock_counts,
    strategy_dir_for_mode,
    universe_ids_from_meta,
    utc_now_iso,
)
from config import DEFAULT_STOCK_COUNT  # noqa: E402
from progress import step  # noqa: E402
from scaling import write_overall_report  # noqa: E402
from workload import (  # noqa: E402
    install_perf_worker_db_overlay,
    install_perf_worker_server_overlay,
)

_REPO = repo_root()
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_CASE_BY_MODE = {
    "entity_based": "entity_based",
    "slice_based": "slice_based",
}

_MODE_LABEL = {
    "entity_based": "按股票分包（entity）",
    "slice_based": "按时间切片（slice）",
}


def _attach_perf_duckdb(entry: Dict[str, Any]) -> Dict[str, Any]:
    from core.infra.db import Db
    from core.modules.data_manager import DataManager

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
    install_perf_worker_db_overlay(
        {
            "data": str(paths.get("data") or ""),
            "tag": str(paths.get("tag") or ""),
            "strategy": str(paths.get("strategy") or ""),
        }
    )
    return entry


def _attach_perf_mysql(entry: Dict[str, Any]) -> Dict[str, Any]:
    from core.infra.db import Db
    from core.modules.data_manager import DataManager
    from mysql_support import (
        assert_safe_perf_db_name,
        build_mysql_manager_config,
        load_mysql_server_config,
        mysql_database_exists,
        probe_mysql_server,
    )

    name = assert_safe_perf_db_name(str(entry.get("name") or ""))
    server_cfg = load_mysql_server_config()
    probe_mysql_server(server_cfg)
    if not mysql_database_exists(server_cfg, name):
        raise SystemExit(
            f"registry 中有 mysql/{name}，但服务器上找不到该库；"
            "请先重新运行 db_creation（--db mysql --reuse）。"
        )
    mgr_cfg = build_mysql_manager_config(server_cfg, name)
    Db.manager.reset_default()
    db = Db.manager.create(mgr_cfg, is_verbose=False)
    db.initialize()
    Db.manager.set_default(db)
    DataManager.reset_instance()
    DataManager(db=db, is_verbose=False)
    install_perf_worker_server_overlay(mgr_cfg)
    return entry


def _attach_perf_postgresql(entry: Dict[str, Any]) -> Dict[str, Any]:
    from core.infra.db import Db
    from core.modules.data_manager import DataManager
    from postgresql_support import (
        assert_safe_perf_db_name,
        build_postgresql_manager_config,
        load_postgresql_server_config,
        postgresql_database_exists,
        probe_postgresql_server,
    )

    name = assert_safe_perf_db_name(str(entry.get("name") or ""))
    server_cfg = load_postgresql_server_config()
    probe_postgresql_server(server_cfg)
    if not postgresql_database_exists(server_cfg, name):
        raise SystemExit(
            f"registry 中有 postgresql/{name}，但服务器上找不到该库；"
            "请先重新运行 db_creation（--db postgresql --reuse）。"
        )
    mgr_cfg = build_postgresql_manager_config(server_cfg, name)
    Db.manager.reset_default()
    db = Db.manager.create(mgr_cfg, is_verbose=False)
    db.initialize()
    Db.manager.set_default(db)
    DataManager.reset_instance()
    DataManager(db=db, is_verbose=False)
    install_perf_worker_server_overlay(mgr_cfg)
    return entry


def _attach_perf_db(entry: Dict[str, Any]) -> Dict[str, Any]:
    eng = str(entry.get("engine") or "").lower()
    if eng == "duckdb":
        return _attach_perf_duckdb(entry)
    if eng == "mysql":
        return _attach_perf_mysql(entry)
    if eng == "postgresql":
        return _attach_perf_postgresql(entry)
    raise SystemExit(f"unsupported perf db engine: {eng!r}")


def _load_baseline_strategy(mode: str):
    """Load fixed test_strategies/{entity_based,slice_based} (mode baked into settings)."""
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
    db_entry: Dict[str, Any],
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
    # Worker overlay already installed in _attach_perf_db.
    engine = str(db_entry.get("engine") or "duckdb")
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
        f"{case_id}: mode={mode} db={engine} entities={len(ids)} "
        f"window={start}..{end} strategy={folder.name}",
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
        "db_engine": engine,
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


def _env_snapshot() -> Dict[str, Any]:
    mem_gb: Optional[float] = None
    try:
        from core.infra.machine_capacity.machine_capacity import MachineInfo

        total_mb, _ = MachineInfo._virtual_memory_mb()
        if total_mb is not None:
            mem_gb = round(total_mb / 1024.0, 1)
    except Exception:
        pass
    cpu = (platform.processor() or "").strip() or platform.machine()
    return {
        "os": f"{platform.system()} {platform.release()}",
        "cpu": cpu,
        "memory_gb": mem_gb,
        "python": f"{sys.version_info.major}.{sys.version_info.minor}",
    }


def _load_performance_payload(output_dir: Any) -> Dict[str, Any]:
    if not output_dir:
        return {}
    path = Path(str(output_dir)) / "performance.json"
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _bucket_sec_pct(bucket: Any) -> tuple:
    if not isinstance(bucket, dict):
        return None, None
    sec = bucket.get("sec")
    pct = bucket.get("pct")
    try:
        sec_f = float(sec) if sec is not None else None
    except (TypeError, ValueError):
        sec_f = None
    try:
        pct_f = float(pct) if pct is not None else None
    except (TypeError, ValueError):
        pct_f = None
    return sec_f, pct_f


def _format_sec_pct(sec: Optional[float], pct: Optional[float]) -> str:
    if sec is None:
        return "—"
    if pct is None:
        return f"{sec:.2f}s"
    return f"{sec:.2f}s（{pct:.1f}%）"


def _safe_float(raw: Any) -> Optional[float]:
    try:
        if raw is None:
            return None
        return float(raw)
    except (TypeError, ValueError):
        return None


def _probe_detail(perf: Dict[str, Any]) -> Dict[str, Any]:
    planner = dict(perf.get("planner") or {})
    probe = dict(planner.get("probe") or {})
    detail = probe.get("detail")
    return dict(detail) if isinstance(detail, dict) else {}


def _scale_parts(
    total_sec: Optional[float], weights: Dict[str, float]
) -> Dict[str, float]:
    """Distribute wall ``total_sec`` by relative weights (ignore non-positive)."""
    if total_sec is None or total_sec <= 0:
        return {}
    clean = {k: float(v) for k, v in weights.items() if float(v or 0.0) > 0}
    s = sum(clean.values())
    if s <= 0:
        return {}
    return {k: total_sec * (v / s) for k, v in clean.items()}


def _time_split_from_glance(glance: Dict[str, Any]) -> Dict[str, Any]:
    td = dict(glance.get("time_distribution") or {})
    planning_sec, planning_pct = _bucket_sec_pct(td.get("planning"))
    load_raw = td.get("load_data") if "load_data" in td else td.get("read")
    load_sec, load_pct = _bucket_sec_pct(load_raw)
    compute_sec, compute_pct = _bucket_sec_pct(td.get("compute"))
    report_sec, report_pct = _bucket_sec_pct(td.get("report"))
    return {
        "planning_sec": planning_sec,
        "planning_pct": planning_pct,
        "load_sec": load_sec,
        "load_pct": load_pct,
        "compute_sec": compute_sec,
        "compute_pct": compute_pct,
        "report_sec": report_sec,
        "report_pct": report_pct,
    }


def _build_time_breakdown(
    *,
    mode: str,
    glance: Dict[str, Any],
    perf: Dict[str, Any],
) -> Dict[str, Any]:
    """Four big buckets + a few plain-language sub-items for the report."""
    split = _time_split_from_glance(glance)
    detail = _probe_detail(perf)
    staged = dict((perf.get("child_process") or {}).get("staged") or {})
    monitor = dict(perf.get("monitor") or {})

    planning_sec = split.get("planning_sec")
    load_sec = split.get("load_sec")
    compute_sec = split.get("compute_sec")

    # entity: separate short probe job → wall fits under planning.
    # slice: head-sample on the formal job; probe.wall_sec is whole-job wall — not a
    # planning sub-cost (nesting it under 0.1s planning looked like 13s inside 0.1s).
    probe_wall = _safe_float(detail.get("wall_sec"))
    planning_subs: Dict[str, Any] = {}

    load_subs: Dict[str, Any] = {}
    compute_subs: Dict[str, Any] = {}
    notes: List[str] = [
        "空策略下「推进日历 / 引擎开销」主要是填上下文、按日推进、数据交接，不是选股算力。"
    ]

    if mode == "slice_based":
        sampled = detail.get("slices_sampled")
        try:
            n_samp = int(sampled) if sampled is not None else 0
        except (TypeError, ValueError):
            n_samp = 0
        if n_samp > 0:
            planning_subs["调度采样"] = (
                f"正式任务前 {n_samp} 片（耗时已计入读数据/推进，不单列）"
            )
        peak_r = _safe_float(
            detail.get("peak_rss_mb_reader") or monitor.get("peak_rss_mb")
        )
        peak_c = _safe_float(detail.get("peak_rss_mb_compute"))
        if peak_r is not None:
            load_subs["读进程峰值内存"] = f"{peak_r:.1f} MB"
        if peak_c is not None:
            compute_subs["计算进程峰值内存"] = f"{peak_c:.1f} MB"
        ser = _safe_float(detail.get("sec_per_slice_serialize")) or 0.0
        deser = _safe_float(detail.get("sec_per_slice_deserialize")) or 0.0
        read_hat = _safe_float(detail.get("sec_per_slice_reader")) or 0.0
        comp_hat = _safe_float(detail.get("sec_per_slice_compute")) or 0.0
        read_hat = _safe_float(monitor.get("sec_per_slice_reader_hat")) or read_hat
        comp_hat = _safe_float(monitor.get("sec_per_slice_compute_hat")) or comp_hat
        if load_sec and read_hat > 0:
            load_subs["单片读数（估）"] = f"{read_hat:.3f}s/片"
        if compute_sec and comp_hat > 0:
            compute_subs["单片推进（估）"] = f"{comp_hat:.3f}s/片"
        scaled = _scale_parts(
            compute_sec,
            {
                "片间序列化": ser,
                "片间反序列化": deser,
                "片内推进": max(comp_hat - ser - deser, 0.0) if comp_hat else 0.0,
            },
        )
        for k, v in scaled.items():
            if v >= 0.005:
                compute_subs[k] = round(v, 4)
    else:
        if (
            probe_wall is not None
            and probe_wall > 0
            and planning_sec is not None
            and probe_wall <= float(planning_sec) * 1.25 + 0.05
        ):
            planning_subs["试跑采样（定并行）"] = round(probe_wall, 4)
            rest = max(0.0, float(planning_sec) - probe_wall)
            if rest > 0.0005:
                planning_subs["正式规划"] = round(rest, 4)
        elif planning_sec is not None and planning_sec > 0:
            planning_subs["正式规划"] = round(float(planning_sec), 4)
        peak = _safe_float(detail.get("peak_rss_mb"))
        if peak is not None:
            load_subs["峰值内存（试跑采样）"] = f"{peak:.1f} MB"
        load_scaled = _scale_parts(
            load_sec,
            {
                "装合约/行情": float(staged.get("load_contract_issue") or 0.0),
                "指标应用": float(staged.get("load_apply_indicators") or 0.0),
            },
        )
        for k, v in load_scaled.items():
            if v >= 0.005:
                load_subs[k] = round(v, 4)
        enum_scaled = _scale_parts(
            compute_sec,
            {
                "填上下文": float(staged.get("enum_context_fill") or 0.0),
                "按日 as-of": float(staged.get("enum_as_of_slice") or 0.0),
                "合约 until": float(staged.get("enum_contract_until") or 0.0),
                "日历 tick": float(staged.get("enum_process_tick") or 0.0),
            },
        )
        for k, v in enum_scaled.items():
            if v >= 0.005:
                compute_subs[k] = round(v, 4)

    return {
        **split,
        "planning_subs": planning_subs,
        "load_subs": load_subs,
        "compute_subs": compute_subs,
        "report_subs": {},
        "notes": notes,
    }


def _append_time_section(lines: List[str], breakdown: Dict[str, Any]) -> None:
    lines.append("## 时间花在哪")
    lines.append(
        f"- 准备/规划: {_format_sec_pct(breakdown.get('planning_sec'), breakdown.get('planning_pct'))}"
    )
    for k, v in dict(breakdown.get("planning_subs") or {}).items():
        if isinstance(v, (int, float)):
            lines.append(f"  - {k}: {v:.2f}s")
        else:
            lines.append(f"  - {k}: {v}")
    lines.append(
        f"- 读数据: {_format_sec_pct(breakdown.get('load_sec'), breakdown.get('load_pct'))}"
    )
    for k, v in dict(breakdown.get("load_subs") or {}).items():
        if isinstance(v, (int, float)):
            lines.append(f"  - {k}: {v:.2f}s")
        else:
            lines.append(f"  - {k}: {v}")
    lines.append(
        f"- 推进日历 / 引擎开销: {_format_sec_pct(breakdown.get('compute_sec'), breakdown.get('compute_pct'))}"
    )
    for k, v in dict(breakdown.get("compute_subs") or {}).items():
        if isinstance(v, (int, float)):
            lines.append(f"  - {k}: {v:.2f}s")
        else:
            lines.append(f"  - {k}: {v}")
    lines.append(
        f"- 写报告: {_format_sec_pct(breakdown.get('report_sec'), breakdown.get('report_pct'))}"
    )
    for note in list(breakdown.get("notes") or []):
        lines.append(f"- 说明: {note}")


def _schedule_from_case(
    case: Dict[str, Any],
    glance: Dict[str, Any],
    *,
    planner: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    plan = dict(glance.get("plan") or {})
    planner = dict(planner or {})
    mode = str(case.get("mode") or "")
    if mode == "slice_based":
        sr = case.get("slice_runtime") or {}
        return {
            "compute_workers": int(
                plan.get("compute_workers")
                or planner.get("compute_workers")
                or planner.get("compute_processes")
                or 1
            ),
            "reader_workers": int(
                plan.get("reader_workers")
                or planner.get("reader_workers")
                or sr.get("reader_workers")
                or 0
            ),
            "queue_depth": int(
                plan.get("max_queue")
                or planner.get("queue_capacity")
                or sr.get("queue_depth")
                or 0
            ),
            "slice_open_days": int(
                plan.get("slice_open_days") or planner.get("slice_open_days") or 0
            ),
            "formal_slices": int(
                sr.get("formal_slices_completed")
                or plan.get("total_slices")
                or planner.get("total_slices")
                or planner.get("dispatch_jobs")
                or 0
            ),
            "per_entity_load_count": int(sr.get("per_entity_load_count") or 0),
        }
    return {
        "workers": int(
            plan.get("worker")
            or planner.get("max_workers")
            or 0
        ),
        "job_count": int(
            (glance.get("job_batches") or {}).get("total")
            or planner.get("dispatch_jobs")
            or case.get("total_jobs")
            or 0
        ),
        "entities_per_job": int(
            plan.get("entity_per_job")
            or planner.get("entities_per_job")
            or 0
        ),
    }


def _normalize_engine_name(raw: Any) -> str:
    eng = str(raw or "duckdb").strip().lower()
    if eng == "pgsql":
        return "postgresql"
    return eng or "duckdb"


def _print_run_summary(
    case: Dict[str, Any],
    *,
    db_entry: dict,
    report_path: Path,
    versions: Dict[str, Any],
) -> None:
    mode = str(case.get("mode") or "")
    mode_label = _MODE_LABEL.get(mode, mode)
    engine = _normalize_engine_name(
        case.get("db_engine") or db_entry.get("engine") or "duckdb"
    )
    db_name = db_entry.get("name") or "—"
    wall = float(case.get("wall_time_s") or 0.0)
    entities = int(case.get("entities") or 0)
    days = int(case.get("timeline_points") or 0)
    rows = entities * days
    throughput = (rows / wall) if wall > 0 and rows > 0 else None
    success = "成功" if case.get("success") else "失败"
    speed = f"{throughput:,.0f} 股票×交易日/秒" if throughput is not None else "—"
    print("", flush=True)
    print("======== 性能测试摘要 ========", flush=True)
    print(
        f"版本: Backtest Engine {versions.get('backtest_engine')} / core {versions.get('core')}",
        flush=True,
    )
    print(f"模式: {mode_label}", flush=True)
    print(
        f"数据库: {report_engine_dirname(engine)} ({engine}) / {db_name}",
        flush=True,
    )
    print(f"总执行时间: {wall:.2f} 秒", flush=True)
    print(f"数据量: {entities} 股 × {days} 天 = {rows:,} 行", flush=True)
    print(f"处理速度: {speed}", flush=True)
    print(f"是否成功: {success}", flush=True)
    sr = case.get("slice_runtime") or {}
    if sr:
        print(
            f"切片: 装载 {sr.get('per_entity_load_count')} 次 / "
            f"片数 {sr.get('formal_slices_completed')} / "
            f"读进程 {sr.get('reader_workers')} / "
            f"预读排队 {sr.get('queue_depth')}",
            flush=True,
        )
    print(f"报告: {report_path}", flush=True)
    print("==============================", flush=True)


def _write_report(case: Dict[str, Any], *, db_entry: dict) -> Path:
    ensure_layout()
    mode = str(case.get("mode") or "")
    engine = _normalize_engine_name(
        case.get("db_engine") or db_entry.get("engine") or "duckdb"
    )
    versions = collect_perf_versions()
    be_ver = str(versions.get("backtest_engine") or be_module_version())
    entities = int(case.get("entities") or 0)
    out_dir = report_out_dir(
        be_version=be_ver,
        mode=mode,
        engine=engine,
        stock_count=entities,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = read_dataset_meta(engine=engine) or {}
    mode_label = _MODE_LABEL.get(mode, mode)
    env = _env_snapshot()
    run_at = utc_now_iso()
    perf = _load_performance_payload(case.get("output_dir"))
    glance = dict(perf.get("quick_summary") or {}) if perf else {}
    planner = dict(perf.get("planner") or {}) if perf else {}
    breakdown = _build_time_breakdown(mode=mode, glance=glance, perf=perf or {})
    schedule = _schedule_from_case(case, glance, planner=planner)
    days = int(case.get("timeline_points") or 0)
    rows = entities * days
    wall = float(case.get("wall_time_s") or 0.0)
    throughput = (rows / wall) if wall > 0 and rows > 0 else None
    parallelism = glance.get("parallelism")
    parallelism_eff = glance.get("parallelism_efficiency")
    success_label = "成功" if case.get("success") else "失败"
    eng_dir = report_engine_dirname(engine)
    stock_max = int(case.get("stock_count_max") or meta.get("stock_count") or entities)
    scale_frac = case.get("scale_fraction")

    if mode == "slice_based":
        desc = "按时间切片空策略基准：测引擎按片读数与推进日历的速度"
    else:
        desc = "按股票分包空策略基准：测引擎全段装载与计算的速度"

    report = {
        "case_name": case["case_id"],
        "run_at": run_at,
        "run_date": run_at,
        "module": "modules.backtest_engine",
        "description": desc,
        "versions": versions,
        "environment": env,
        "dataset": meta,
        "db": {
            "engine": engine,
            "engine_dir": eng_dir,
            "name": db_entry.get("name"),
            "paths": db_entry.get("paths"),
        },
        "metrics": {
            **case,
            "mode_label": mode_label,
            "sample_size": entities,
            "stock_count_max": stock_max,
            "scale_fraction": scale_frac,
            "data_rows": rows,
            "throughput_entity_day_per_s": throughput,
            "schedule": schedule,
            "time_split": breakdown,
            "parallelism": parallelism,
            "parallelism_efficiency": parallelism_eff,
            "report_dir": str(out_dir),
        },
    }
    (out_dir / "metrics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    mem = env.get("memory_gb")
    mem_s = f"{mem} GB" if mem is not None else "—"
    deps = dict(versions.get("dependencies") or {})
    dep_bits = [f"{k} {v}" for k, v in deps.items() if v]
    lines = [
        f"# 性能测试报告 — {mode_label} · N{entities} · {eng_dir}",
        "",
        "## 环境",
        f"- 跑测时间: {run_at}",
        f"- 回测引擎 (BE): {be_ver}",
        f"- core: {versions.get('core')}",
        f"- 相关模块: {', '.join(dep_bits) if dep_bits else '—'}",
        f"- 操作系统: {env.get('os')}",
        f"- CPU: {env.get('cpu')}",
        f"- 内存: {mem_s}",
        f"- Python: {env.get('python')}",
        f"- 数据库类型: {eng_dir} ({engine})",
        f"- 数据库名称: {report['db'].get('name')}",
        "",
        "## 结果",
        f"- 运行模式: {mode_label}",
        f"- 样本档: N{entities}"
        + (
            f"（最大 N{stock_max} 的 {float(scale_frac)*100:.0f}%）"
            if scale_frac is not None
            else ""
        ),
        f"- 总执行时间（秒）: {wall:.4f}",
        f"- 股票数: {entities}",
        f"- 交易日数: {days}",
        f"- 数据量（行）: {rows}",
        (
            f"- 处理速度（股票×交易日 / 秒）: {throughput:.2f}"
            if throughput is not None
            else "- 处理速度（股票×交易日 / 秒）: —"
        ),
        f"- 是否成功: {success_label}",
        "",
        "## 调度情况",
    ]
    if mode == "slice_based":
        lines.extend(
            [
                f"- 计算用几个进程: {schedule.get('compute_workers')}",
                f"- 读数据用几个进程: {schedule.get('reader_workers')}",
                f"- 预读排队深度: {schedule.get('queue_depth')}",
                f"- 每片多少个交易日: {schedule.get('slice_open_days') or '—'}",
                f"- 一共切了几片: {schedule.get('formal_slices')}",
                f"- 每只股票装载几次: {schedule.get('per_entity_load_count')}",
            ]
        )
    else:
        lines.extend(
            [
                f"- 同时开几个进程: {schedule.get('workers') or '—'}",
                f"- 任务包数量: {schedule.get('job_count') or '—'}",
                f"- 每包多少只股票: {schedule.get('entities_per_job') or '—'}",
            ]
        )

    lines.append("")
    _append_time_section(lines, breakdown)
    lines.extend(
        [
            "",
            "## 并行效果",
            f"- 并行效果: {parallelism if parallelism is not None else '—'}",
            f"- 并行效率: {parallelism_eff if parallelism_eff is not None else '—'}",
            "",
        ]
    )
    notes = list(case.get("warnings") or [])
    if notes:
        lines.append("## 备注")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")

    report_path = out_dir / "REPORT.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    # stash versions on case for CLI summary
    case["_versions"] = versions
    return report_path


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
        description="Run BE performance baselines across scale ladder "
        "(25%/50%/100% of max stocks)"
    )
    p.add_argument(
        "mode",
        choices=["entity_based", "slice_based"],
        help="BE mode / baseline strategy to run",
    )
    p.add_argument(
        "--db",
        default="duckdb",
        choices=["duckdb", "mysql", "pgsql", "postgresql"],
        help="perf DB engine (default: duckdb)",
    )
    p.add_argument(
        "--only-n",
        type=int,
        default=None,
        help="optional: run a single sample size instead of the full ladder",
    )
    args = p.parse_args(argv)
    mode = str(args.mode)
    engine = "postgresql" if args.db == "pgsql" else str(args.db)
    if engine not in {"duckdb", "mysql", "postgresql"}:
        raise SystemExit(f"--db {engine} 不支持")

    entry_probe = active_perf_entry(engine=engine)
    if not entry_probe:
        raise SystemExit(
            f"no perf {engine} entry; run db_creation.py --db {engine} first"
        )

    meta = read_dataset_meta(engine=engine)
    if not meta:
        raise SystemExit(
            f"perf {engine} entry has no dataset meta; re-run db_creation.py"
        )
    all_ids = universe_ids_from_meta(meta)
    stock_max = int(meta.get("stock_count") or len(all_ids) or DEFAULT_STOCK_COUNT)
    if len(all_ids) < stock_max:
        stock_max = len(all_ids)
    timeline = open_dates_from_meta(meta)
    if not timeline:
        raise SystemExit("no open dates for dataset window")

    sizes = scale_stock_counts(stock_max)
    if args.only_n is not None:
        only = max(1, min(int(args.only_n), stock_max))
        sizes = [only]

    step(
        "test",
        f"dataset max_stocks={stock_max} open_days={meta.get('open_days')} "
        f"klines={meta.get('kline_rows')} mode={mode} db={engine} "
        f"ladder={sizes}",
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

    step("test", f"attach perf {engine}…")
    db_entry = _attach_perf_db(entry_probe)
    step("test", f"using {engine} {db_entry.get('name')}")

    any_fail = False
    last_path: Optional[Path] = None
    for i, n in enumerate(sizes, start=1):
        ids = list(all_ids[:n])
        frac = (n / stock_max) if stock_max else 1.0
        step(
            "test",
            f"scale [{i}/{len(sizes)}] N{n} "
            f"({frac*100:.0f}% of max {stock_max})",
        )
        case = _run_one(
            ids,
            db_entry=db_entry,
            meta=meta,
            mode=mode,
        )
        case["stock_count_max"] = stock_max
        case["scale_fraction"] = round(frac, 4)
        path = _write_report(case, db_entry=db_entry)
        last_path = path
        _print_run_summary(
            case,
            db_entry=db_entry,
            report_path=path,
            versions=dict(case.get("_versions") or collect_perf_versions()),
        )
        if not case.get("success"):
            any_fail = True

    overall = write_overall_report(
        mode=mode,
        mode_label=_MODE_LABEL.get(mode, mode),
        be_version=be_module_version(),
    )
    print(f"总览报告: {overall}", flush=True)
    if last_path is not None:
        print(f"末档报告: {last_path}", flush=True)
    return 1 if any_fail else 0


if __name__ == "__main__":
    import multiprocessing as mp

    if mp.current_process().name == "MainProcess":
        raise SystemExit(main())
