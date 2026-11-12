"""后台跑数据源 renew。一次只允许一个长任务。"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Dict, Optional

from core.infra.job_pipeline import JobPipeline
from core.infra.job_pipeline.contracts import JobRunningBusyError

logger = logging.getLogger(__name__)

# 与 job_handlers.DATA_RENEW_ALL_RESOURCE 对齐
_ALL_RESOURCE = "*"


class DataRenewLauncher:
    """UI 一键更新或单源更新。进度由数据源自己的运行目录写出。"""

    _LOCK = threading.Lock()
    _ACTIVE: Optional[Dict[str, Any]] = None

    @classmethod
    def trigger(cls, source: Optional[str] = None) -> Dict[str, Any]:
        """校验后交给 ``JobPipeline.submit``。"""
        raw = str(source or "").strip()
        source_key = ""
        if raw:
            from core.modules.data_source import DataSourceManager

            try:
                source_key = DataSourceManager().resolve_renew_target(raw)
            except ValueError as exc:
                return {"is_triggered": False, "reason": str(exc).splitlines()[0]}

        resource = source_key or _ALL_RESOURCE
        label = (
            "更新需要更新的数据源"
            if not source_key
            else f"更新 {source_key}"
        )
        return JobPipeline.submit(
            {
                "kind": "data_renew",
                "resource_key": resource,
                "label": label,
                "domains": ["data"],
                "payload": {"source": source_key},
            }
        )

    @classmethod
    def start_now(cls, source: Optional[str] = None) -> Dict[str, Any]:
        """管道 handler 调用：立刻开跑，不再入队。"""
        raw = str(source or "").strip()
        source_key = ""
        if raw and raw != _ALL_RESOURCE:
            from core.modules.data_source import DataSourceManager

            try:
                source_key = DataSourceManager().resolve_renew_target(raw)
            except ValueError as exc:
                return {"is_triggered": False, "reason": str(exc).splitlines()[0]}

        with cls._LOCK:
            if cls._running_locked():
                return {"is_triggered": False, "reason": "已有数据更新在运行，请稍后再试"}
            job_id = f"data-renew-{uuid.uuid4().hex[:12]}"
            cls._ACTIVE = {
                "job_id": job_id,
                "source": source_key,
                "running": True,
                "error": "",
                "message": "",
            }

        thread = threading.Thread(
            target=cls._background,
            args=(job_id, source_key),
            daemon=True,
            name=f"data-renew-{job_id[-8:]}",
        )
        thread.start()
        return {
            "is_triggered": True,
            "job_id": job_id,
            "source": source_key,
            "running": True,
        }

    @classmethod
    def status(cls) -> Dict[str, Any]:
        with cls._LOCK:
            active = dict(cls._ACTIVE or {})
        if not active:
            running = JobPipeline.get_running_job()
            if running and str(running.get("kind") or "") == "data_renew":
                return {
                    "running": True,
                    "job_id": str(running.get("job_id") or ""),
                    "source": str(running.get("resource_key") or ""),
                    "error": "",
                    "message": "",
                    "tasks": _public_tasks(),
                    "progress": _public_progress(),
                }
            return {
                "running": False,
                "job_id": "",
                "source": "",
                "error": "",
                "message": "",
                "tasks": _public_tasks(),
                "progress": _public_progress(),
            }
        return {
            "running": bool(active.get("running")),
            "job_id": str(active.get("job_id") or ""),
            "source": str(active.get("source") or ""),
            "error": str(active.get("error") or ""),
            "message": str(active.get("message") or ""),
            "tasks": _public_tasks(),
            "progress": _public_progress(),
        }

    @classmethod
    def _running_locked(cls) -> bool:
        active = cls._ACTIVE
        return bool(active and active.get("running"))

    @classmethod
    def _background(cls, job_id: str, source_key: str) -> None:
        lease = JobPipeline.running_lease(
            kind="data_renew",
            job_id=job_id,
            resource_key=source_key,
            label="更新需要更新的数据源" if not source_key else f"更新 {source_key}",
            domains=["data"],
        )
        acquired = False
        try:
            lease.acquire()
            acquired = True
        except JobRunningBusyError as exc:
            cls._finish(job_id, str(exc))
            cls._notify_finished()
            return
        try:
            if JobPipeline.is_cancel_requested(job_id):
                cls._finish(job_id, "用户取消")
                return
            from core.modules.data_source import DataSourceManager

            manager = DataSourceManager()
            if source_key:
                manager.renew(table_name=source_key, progress_id=job_id)
            else:
                keys = manager.sources_needing_renew()
                if not keys:
                    cls._finish(job_id, "", message="没有需要更新的数据源")
                    return
                logger.info("一键更新 %s 个需要更新的数据源: %s", len(keys), ", ".join(keys))
                manager.execute(sources=tuple(keys), progress_id=job_id)
            cls._finish(job_id, "")
        except Exception as exc:
            logger.exception("data renew failed job_id=%s source=%s", job_id, source_key or "*")
            cls._finish(job_id, str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__)
        finally:
            if acquired:
                lease.release()
            cls._notify_finished()

    @staticmethod
    def _notify_finished() -> None:
        try:
            JobPipeline.notify_job_finished()
        except Exception:
            logger.exception("JobPipeline.notify_job_finished after renew failed")

    @classmethod
    def _finish(cls, job_id: str, error: str, message: str = "") -> None:
        with cls._LOCK:
            active = cls._ACTIVE
            if not active or active.get("job_id") != job_id:
                return
            active["running"] = False
            active["error"] = error
            active["message"] = message


def _public_tasks() -> list:
    """最近一次运行的任务栏，只留界面要用的字段。"""
    from core.modules.data_source.core.service.run_status import read_latest_run_status

    payload = read_latest_run_status()
    raw = payload.get("tasks") if isinstance(payload, dict) else None
    if not isinstance(raw, list):
        return []
    tasks = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        tasks.append(
            {
                "source": str(row.get("source") or ""),
                "status": str(row.get("status") or ""),
                "started_at": row.get("started_at"),
                "total_seconds": row.get("total_seconds"),
                "error": str(row.get("error") or ""),
            }
        )
    return tasks


def _public_progress() -> dict:
    """当前 renew 任务。step 是数据源计数，sub 是正在跑的那一个。"""
    from core.infra.progress import Progress

    snap = Progress.latest("renew")
    if not isinstance(snap, dict):
        return _empty_progress()
    current = _deepest_running(snap)
    leaf = current if current and current.get("id") != snap.get("id") else None
    return {
        "job": str(snap.get("job") or ""),
        "source": str((leaf or {}).get("source") or ""),
        "step": int(snap.get("done") or 0),
        "step_total": int(snap.get("total") or 0),
        "sub": int((leaf or {}).get("done") or 0),
        "sub_total": int((leaf or {}).get("total") or 0),
        "updated_at": int(snap.get("updated_at") or 0),
        "ratio": float(snap.get("ratio") or 0),
        "status": str(snap.get("status") or ""),
        "label": str((leaf or snap).get("label") or ""),
        "detail": str((leaf or {}).get("detail") or ""),
    }


def _empty_progress() -> dict:
    return {
        "job": "",
        "source": "",
        "step": 0,
        "step_total": 0,
        "sub": 0,
        "sub_total": 0,
        "updated_at": 0,
        "ratio": 0,
        "status": "",
        "label": "",
        "detail": "",
    }


def _deepest_running(node: dict) -> Optional[dict]:
    found = node if str(node.get("status") or "") == "running" else None
    for child in node.get("steps") or []:
        if not isinstance(child, dict):
            continue
        deeper = _deepest_running(child)
        if deeper is not None:
            found = deeper
    return found
