"""Pickle-safe BE perf workloads (must not be run as ``__main__``).

ProcessPool spawn re-imports this module by name; callbacks live here so
``python test_script.py`` does not pickle ``__main__.*`` (which re-runs CLI).
"""
from __future__ import annotations

import time
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

_PERF_DB_PATHS_KEY = "_perf_duckdb_paths"
_PERF_OVERLAY_CFG: Optional[Dict[str, Any]] = None
_ORIG_DB_CFG_RO = None
_WORKER_PERF_DM_READY = False


def paths_key() -> str:
    return _PERF_DB_PATHS_KEY


def paths_from_payload(payload: Dict[str, Any]) -> Dict[str, str]:
    raw = payload.get(_PERF_DB_PATHS_KEY)
    if not isinstance(raw, dict):
        global_block = payload.get("global") or {}
        raw = (
            global_block.get(_PERF_DB_PATHS_KEY)
            if isinstance(global_block, dict)
            else None
        )
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, str] = {}
    for key in ("data", "tag", "strategy"):
        val = raw.get(key)
        if val:
            out[key] = str(val)
    return out


def stamp_perf_db_paths(
    jobs: List[Dict[str, Any]], paths: Dict[str, Any]
) -> List[Dict[str, Any]]:
    stamped: List[Dict[str, Any]] = []
    path_block = {
        "data": str(paths.get("data") or ""),
        "tag": str(paths.get("tag") or ""),
        "strategy": str(paths.get("strategy") or ""),
    }
    for job in jobs:
        payload = dict(job.get("payload") or {})
        payload[_PERF_DB_PATHS_KEY] = path_block
        stamped.append({**job, "payload": payload})
    return stamped


def entity_ids_from_payload(payload: Dict[str, Any]) -> List[str]:
    specified = payload.get("entity_specified")
    if isinstance(specified, list) and specified:
        out: List[str] = []
        for item in specified:
            if isinstance(item, dict):
                sid = str(item.get("id") or "").strip()
            else:
                sid = str(item or "").strip()
            if sid:
                out.append(sid)
        return out
    ids = payload.get("entity_ids")
    if isinstance(ids, list):
        return [str(x).strip() for x in ids if str(x).strip()]
    return []


def window_from_job(ctx) -> Tuple[str, str]:
    from core.modules.backtest_engine.core.timeline.timeline import Timeline

    payload = getattr(ctx, "payload", None) or {}
    timeline = Timeline.read_for_job(payload)
    if timeline is None:
        raise RuntimeError("perf IO: timeline missing on job payload")
    clipped = timeline.clipped()
    points = list(clipped.points or ())
    if not points:
        raise RuntimeError("perf IO: timeline has no points")
    start = str(clipped.start or points[0]).strip() or points[0]
    end = str(clipped.end or points[-1]).strip() or points[-1]
    return start, end


def bar_date(bar: Dict[str, Any]) -> str:
    raw = bar.get("date")
    if raw is None:
        return ""
    text = str(raw).strip()
    if len(text) >= 10 and text[4] == "-":
        return text.replace("-", "")[:8]
    return text[:8]


def _perf_database_config_read_only() -> Dict[str, Any]:
    global _PERF_OVERLAY_CFG, _ORIG_DB_CFG_RO
    if _PERF_OVERLAY_CFG is not None:
        cfg = deepcopy(_PERF_OVERLAY_CFG)
        duck = cfg.setdefault("duckdb", {})
        domains = duck.setdefault("domains", {})
        if isinstance(domains, dict):
            for block in domains.values():
                if isinstance(block, dict):
                    block["read_only"] = True
        return cfg
    if _ORIG_DB_CFG_RO is not None:
        return _ORIG_DB_CFG_RO()
    from core.infra.db.core.engines.duckdb import process_pool_scope as pps

    return pps.database_config_read_only()


def install_perf_worker_db_overlay(paths: Dict[str, str]) -> None:
    """Point worker RO DuckDB bootstrap at perf files (spawn-safe via env)."""
    import json
    import os

    from core.infra.db import Db
    from core.infra.db.core.engines.duckdb import process_pool_scope as pps
    from core.infra.db.core.engines.duckdb.process_pool_scope import (
        _ENV_DUCKDB_CONFIG_JSON,
    )

    global _PERF_OVERLAY_CFG, _ORIG_DB_CFG_RO
    if not paths.get("data"):
        return
    _PERF_OVERLAY_CFG = Db.duckdb.overlay_domain_paths(
        data=paths.get("data"),
        tag=paths.get("tag"),
        strategy=paths.get("strategy"),
    )
    # Spawn workers inherit env; database_config_read_only reads this key.
    os.environ[_ENV_DUCKDB_CONFIG_JSON] = json.dumps(
        _PERF_OVERLAY_CFG, ensure_ascii=False
    )
    if _ORIG_DB_CFG_RO is None:
        _ORIG_DB_CFG_RO = pps.database_config_read_only
    pps.database_config_read_only = _perf_database_config_read_only  # type: ignore[assignment]


