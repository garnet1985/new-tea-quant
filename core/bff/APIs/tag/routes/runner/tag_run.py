"""BFF tag async shell: lock / lease / thread; progress via Tag Facade helpers."""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Dict, Optional

from core.infra.job_pipeline import JobPipeline
from core.infra.job_pipeline.contracts import JobRunningBusyError
from core.modules.tag import Tag

logger = logging.getLogger(__name__)


class TagRunLauncher:
    """UI 异步跑 tag：锁 / lease / 后台线程；计算仍走 ``Tag.execute``。"""

    _LOCK = threading.Lock()
    _JOBS: Dict[str, Dict[str, Any]] = {}
    _ACTIVE_TAG_JOB_ID: Optional[str] = None

    @classmethod
    def trigger(cls, *, tag_key: str) -> Dict[str, Any]:
        """校验后交给 ``JobPipeline.submit``。"""
        key = str(tag_key or "").strip()
        info = Tag.get_tag_info(key) if key else None
        if not key or info is None:
            return {"is_triggered": False, "reason": f"未知 Tag scenario: {tag_key}"}
        if not bool(info.get("is_enabled")):
            return {"is_triggered": False, "reason": "Scenario 未启用"}
        run_key = str(info.get("unique_relative_path") or key)

        return JobPipeline.submit(
            {
                "kind": "tag_run",
                "resource_key": run_key,
                "label": f"Tag: {run_key}",
                "domains": ["data", "tag"],
                "payload": {},
            }
        )

    @classmethod
    def start_now(cls, *, tag_key: str) -> Dict[str, Any]:
        """管道 handler 调用：立刻开跑，不再入队。"""
        key = str(tag_key or "").strip()
        info = Tag.get_tag_info(key) if key else None
        if not key or info is None:
            return {"is_triggered": False, "reason": f"未知 Tag scenario: {tag_key}"}
        if not bool(info.get("is_enabled")):
            return {"is_triggered": False, "reason": "Scenario 未启用"}
        run_key = str(info.get("unique_relative_path") or key)

        with cls._LOCK:
            if cls._has_active_tag_run_locked():
                return {
                    "is_triggered": False,
                    "reason": "已有 Tag 任务在运行中，请稍后重试",
                }
            jid = cls._job_create(tag_key=run_key)
            cls._ACTIVE_TAG_JOB_ID = jid

        Tag.seed_run_progress(run_key, jid)
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
    def get_progress(cls, *, tag_key: str, job_id: str) -> Optional[Dict[str, Any]]:
        return Tag.get_run_progress(tag_key=tag_key, job_id=job_id)

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
            "status": "queued",
            "error": None,
        }
        return jid

    @staticmethod
    def _require_successful_run(result: Optional[Dict[str, Any]]) -> None:
        if not isinstance(result, dict) or not result.get("success"):
            message = ""
            if isinstance(result, dict):
                message = str(result.get("message") or "").strip()
                failed = int(result.get("fail") or 0)
                if not message and failed:
                    message = f"标签计算失败（{failed} 个任务）"
            raise RuntimeError(message or "标签计算未完成")
        if result.get("dry_run"):
            return
        produced = int(result.get("tag_values_count") or 0)
        saved = int(result.get("saved_tag_values") or 0)
        if produced > 0 and saved < produced:
            raise RuntimeError(
                f"标签值未全部落库（计算 {produced} 行，写入 {saved} 行）"
            )

    @classmethod
    def _background_tag_job(cls, job_id: str, tag_key: str) -> None:
        lease = JobPipeline.running_lease(
            kind="tag_run",
            job_id=job_id,
            resource_key=tag_key,
            label=f"Tag: {tag_key}",
            domains=["data", "tag"],
        )
        acquired = False
        try:
            lease.acquire()
            acquired = True
        except JobRunningBusyError as exc:
            err = str(exc)
            Tag.fail_run_progress(tag_key, job_id, err)
            with cls._LOCK:
                row = cls._JOBS.get(job_id)
                if row:
                    row.update({"status": "failed", "error": err})
            cls._clear_active(job_id)
            cls._notify_finished()
            return

        try:
            Tag.mark_run_running(tag_key, job_id)
            if JobPipeline.is_cancel_requested(job_id):
                Tag.fail_run_progress(tag_key, job_id, "用户取消")
                with cls._LOCK:
                    row = cls._JOBS.get(job_id)
                    if row:
                        row.update({"status": "failed", "error": "用户取消"})
                return
            base_cb = Tag.run_progress_callback(tag_key, job_id)

            def _on_progress(*args, **kwargs):
                if JobPipeline.is_cancel_requested(job_id):
                    raise RuntimeError("用户取消")
                if callable(base_cb):
                    return base_cb(*args, **kwargs)
                return None

            result = Tag(is_verbose=False).execute(
                scenario_name=tag_key,
                on_pipeline_progress=_on_progress,
            )
            if JobPipeline.is_cancel_requested(job_id):
                Tag.fail_run_progress(tag_key, job_id, "用户取消")
                with cls._LOCK:
                    row = cls._JOBS.get(job_id)
                    if row:
                        row.update({"status": "failed", "error": "用户取消"})
                return
            cls._require_successful_run(result)
            Tag.complete_run_progress(tag_key, job_id)
            with cls._LOCK:
                row = cls._JOBS.get(job_id)
                if row:
                    row.update({"status": "completed"})
        except Exception as exc:
            logger.exception(
                "Tag UI run failed tag_key=%s job_id=%s", tag_key, job_id
            )
            Tag.fail_run_progress(tag_key, job_id, str(exc))
            with cls._LOCK:
                row = cls._JOBS.get(job_id)
                if row:
                    row.update({"status": "failed", "error": str(exc)})
        finally:
            if acquired:
                lease.release()
            cls._clear_active(job_id)
            cls._notify_finished()

    @classmethod
    def _clear_active(cls, job_id: str) -> None:
        with cls._LOCK:
            if str(cls._ACTIVE_TAG_JOB_ID or "") == job_id:
                cls._ACTIVE_TAG_JOB_ID = None

    @staticmethod
    def _notify_finished() -> None:
        try:
            JobPipeline.notify_job_finished()
        except Exception:
            logger.exception("JobPipeline.notify_job_finished after tag failed")


__all__ = ["TagRunLauncher"]
