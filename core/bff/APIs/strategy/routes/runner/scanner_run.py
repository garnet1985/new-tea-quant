"""BFF scanner async shell: single-flight + thread; domain on ``Strategy.scan_run`` / ``ScanProgress``."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any, Dict, Optional

from core.modules.strategy import Strategy

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_ACTIVE_JOB_ID: Optional[str] = None


def _has_active_scan_locked() -> bool:
    global _ACTIVE_JOB_ID  # noqa: PLW0603
    jid = str(_ACTIVE_JOB_ID or "").strip()
    if not jid:
        return False
    # Active flag cleared in background finally; presence means in-flight.
    return True


def get_scan_page_context() -> Dict[str, Any]:
    return Strategy.scan_page_context()


def get_scan_readiness(*, strategy_name: str, demo: bool = False) -> Dict[str, Any]:
    return Strategy.scan_readiness(strategy_name, demo=bool(demo))


def get_scan_progress(*, strategy_name: str, job_id: str) -> Optional[Dict[str, Any]]:
    return Strategy.get_scan_progress(strategy_name, job_id)


def _background_scan_job(
    job_id: str,
    strategy_name: str,
    *,
    demo: bool,
    force: bool,
    run_post_process: bool,
) -> None:
    try:
        Strategy.scan_run(
            strategy_name,
            progress_id=job_id,
            demo=bool(demo),
            force=bool(force),
            run_post_process=bool(run_post_process),
        )
    except Exception as exc:
        logger.exception(
            "background scan job failed job_id=%s strategy=%s",
            job_id,
            strategy_name,
        )
    finally:
        global _ACTIVE_JOB_ID  # noqa: PLW0603
        with _LOCK:
            if str(_ACTIVE_JOB_ID or "").strip() == str(job_id).strip():
                _ACTIVE_JOB_ID = None


def trigger_strategy_scan_run(
    *,
    strategy_name: str,
    demo: bool = False,
    force: bool = False,
    run_post_process: bool = True,
) -> Dict[str, Any]:
    t0 = time.time()
    name = str(strategy_name or "").strip()
    if not name:
        return {"is_triggered": False, "reason": "strategy_name 无效"}

    # 严格模式：启动线程前先做数据门禁，避免先跑进度再失败
    block = Strategy.scan_block_reason(demo=bool(demo))
    if block:
        return {"is_triggered": False, "reason": block}

    global _ACTIVE_JOB_ID  # noqa: PLW0603
    with _LOCK:
        if _has_active_scan_locked():
            return {"is_triggered": False, "reason": "已有扫描任务在运行中，请稍后重试"}
        jid = str(uuid.uuid4())
        _ACTIVE_JOB_ID = jid

    Strategy.seed_scan_progress(
        name,
        jid,
        demo=bool(demo),
        force=bool(force),
        run_post_process=bool(run_post_process),
    )
    logger.info(
        "[scanner_run] triggered job_id=%s strategy=%s demo=%s force=%s "
        "run_post_process=%s in %.1fms",
        jid,
        name,
        bool(demo),
        bool(force),
        bool(run_post_process),
        (time.time() - t0) * 1000.0,
    )
    thread = threading.Thread(
        target=_background_scan_job,
        args=(jid, name),
        kwargs={
            "demo": bool(demo),
            "force": bool(force),
            "run_post_process": bool(run_post_process),
        },
        daemon=True,
        name=f"scanner-run-{jid[:8]}",
    )
    thread.start()
    return {"is_triggered": True, "job_id": jid, "strategy_name": name}


__all__ = [
    "get_scan_page_context",
    "get_scan_progress",
    "get_scan_readiness",
    "trigger_strategy_scan_run",
]
