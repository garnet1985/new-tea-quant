"""Strategy scanner run launcher: trigger + progress polling (BFF).

Mirrors the workbench step-run pattern:
- trigger returns a job_id immediately and spawns a background thread
- progress is persisted to disk via ProgressRecorder (polling reads disk only)
- when completed, progress reaches 100 and includes the final scan report
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from core.infra.project_context import ProjectContext
from core.modules.data_manager import DataManager
from core.modules.strategy.core.engines.scanner.helpers import (
    ScanCacheManager,
    ScanDateResolver,
)
from core.modules.strategy.core.engines.scanner.pipeline import ScannerPipeline
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)
from core.modules.strategy.core.services.progress import ProgressRecorder

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_JOBS: Dict[str, Dict[str, Any]] = {}
_ACTIVE_JOB_ID: Optional[str] = None


def _job_create(*, strategy_name: str, demo: bool, force: bool) -> str:
    jid = str(uuid.uuid4())
    name = str(strategy_name).strip()
    _JOBS[jid] = {
        "strategy_name": name,
        "demo": bool(demo),
        "force": bool(force),
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


def _seed_progress_file(strategy_name: str, job_id: str, *, demo: bool, force: bool) -> None:
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
            "force": bool(force),
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
    """ScannerPipeline on_progress payload -> disk progress snapshot."""
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


def _opportunity_rows_for_report(opportunities: List[Any]) -> List[Dict[str, Any]]:
    """与进度落盘 ``report.opportunities`` 结构一致，供 BFF / 列表预热。"""
    return [
        {
            "stock_id": opp.stock_id,
            "stock_name": opp.stock_name,
            "trigger_date": opp.trigger_date,
            "trigger_price": opp.trigger_price,
            "extra_fields": opp.extra_fields or {},
        }
        for opp in opportunities
    ]


def _disk_mark_completed(
    strategy_name: str,
    job_id: str,
    report: Dict[str, Any],
    *,
    cache_key: str = "",
) -> None:
    sn = str(strategy_name).strip()
    jid = str(job_id).strip()
    rec = ProgressRecorder.for_scanner_run(sn, jid)
    prev = rec.get_progress()
    base = dict(prev) if isinstance(prev, dict) else {}
    packed_report = dict(report or {})
    try:
        scan_date = str(packed_report.get("date") or "").strip()
        disk_key = str(cache_key or packed_report.get("strategy_key") or sn).strip()
        if scan_date and disk_key:
            cache = ScanCacheManager(disk_key)
            opportunities = cache.load_opportunities(scan_date)
            packed_report["opportunities"] = _opportunity_rows_for_report(opportunities)
    except Exception:
        logger.exception(
            "Failed to attach opportunities for job_id=%s strategy=%s", jid, sn
        )
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


def _strategy_cache_key(info: EnabledStrategyInfo, fallback: str = "") -> str:
    """与 ``ScannerPipeline.run`` 写盘目录一致：key 优先，否则 unique_relative_path。"""
    return str(info.key or info.unique_relative_path or fallback or "").strip()


def _resolve_strategy(strategy_name: str) -> tuple[Optional[EnabledStrategyInfo], Optional[str]]:
    """Load strategy from userspace (explicit name may be disabled)."""
    name = str(strategy_name or "").strip()
    if not name:
        return None, "strategy_name 无效"
    targets = ScannerPipeline.resolve_targets(name)
    if not targets:
        return None, "策略不存在或无法加载"
    return targets[0], None


def get_scan_page_context() -> Dict[str, Any]:
    """Scan UI: ``data.json`` as-of meta + demo-mode cutoff date."""
    from core.modules.data_source.catalog.freshness_probe import get_data_end_meta

    data_end: Dict[str, Any] = {}
    demo_scan_cutoff_date = ""
    try:
        data_mgr = DataManager(is_verbose=False)
        data_mgr.initialize()
        data_end = get_data_end_meta(data_mgr)
        demo_scan_cutoff_date = ScanDateResolver.resolve_anchor_date(
            data_mgr,
            use_strict=False,
        )
    except Exception:
        logger.debug("get_scan_page_context failed", exc_info=True)
    return {
        "data_end": data_end,
        "demo_scan_cutoff_date": demo_scan_cutoff_date or None,
    }


def get_scan_readiness(*, strategy_name: str, demo: bool = False) -> Dict[str, Any]:
    """Opaque UI hint: ``primary_action`` is ``run`` or ``rerun`` (disk hit for current cutoff).

    若存在与当前截止日对齐的磁盘缓存，额外返回 ``report``（与扫描完成进度里的 ``report`` 同形）。
    """
    name = str(strategy_name or "").strip()
    if not name:
        return {"primary_action": "run"}
    try:
        info, err = _resolve_strategy(name)
        if err or info is None:
            return {"primary_action": "run"}

        path_key = _strategy_cache_key(info, name)
        data_mgr = DataManager(is_verbose=False)
        kline_latest = ScanDateResolver.load_kline_latest_date(data_mgr)
        if not kline_latest:
            return {"primary_action": "run"}

        settings = StrategySettings.from_dict(dict(info.settings or {}))
        settings.apply_defaults()
        use_strict = bool(settings.scanner.use_strict_previous_trading_day)
        if demo:
            use_strict = False
        if not demo:
            cal_latest = ScanDateResolver.resolve_anchor_date(
                data_mgr, use_strict=use_strict
            )
            if not cal_latest or cal_latest != kline_latest:
                return {"primary_action": "run"}

        resolver = ScanDateResolver(data_mgr)
        scan_date, stock_ids = resolver.resolve_scan_date(use_strict=use_strict)
        csv_path = (
            ProjectContext.path.get_strategy_scan_results_directory(path_key)
            / scan_date
            / "opportunities.csv"
        )
        if not csv_path.is_file():
            return {"primary_action": "run"}

        cache = ScanCacheManager(path_key, settings.scanner.max_cache_days)
        opportunities = cache.load_opportunities(scan_date)
        stocks_with_opps = {o.stock_id for o in opportunities} if opportunities else set()
        summary = {
            "total_opportunities": len(opportunities),
            "total_stocks": len(stocks_with_opps),
            "stocks_with_opportunities": sorted(stocks_with_opps),
        }
        report: Dict[str, Any] = {
            "date": scan_date,
            "total_opportunities": len(opportunities),
            "total_stocks": len(stock_ids),
            "summary": summary,
            "opportunities": _opportunity_rows_for_report(opportunities),
        }
        return {"primary_action": "rerun", "report": report}
    except Exception:
        logger.debug("get_scan_readiness failed strategy=%s", name, exc_info=True)
        return {"primary_action": "run"}


def _background_scan_job(job_id: str, strategy_name: str, *, demo: bool, force: bool) -> None:
    _job_update(job_id, status="running", progress=1.0)
    _disk_mark_running(strategy_name, job_id)
    try:
        info, err = _resolve_strategy(strategy_name)
        if err or info is None:
            raise ValueError(err or "无法解析策略")

        path_key = _strategy_cache_key(info, strategy_name)
        data_mgr = DataManager(is_verbose=False)

        kline_latest = ScanDateResolver.load_kline_latest_date(data_mgr)
        if not kline_latest:
            raise ValueError("无法解析 K 线最新日期（sys_stock_klines 可能为空）")

        settings = StrategySettings.from_dict(dict(info.settings or {}))
        settings.apply_defaults()
        use_strict = bool(settings.scanner.use_strict_previous_trading_day)
        if demo:
            settings.scanner.set_use_strict_previous_trading_day(False)
            use_strict = False

        if not demo:
            cal_latest = ScanDateResolver.resolve_anchor_date(
                data_mgr, use_strict=use_strict
            )
            if not cal_latest:
                raise ValueError("无法解析最新已完成交易日（日历服务不可用）")
            if cal_latest != kline_latest:
                raise ValueError(
                    f"数据未对齐最新交易日：anchor={cal_latest}，kline={kline_latest} "
                    f"(strict={use_strict})"
                )

        def _on_progress(payload: Dict[str, Any]) -> None:
            _disk_tick_progress(strategy_name, job_id, payload)

        report = ScannerPipeline.run(
            info,
            settings,
            force=bool(force),
            on_progress=_on_progress,
            data_manager=data_mgr,
        )
        if isinstance(report, dict):
            report.setdefault("strategy_key", path_key)
        _job_update(job_id, status="completed", progress=100.0)
        _disk_mark_completed(
            strategy_name,
            job_id,
            report if isinstance(report, dict) else {},
            cache_key=path_key,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Scanner run failed job_id=%s strategy=%s", job_id, strategy_name)
        _job_update(job_id, status="failed", progress=100.0, error=str(exc))
        _disk_mark_failed(strategy_name, job_id, str(exc))
    finally:
        global _ACTIVE_JOB_ID  # noqa: PLW0603
        with _LOCK:
            if str(_ACTIVE_JOB_ID or "").strip() == str(job_id).strip():
                _ACTIVE_JOB_ID = None


def trigger_strategy_scan_run(
    *, strategy_name: str, demo: bool = False, force: bool = False
) -> Dict[str, Any]:
    t0 = time.time()
    name = str(strategy_name or "").strip()
    if not name:
        return {"is_triggered": False, "reason": "strategy_name 无效"}

    global _ACTIVE_JOB_ID  # noqa: PLW0603
    with _LOCK:
        if _has_active_scan_locked():
            return {"is_triggered": False, "reason": "已有扫描任务在运行中，请稍后重试"}
        jid = _job_create(strategy_name=name, demo=demo, force=force)
        _ACTIVE_JOB_ID = jid
    _seed_progress_file(name, jid, demo=demo, force=force)
    logger.info(
        "[scanner_run] triggered job_id=%s strategy=%s demo=%s force=%s in %.1fms",
        jid,
        name,
        bool(demo),
        bool(force),
        (time.time() - t0) * 1000.0,
    )
    thread = threading.Thread(
        target=_background_scan_job,
        args=(jid, name),
        kwargs={"demo": bool(demo), "force": bool(force)},
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
        for k in ("total_jobs", "done_jobs", "last_job_id", "last_job_status"):
            if k in disk:
                out[k] = disk.get(k)
    return out


__all__ = [
    "get_scan_page_context",
    "get_scan_progress",
    "get_scan_readiness",
    "trigger_strategy_scan_run",
]
