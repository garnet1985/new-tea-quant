"""后台跑数据源 renew。一次只允许一个长任务。"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Dict, Optional

from core.infra.task_guard import TaskGuard
from core.infra.task_guard.contracts import TaskLeaseBusyError

logger = logging.getLogger(__name__)


class DataRenewLauncher:
    """UI 一键更新或单源更新。进度由数据源自己的运行目录写出。"""

    _LOCK = threading.Lock()
    _ACTIVE: Optional[Dict[str, Any]] = None

    @classmethod
    def trigger(cls, source: Optional[str] = None) -> Dict[str, Any]:
        raw = str(source or "").strip()
        source_key = ""
        if raw:
            from core.modules.data_source import DataSourceManager

            try:
                source_key = DataSourceManager().resolve_renew_target(raw)
            except ValueError as exc:
                return {"is_triggered": False, "reason": str(exc).splitlines()[0]}

        status = TaskGuard.read_status()
        if status.get("busy"):
            kind = status.get("kind") or "unknown"
            return {
                "is_triggered": False,
                "reason": f"系统任务进行中（{kind}），请稍后再试",
            }

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
            guard = TaskGuard.read_status()
            if guard.get("busy") and guard.get("kind") == "data_renew":
                return {
                    "running": True,
                    "job_id": str(guard.get("job_id") or ""),
                    "source": str(guard.get("resource_key") or ""),
                    "error": "",
                    "message": "",
                    "tasks": _public_tasks(),
                }
            return {
                "running": False,
                "job_id": "",
                "source": "",
                "error": "",
                "message": "",
                "tasks": _public_tasks(),
            }
        return {
            "running": bool(active.get("running")),
            "job_id": str(active.get("job_id") or ""),
            "source": str(active.get("source") or ""),
            "error": str(active.get("error") or ""),
            "message": str(active.get("message") or ""),
            "tasks": _public_tasks(),
        }

    @classmethod
    def _running_locked(cls) -> bool:
        active = cls._ACTIVE
        return bool(active and active.get("running"))

    @classmethod
    def _background(cls, job_id: str, source_key: str) -> None:
        lease = TaskGuard.lease(
            kind="data_renew",
            job_id=job_id,
            resource_key=source_key,
            label="更新需要更新的数据源" if not source_key else f"更新 {source_key}",
            domains=["data"],
        )
        try:
            lease.acquire()
        except TaskLeaseBusyError as exc:
            cls._finish(job_id, str(exc))
            return
        try:
            from core.modules.data_source import DataSourceManager

            manager = DataSourceManager()
            if source_key:
                manager.renew(table_name=source_key)
            else:
                keys = manager.sources_needing_renew()
                if not keys:
                    cls._finish(job_id, "", message="没有需要更新的数据源")
                    return
                logger.info("一键更新 %s 个需要更新的数据源: %s", len(keys), ", ".join(keys))
                manager.execute(sources=tuple(keys))
            cls._finish(job_id, "")
        except Exception as exc:
            logger.exception("data renew failed job_id=%s source=%s", job_id, source_key or "*")
            cls._finish(job_id, str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__)
        finally:
            lease.release()

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
                "progress_done": row.get("progress_done"),
                "progress_total": row.get("progress_total"),
                "progress_saved": row.get("progress_saved"),
                "progress_label": str(row.get("progress_label") or ""),
                "error": str(row.get("error") or ""),
            }
        )
    return tasks
