"""BFF tag async shell: lock / lease / thread; progress via ``TagRunProgress``."""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Dict, Optional

from core.infra.task_guard import TaskGuard
from core.infra.task_guard.contracts import TaskLeaseBusyError
from core.modules.tag.core.services.discovery import DiscoveryService
from core.modules.tag.core.services.progress import TagRunProgress
from core.modules.tag import Tag

logger = logging.getLogger(__name__)


class TagRunLauncher:
    """UI 异步跑 tag：锁 / lease / 后台线程；进度落盘在 TagRunProgress。"""

    _LOCK = threading.Lock()
    _JOBS: Dict[str, Dict[str, Any]] = {}
    _ACTIVE_TAG_JOB_ID: Optional[str] = None

    @classmethod
    def trigger(cls, *, tag_key: str) -> Dict[str, Any]:
        key = str(tag_key or "").strip()
        item = cls._find_info(key) if key else None
        if not key or item is None:
            return {"is_triggered": False, "reason": f"未知 Tag scenario: {tag_key}"}
        settings = item.settings if isinstance(item.settings, dict) else {}
        if not bool(settings.get("is_enabled")):
            return {"is_triggered": False, "reason": "Scenario 未启用"}
        run_key = str(item.id())

        status = TaskGuard.read_status()
        if status.get("busy"):
            kind = status.get("kind") or "unknown"
            return {
                "is_triggered": False,
                "reason": f"系统任务进行中（{kind}），请稍后再试",
            }

        with cls._LOCK:
            if cls._has_active_tag_run_locked():
                return {
                    "is_triggered": False,
                    "reason": "已有 Tag 任务在运行中，请稍后重试",
                }
            jid = cls._job_create(tag_key=run_key)
            cls._ACTIVE_TAG_JOB_ID = jid

        TagRunProgress.for_job(run_key, jid).seed()
        thread = threading.Thread(
            target=cls._background_tag_job,
            args=(jid, run_key),
            daemon=True,
            name=f"tag-run-{jid[:8]}",
        )
        thread.start()
        return {
            "is_triggered": True,
            "job_id": jid,
            "run_id": jid,
            "tag_key": run_key,
            "name": run_key,
        }

    @classmethod
    def _find_info(cls, key_or_id: str):
        needle = str(key_or_id or "").strip()
        if not needle:
            return None
        for info in DiscoveryService.discover_tags():
            if info.key == needle or info.id() == needle:
                return info
        return None

    @classmethod
    def get_progress(cls, *, tag_key: str, job_id: str) -> Optional[Dict[str, Any]]:
        return TagRunProgress.get_poll_dto(tag_key=tag_key, job_id=job_id)

    @classmethod
    def _has_active_tag_run_locked(cls) -> bool:
        jid = str(cls._ACTIVE_TAG_JOB_ID or "").strip()
        if not jid:
            return False
        row = cls._JOBS.get(jid)
        if not isinstance(row, dict):
            cls._ACTIVE_TAG_JOB_ID = None
            return False
        st = str(row.get("status") or "").strip().lower()
        if st in ("completed", "failed"):
            cls._ACTIVE_TAG_JOB_ID = None
            return False
        return True

    @classmethod
    def _job_create(cls, *, tag_key: str) -> str:
        jid = f"tag-run-{uuid.uuid4().hex[:12]}"
        cls._JOBS[jid] = {
            "tag_key": tag_key,
            "progress": 0.0,
            "status": "queued",
            "error": None,
        }
        return jid

    @classmethod
    def _background_tag_job(cls, job_id: str, tag_key: str) -> None:
        prog = TagRunProgress.for_job(tag_key, job_id)
        lease = TaskGuard.lease(
            kind="tag_run",
            job_id=job_id,
            resource_key=tag_key,
            label=f"Tag: {tag_key}",
            domains=["data", "tag"],
        )
        try:
            lease.acquire()
        except TaskLeaseBusyError as exc:
            err = str(exc)
            prog.fail(err)
            with cls._LOCK:
                row = cls._JOBS.get(job_id)
                if row:
                    row.update({"status": "failed", "error": err, "progress": 100.0})
            return

        try:
            prog.mark_running()
            Tag(is_verbose=False).execute(
                scenario_name=tag_key,
                on_pipeline_progress=prog.on_progress_callback(),
            )
            prog.complete()
            with cls._LOCK:
                row = cls._JOBS.get(job_id)
                if row:
                    row.update({"status": "completed", "progress": 100.0})
        except Exception as exc:
            logger.exception(
                "Tag UI run failed tag_key=%s job_id=%s", tag_key, job_id
            )
            prog.fail(str(exc))
            with cls._LOCK:
                row = cls._JOBS.get(job_id)
                if row:
                    row.update(
                        {"status": "failed", "error": str(exc), "progress": 100.0}
                    )
        finally:
            lease.release()
            with cls._LOCK:
                if str(cls._ACTIVE_TAG_JOB_ID or "") == job_id:
                    cls._ACTIVE_TAG_JOB_ID = None


__all__ = ["TagRunLauncher"]
