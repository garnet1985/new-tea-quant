"""数据 renew：agent 侧异步壳（域执行在 DataSourceManager）。"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Dict, Optional

from core.infra.job_pipeline import JobPipeline
from core.infra.job_pipeline.contracts import JobRunningBusyError
from core.modules.data_source import DataSourceManager

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_ACTIVE: Optional[Dict[str, Any]] = None


def start_data_renew(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """启动数据更新并立刻返回。可选 source（表名或 data source key）、force。"""
    args = arguments if isinstance(arguments, dict) else {}
    extra = set(args) - {"source", "force"}
    if extra:
        return {"ok": False, "error": f"不支持的参数: {', '.join(sorted(extra))}"}

    source_raw = args.get("source")
    if source_raw is None:
        source_raw = ""
    if not isinstance(source_raw, str):
        return {"ok": False, "error": "source 须为字符串"}
    force = args.get("force", False)
    if not isinstance(force, bool):
        return {"ok": False, "error": "force 须为布尔"}

    source_key = ""
    text = source_raw.strip()
    if text:
        try:
            source_key = DataSourceManager().resolve_renew_target(text)
        except ValueError as exc:
            return {"ok": False, "error": str(exc).splitlines()[0]}

    running = JobPipeline.get_running_job()
    if running:
        kind = str(running.get("kind") or "unknown")
        return {
            "ok": False,
            "error": f"系统任务进行中（{kind}），请稍后再试",
        }

    global _ACTIVE
    with _LOCK:
        if _ACTIVE and _ACTIVE.get("running"):
            return {"ok": False, "error": "已有数据更新在运行，请稍后再试"}
        job_id = f"data-renew-{uuid.uuid4().hex[:12]}"
        _ACTIVE = {
            "job_id": job_id,
            "source": source_key,
            "force": force,
            "running": True,
            "error": "",
            "message": "",
        }

    thread = threading.Thread(
        target=_worker,
        args=(job_id, source_key, force),
        daemon=True,
        name=f"ntq-renew-{job_id[-6:]}",
    )
    thread.start()
    return {
        "ok": True,
        "job_id": job_id,
        "source": source_key or None,
        "force": force,
        "status": "running",
        "note": (
            "数据更新已启动。完成前不要编造行数或新鲜度；"
            "用 read_renew_progress 查看进度。"
        ),
    }


def read_renew_progress(arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """读 renew UI 进度投影 + 本进程 active 壳状态。"""
    _ = arguments
    try:
        ui = DataSourceManager.read_renew_ui_status()
    except Exception as exc:
        return {"ok": False, "error": f"无法读取 renew 进度: {exc}"}
    with _LOCK:
        active = dict(_ACTIVE or {})
    pipeline = JobPipeline.get_running_job()
    pipeline_renew = bool(
        pipeline and str(pipeline.get("kind") or "") == "data_renew"
    )
    running = bool(active.get("running")) or pipeline_renew
    return {
        "ok": True,
        "running": running,
        "job_id": str(active.get("job_id") or (pipeline or {}).get("job_id") or ""),
        "source": str(active.get("source") or (pipeline or {}).get("resource_key") or ""),
        "force": bool(active.get("force")),
        "error": str(active.get("error") or ""),
        "message": str(active.get("message") or ""),
        "tasks": ui.get("tasks") or [],
        "progress": ui.get("progress") or {},
        "note": "只读进度。不要编造未出现在 tasks/progress 里的数字。",
    }


def _worker(job_id: str, source_key: str, force: bool) -> None:
    lease = JobPipeline.running_lease(
        kind="data_renew",
        job_id=job_id,
        resource_key=source_key or "*",
        label="更新需要更新的数据源" if not source_key else f"更新 {source_key}",
        domains=["data"],
    )
    acquired = False
    try:
        lease.acquire()
        acquired = True
    except JobRunningBusyError as exc:
        _finish(job_id, str(exc))
        return
    try:
        if JobPipeline.is_cancel_requested(job_id):
            _finish(job_id, "用户取消")
            return
        manager = DataSourceManager()
        if source_key:
            manager.renew(table_name=source_key, force=force, progress_id=job_id)
        else:
            keys = manager.sources_needing_renew()
            if not keys:
                _finish(job_id, "", message="没有需要更新的数据源")
                return
            logger.info(
                "agent renew %s sources: %s force=%s",
                len(keys),
                ", ".join(keys),
                force,
            )
            manager.execute(
                sources=tuple(keys), force=force, progress_id=job_id
            )
        _finish(job_id, "")
    except Exception as exc:
        logger.exception("agent data renew failed job_id=%s", job_id)
        _finish(
            job_id,
            str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__,
        )
    finally:
        if acquired:
            lease.release()
        try:
            JobPipeline.notify_job_finished()
        except Exception:
            logger.exception("notify_job_finished after agent renew failed")


def _finish(job_id: str, error: str, message: str = "") -> None:
    with _LOCK:
        active = _ACTIVE
        if not active or active.get("job_id") != job_id:
            return
        active["running"] = False
        active["error"] = error
        active["message"] = message