def data_manager_for_io_job(ctx) -> Any:
    import multiprocessing as mp

    from core.modules.backtest_engine.core.shared.worker_data_runtime import (
        bootstrap_worker_data_manager,
        create_worker_data_manager,
        release_worker_runtime,
    )
    from core.modules.data_manager import DataManager

    global _WORKER_PERF_DM_READY

    payload = getattr(ctx, "payload", None) or {}
    paths = paths_from_payload(payload)

    if mp.current_process().name == "MainProcess":
        dm = DataManager.get_instance()
        if dm is not None:
            return dm
        return bootstrap_worker_data_manager()

    if not paths:
        return bootstrap_worker_data_manager()

    install_perf_worker_db_overlay(paths)
    if _WORKER_PERF_DM_READY:
        return bootstrap_worker_data_manager()

    release_worker_runtime()
    DataManager.reset_instance()
    dm = create_worker_data_manager()
    _WORKER_PERF_DM_READY = True
    return dm


def idle_on_tick(ctx, point: str, index: int) -> None:
    _ = (ctx, point, index)


def idle_on_ticks_complete(ctx, timeline) -> Dict[str, Any]:
    points = list(getattr(timeline, "points", None) or [])
    entities = len(entity_ids_from_payload(getattr(ctx, "payload", None) or {}))
    return {
        "tick_count": len(points),
        "entities_in_job": entities,
        "load_rows": 0,
        "bars_hit": 0,
    }


def io_on_before_task_start(ctx) -> Dict[str, Any]:
    dm = data_manager_for_io_job(ctx)
    entity_ids = entity_ids_from_payload(getattr(ctx, "payload", None) or {})
    start, end = window_from_job(ctx)
    t0 = time.perf_counter()
    raw_by_id = dm.stock.kline.load_batch(
        entity_ids,
        term="daily",
        start_date=start,
        end_date=end,
        adjust="none",
        filter_negative=False,
    )
    by_entity: Dict[str, Dict[str, Dict[str, Any]]] = {}
    load_rows = 0
    for sid in entity_ids:
        rows = raw_by_id.get(sid) or []
        day_map: Dict[str, Dict[str, Any]] = {}
        for bar in rows:
            if not isinstance(bar, dict):
                continue
            dt = bar_date(bar)
            if not dt:
                continue
            day_map[dt] = bar
            load_rows += 1
        by_entity[sid] = day_map
    return {
        "by_entity": by_entity,
        "entity_ids": entity_ids,
        "load_rows": load_rows,
        "load_sec": time.perf_counter() - t0,
        "bars_hit": 0,
        "close_sum": 0.0,
    }


def io_on_tick(ctx, point: str, index: int) -> None:
    _ = index
    session = getattr(ctx, "init", None)
    if not isinstance(session, dict):
        return
    by_entity = session.get("by_entity") or {}
    entity_ids = session.get("entity_ids") or []
    day = str(point).strip()
    hits = 0
    close_sum = 0.0
    for sid in entity_ids:
        bar = by_entity.get(sid, {}).get(day)
        if not bar:
            continue
        hits += 1
        try:
            close_sum += float(bar.get("close") or 0.0)
        except (TypeError, ValueError):
            pass
        _ = bar.get("volume")
    session["bars_hit"] = int(session.get("bars_hit") or 0) + hits
    session["close_sum"] = float(session.get("close_sum") or 0.0) + close_sum


def io_on_ticks_complete(ctx, timeline) -> Dict[str, Any]:
    points = list(getattr(timeline, "points", None) or [])
    session = getattr(ctx, "init", None)
    if not isinstance(session, dict):
        session = {}
    entities = session.get("entity_ids") or entity_ids_from_payload(
        getattr(ctx, "payload", None) or {}
    )
    return {
        "tick_count": len(points),
        "entities_in_job": len(entities),
        "load_rows": int(session.get("load_rows") or 0),
        "bars_hit": int(session.get("bars_hit") or 0),
        "load_sec": float(session.get("load_sec") or 0.0),
        "close_sum": float(session.get("close_sum") or 0.0),
    }
