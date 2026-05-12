"""Strategy scanner run launcher: trigger + progress polling.

This mirrors the workbench step-run pattern:
- trigger returns a job_id immediately and spawns a background thread
- progress is persisted to disk via ProgressRecorder (polling reads disk only)
- when completed, progress reaches 100 and includes the final scan report
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any, Dict, Optional

from core.infra.project_context.path_manager import PathManager
from core.modules.data_manager import DataManager
from core.modules.strategy.engines.scanner.scanner import Scanner
from core.modules.strategy.services.discovery import StrategyDiscoveryHelper
from core.modules.strategy.services.progress import ProgressRecorder
# NOTE: keep launcher import-light; DB lookups live in DataManager services in background thread.

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_JOBS: Dict[str, Dict[str, Any]] = {}
_ACTIVE_JOB_ID: Optional[str] = None


def _job_create(*, strategy_name: str, demo: bool) -> str:
    jid = str(uuid.uuid4())
    name = str(strategy_name).strip()
    # Caller must hold _LOCK when mutating _JOBS / _ACTIVE_JOB_ID.
    _JOBS[jid] = {
        "strategy_name": name,
        "demo": bool(demo),
        "progress": 0.0,
        "status": "queued",
        "error": None,
    }
    return jid


def _job_update(job_id: str, **fields: Any) -> None:
    with _LOCK:
        row = _JOBS.get(job_id)
        if row is None:
            return
        row.update(fields)


def _has_active_scan_locked() -> bool:
    """Single-flight guard: at most one scan job globally."""
    global _ACTIVE_JOB_ID  # noqa: PLW0603
    jid = str(_ACTIVE_JOB_ID or "").strip()
    if not jid:
        return False
    row = _JOBS.get(jid)
    if not isinstance(row, dict):
        _ACTIVE_JOB_ID = None
        return False
    st = str(row.get("status") or "").strip().lower()
    if st in ("completed", "failed"):
        _ACTIVE_JOB_ID = None
        return False
    return True


def _seed_progress_file(strategy_name: str, job_id: str, *, demo: bool) -> None:
    sn = str(strategy_name).strip()
    jid = str(job_id).strip()
    ProgressRecorder.for_scanner_run(sn, jid).record(
        {
            "strategy_name": sn,
            "run_id": jid,
            "phase": "queued",
            "status": "queued",
            "progress_pct": 0,
            "demo": bool(demo),
        }
    )


def _disk_mark_running(strategy_name: str, job_id: str) -> None:
    sn = str(strategy_name).strip()
    jid = str(job_id).strip()
    rec = ProgressRecorder.for_scanner_run(sn, jid)
    prev = rec.get_progress()
    base = dict(prev) if isinstance(prev, dict) else {}
    base.update(
        {
            "strategy_name": sn,
            "run_id": jid,
            "phase": "running",
            "status": "running",
            "progress_pct": max(int(base.get("progress_pct") or 0), 1),
        }
    )
    rec.record(base)


def _disk_tick_progress(strategy_name: str, job_id: str, payload: Dict[str, Any]) -> None:
    """ProcessWorker job_done callback payload -> disk progress snapshot."""
    sn = str(strategy_name).strip()
    jid = str(job_id).strip()

    try:
        pct = float(payload.get("progress_pct", 0) or 0)
    except (TypeError, ValueError):
        pct = 0.0
    pct = max(0.0, min(99.9, pct))

    total_jobs = int(payload.get("total_jobs", 0) or 0)
    done_jobs = (
        int(payload.get("completed_jobs", 0) or 0)
        + int(payload.get("failed_jobs", 0) or 0)
        + int(payload.get("cancelled_jobs", 0) or 0)
    )

    rec = ProgressRecorder.for_scanner_run(sn, jid)
    prev = rec.get_progress()
    base = dict(prev) if isinstance(prev, dict) else {}
    base.update(
        {
            "strategy_name": sn,
            "run_id": jid,
            "phase": "running",
            "status": "running",
            "progress_pct": round(pct, 2),
            "total_jobs": total_jobs,
            "done_jobs": done_jobs,
            "last_job_id": str(payload.get("last_job_id") or ""),
            "last_job_status": str(payload.get("last_job_status") or ""),
        }
    )
    rec.record(base)


def _disk_mark_failed(strategy_name: str, job_id: str, error: str) -> None:
    sn = str(strategy_name).strip()
    jid = str(job_id).strip()
    rec = ProgressRecorder.for_scanner_run(sn, jid)
    prev = rec.get_progress()
    base = dict(prev) if isinstance(prev, dict) else {}
    base.update(
        {
            "strategy_name": sn,
            "run_id": jid,
            "phase": "failed",
            "status": "failed",
            "progress_pct": 100,
            "error": str(error),
        }
    )
    rec.record(base)


def _disk_mark_completed(strategy_name: str, job_id: str, report: Dict[str, Any]) -> None:
    sn = str(strategy_name).strip()
    jid = str(job_id).strip()
    rec = ProgressRecorder.for_scanner_run(sn, jid)
    prev = rec.get_progress()
    base = dict(prev) if isinstance(prev, dict) else {}
    packed_report = dict(report or {})
    # Attach opportunity details from scan cache (align with CLI output needs).
    try:
        scan_date = str(packed_report.get("date") or "").strip()
        if scan_date:
            from core.modules.strategy.engines.scanner.helpers.cache_manager import ScanCacheManager

            cache = ScanCacheManager(sn)
            opportunities = cache.load_opportunities(scan_date)
            packed_report["opportunities"] = [
                {
                    "stock_id": opp.stock_id,
                    "stock_name": opp.stock_name,
                    "trigger_date": opp.trigger_date,
                    "trigger_price": opp.trigger_price,
                    "extra_fields": opp.extra_fields or {},
                }
                for opp in opportunities
            ]
    except Exception:
        logger.exception("Failed to attach opportunities for job_id=%s strategy=%s", jid, sn)
    base.update(
        {
            "strategy_name": sn,
            "run_id": jid,
            "phase": "completed",
            "status": "completed",
            "progress_pct": 100,
            "report": packed_report,
        }
    )
    base.pop("error", None)
    rec.record(base)


def _resolve_discovered_strategy(strategy_name: str):
    """Load strategy from userspace. Keep import-light to avoid BFF/Flask cycles."""
    name = str(strategy_name or "").strip()
    if not name:
        return None, "strategy_name 无效"
    folder = PathManager.userspace() / "strategies" / name
    discovered = StrategyDiscoveryHelper.load_strategy(folder)
    if discovered is None:
        return None, "策略不存在或无法加载"
    discovered.validate_required_fields()
    return discovered, None


def _background_scan_job(job_id: str, strategy_name: str, *, demo: bool) -> None:
    _job_update(job_id, status="running", progress=1.0)
    _disk_mark_running(strategy_name, job_id)
    try:
        discovered, err = _resolve_discovered_strategy(strategy_name)
        if err or discovered is None:
            raise ValueError(err or "无法解析策略")

        data_mgr = DataManager(is_verbose=False)

        # demo rules (backend-only):
        # - demo=True: scan cutoff uses DB latest daily kline date.
        # - demo=False: require calendar latest completed trading date == DB latest daily kline date.
        kline_latest = str(data_mgr.stock.kline.load_latest_date("daily") or "").strip()
        if not kline_latest:
            raise ValueError("无法解析 K 线最新日期（sys_stock_klines 可能为空）")
        if not demo:
            cal_latest = str(data_mgr.service.calendar.get_latest_completed_trading_date() or "").strip()
            if not cal_latest:
                raise ValueError("无法解析最新已完成交易日（日历服务不可用）")
            if cal_latest != kline_latest:
                raise ValueError(f"数据未对齐最新交易日：calendar={cal_latest}，kline={kline_latest}")

        # demo == True: relax strict-previous-trading-day check (use latest available)
        # We do this by overriding scanner settings temporarily.
        scanner = Scanner(
            strategy_name=strategy_name,
            data_manager=data_mgr,
            is_verbose=False,
            strategy_info=discovered,
        )
        if demo:
            try:
                scanner.settings.scanner["use_strict_previous_trading_day"] = False
            except Exception:
                pass

        def _on_job_done(payload: Dict[str, Any]) -> None:
            _disk_tick_progress(strategy_name, job_id, payload)

        report = scanner.scan(on_job_done=_on_job_done)
        _job_update(job_id, status="completed", progress=100.0)
        _disk_mark_completed(strategy_name, job_id, report if isinstance(report, dict) else {})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Scanner run failed job_id=%s strategy=%s", job_id, strategy_name)
        _job_update(job_id, status="failed", progress=100.0, error=str(exc))
        _disk_mark_failed(strategy_name, job_id, str(exc))
    finally:
        global _ACTIVE_JOB_ID  # noqa: PLW0603
        with _LOCK:
            if str(_ACTIVE_JOB_ID or "").strip() == str(job_id).strip():
                _ACTIVE_JOB_ID = None


def trigger_strategy_scan_run(*, strategy_name: str, demo: bool = False) -> Dict[str, Any]:
    t0 = time.time()
    name = str(strategy_name or "").strip()
    if not name:
        return {"is_triggered": False, "reason": "strategy_name 无效"}

    global _ACTIVE_JOB_ID  # noqa: PLW0603
    with _LOCK:
        if _has_active_scan_locked():
            return {"is_triggered": False, "reason": "已有扫描任务在运行中，请稍后重试"}
        jid = _job_create(strategy_name=name, demo=demo)
        _ACTIVE_JOB_ID = jid
    _seed_progress_file(name, jid, demo=demo)
    logger.info(
        "[scanner_run] triggered job_id=%s strategy=%s demo=%s in %.1fms",
        jid,
        name,
        bool(demo),
        (time.time() - t0) * 1000.0,
    )
    thread = threading.Thread(
        target=_background_scan_job,
        args=(jid, name),
        kwargs={"demo": bool(demo)},
        daemon=True,
        name=f"scanner-run-{jid[:8]}",
    )
    thread.start()
    return {"is_triggered": True, "job_id": jid}


def get_scan_progress(*, strategy_name: str, job_id: str) -> Optional[Dict[str, Any]]:
    """Polling reads disk only; returns None if not found/mismatch."""
    jid = str(job_id or "").strip()
    if not jid:
        return None
    name = str(strategy_name or "").strip()
    disk = ProgressRecorder.for_scanner_run(name, jid).get_progress()
    if not isinstance(disk, dict) or not disk:
        return None
    sn = str(disk.get("strategy_name") or "").strip()
    if sn and sn != name:
        return None

    status = str(disk.get("status") or "").strip().lower()
    phase = str(disk.get("phase") or "").strip().lower()
    err = disk.get("error")

    if status == "failed" or phase == "failed":
        out: Dict[str, Any] = {
            "progress": 100.0,
            "status": "failed",
            "job_id": jid,
            "is_success": False,
        }
        if err:
            out["reason"] = str(err)
        return out

    try:
        pct = float(disk.get("progress_pct") or 0)
    except (TypeError, ValueError):
        pct = 0.0
    pct = max(0.0, min(100.0, pct))
    done = pct >= 100.0 or status == "completed" or phase == "completed"

    out = {
        "progress": round(pct, 2),
        "status": "completed" if done else "running",
        "job_id": jid,
    }
    if "demo" in disk:
        out["demo"] = bool(disk.get("demo"))
    if done:
        out["is_success"] = True
        report = disk.get("report")
        if isinstance(report, dict):
            out["report"] = report
    else:
        out["is_success"] = None
        # Optional live fields
        for k in ("total_jobs", "done_jobs", "last_job_id", "last_job_status"):
            if k in disk:
                out[k] = disk.get(k)
    return out

