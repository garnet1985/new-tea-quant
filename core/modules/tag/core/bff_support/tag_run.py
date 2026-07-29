"""Tag async run for UI (T1-02 / T1-03)。

消费者: BFF tag_stack
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Dict, Optional

from core.infra.system_actions.cache_cleanup.pipeline_lease import (
    PipelineLease,
    PipelineLeaseBusyError,
    read_pipeline_status,
)
from core.modules.strategy.core.services.progress import ProgressRecorder
from core.modules.tag.tag import Tag
from core.modules.tag.core.services.discovery import DiscoveryService

logger = logging.getLogger(__name__)


class TagRunLauncher:
    """UI 异步跑 tag：锁 / lease / progress / 后台线程。"""

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
        # 执行入口用路径 id（scenario.name）
        run_key = str(item.id())

        pipeline = read_pipeline_status()
        if pipeline.get("busy"):
            kind = pipeline.get("kind") or "unknown"
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

        cls._seed_progress(run_key, jid)
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
        key = str(tag_key or "").strip()
        jid = str(job_id or "").strip()
        if not key or not jid:
            return None

        disk = ProgressRecorder.for_tag_run(key, jid).get_progress()
        if not isinstance(disk, dict) or not disk:
            return None
        if str(disk.get("tag_key") or "").strip() != key:
            return None

        status = str(disk.get("status") or "").strip().lower()
        phase = str(disk.get("phase") or status).strip().lower()
        err = disk.get("error")

        if status == "failed" or phase == "failed":
            out: Dict[str, Any] = {
                "progress": 100.0,
                "status": "failed",
                "phase": "failed",
                "job_id": jid,
                "run_id": jid,
                "tag_key": key,
                "is_success": False,
            }
            if err:
                out["reason"] = str(err)
            label = disk.get("label")
            if label:
                out["label"] = str(label)
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
            "phase": "completed" if done else (phase or "running"),
            "job_id": jid,
            "run_id": jid,
            "tag_key": key,
        }
        label = disk.get("label")
        if label:
            out["label"] = str(label)
        if done:
            out["is_success"] = bool(disk.get("is_success", True))
        return out

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
    def _seed_progress(cls, tag_key: str, job_id: str) -> None:
        ProgressRecorder.for_tag_run(tag_key, job_id).record(
            {
                "tag_key": tag_key,
                "run_id": job_id,
                "job_id": job_id,
                "phase": "queued",
                "status": "queued",
                "progress_pct": 0,
                "label": "准备中…",
            }
        )

    @classmethod
    def _write_progress(
        cls, tag_key: str, job_id: str, payload: Dict[str, Any]
    ) -> None:
        base = {
            "tag_key": tag_key,
            "run_id": job_id,
            "job_id": job_id,
        }
        base.update(payload)
        ProgressRecorder.for_tag_run(tag_key, job_id).record(base)

    @classmethod
    def _on_progress_factory(cls, tag_key: str, job_id: str):
        def _cb(snapshot: Dict[str, Any]) -> None:
            finished = int(snapshot.get("finished") or 0)
            total = int(snapshot.get("total_jobs") or 0)
            try:
                pct = float(snapshot.get("progress_pct") or 0)
            except (TypeError, ValueError):
                pct = 0.0
            pct = max(0.0, min(99.9, pct))
            label = f"执行计算 {finished}/{total}" if total else "执行计算…"
            cls._write_progress(
                tag_key,
                job_id,
                {
                    "phase": "running",
                    "status": "running",
                    "progress_pct": pct,
                    "label": label,
                },
            )

        return _cb

    @classmethod
    def _background_tag_job(cls, job_id: str, tag_key: str) -> None:
        lease = PipelineLease(
            kind="tag_run",
            job_id=job_id,
            resource_key=tag_key,
            label=f"Tag: {tag_key}",
            domains=["data", "tag"],
        )
        try:
            lease.acquire()
        except PipelineLeaseBusyError as exc:
            err = str(exc)
            cls._write_progress(
                tag_key,
                job_id,
                {
                    "phase": "failed",
                    "status": "failed",
                    "progress_pct": 100,
                    "error": err,
                },
            )
            with cls._LOCK:
                row = cls._JOBS.get(job_id)
                if row:
                    row.update({"status": "failed", "error": err, "progress": 100.0})
            return

        try:
            cls._write_progress(
                tag_key,
                job_id,
                {
                    "phase": "running",
                    "status": "running",
                    "progress_pct": 1,
                    "label": "加载场景…",
                },
            )
            Tag(is_verbose=False).execute(
                scenario_name=tag_key,
                on_pipeline_progress=cls._on_progress_factory(tag_key, job_id),
            )
            cls._write_progress(
                tag_key,
                job_id,
                {
                    "phase": "completed",
                    "status": "completed",
                    "progress_pct": 100,
                    "label": "完成",
                    "is_success": True,
                },
            )
            with cls._LOCK:
                row = cls._JOBS.get(job_id)
                if row:
                    row.update({"status": "completed", "progress": 100.0})
        except Exception as exc:
            logger.exception(
                "Tag UI run failed tag_key=%s job_id=%s", tag_key, job_id
            )
            cls._write_progress(
                tag_key,
                job_id,
                {
                    "phase": "failed",
                    "status": "failed",
                    "progress_pct": 100,
                    "error": str(exc),
                    "is_success": False,
                },
            )
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
