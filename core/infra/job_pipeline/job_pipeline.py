"""JobPipeline 门面：只读 + 串行入队 / advance（绞杀期）。"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Callable, Dict, List, Optional

from .contracts import JobStatus, VALID_KINDS
from .core import queue_store
from .core.task_guard_reader import read_running_job

logger = logging.getLogger(__name__)

Handler = Callable[[Dict[str, Any]], Dict[str, Any]]

_HANDLERS: Dict[str, Handler] = {}
_ADVANCE_LOCK = threading.Lock()


class JobPipeline:
    """长任务登记 / 排队 / 进度视图的唯一对外入口。"""

    @staticmethod
    def register_handler(kind: str, handler: Handler) -> None:
        """BFF 启动时注册 kind → 真正开跑的回调（收到 pending job 快照）。"""
        key = str(kind or "").strip()
        if not key:
            raise ValueError("kind required")
        if not callable(handler):
            raise TypeError("handler must be callable")
        _HANDLERS[key] = handler

    @staticmethod
    def get_running_job() -> Optional[Dict[str, Any]]:
        """当前唯一 running 任务；没有则 ``None``。"""
        return read_running_job()

    @staticmethod
    def has_running_job() -> bool:
        return JobPipeline.get_running_job() is not None

    @staticmethod
    def list_jobs() -> List[Dict[str, Any]]:
        """running（0～1）+ pending 队列。"""
        out: List[Dict[str, Any]] = []
        running = read_running_job()
        if running:
            out.append(running)
        for row in queue_store.list_pending():
            snap = {
                "job_id": str(row.get("job_id") or ""),
                "kind": row.get("kind"),
                "resource_key": str(row.get("resource_key") or ""),
                "label": str(row.get("label") or row.get("resource_key") or ""),
                "status": JobStatus.PENDING,
                "domains": list(row.get("domains") or []),
                "started_at": row.get("enqueued_at"),
                "progress": None,
            }
            out.append(snap)
        return out

    @staticmethod
    def get_job(job_id: str) -> Optional[Dict[str, Any]]:
        needle = str(job_id or "").strip()
        if not needle:
            return None
        for job in JobPipeline.list_jobs():
            if str(job.get("job_id") or "") == needle:
                return job
        return None

    @staticmethod
    def enqueue(spec: Dict[str, Any]) -> Dict[str, Any]:
        """只入队，不开跑。成功 ``queued=True``；失败带 ``reason``。"""
        if not isinstance(spec, dict):
            return {"queued": False, "reason": "spec 必须为对象"}
        kind = str(spec.get("kind") or "").strip()
        if kind not in VALID_KINDS:
            return {"queued": False, "reason": f"无效 kind: {kind or '(empty)'}"}
        resource = str(spec.get("resource_key") or "").strip()
        if not resource:
            return {"queued": False, "reason": "resource_key 必填"}
        jid = str(spec.get("job_id") or "").strip() or f"jp-pend-{uuid.uuid4().hex[:12]}"
        label = str(spec.get("label") or "").strip() or f"{kind}:{resource}"
        row = {
            "job_id": jid,
            "kind": kind,
            "resource_key": resource,
            "label": label,
            "domains": list(spec.get("domains") or []),
            "payload": spec.get("payload")
            if isinstance(spec.get("payload"), dict)
            else {},
        }
        result = queue_store.enqueue(row)
        if not result.get("ok"):
            return {
                "queued": False,
                "reason": result.get("reason") or "入队失败",
                "job_id": result.get("job_id") or jid,
            }
        job = result.get("job") or row
        return {
            "queued": True,
            "is_triggered": False,
            "job_id": str(job.get("job_id") or jid),
            "reason": "已加入管道队列，当前任务结束后将自动执行",
            "job": job,
        }

    @staticmethod
    def submit(spec: Dict[str, Any]) -> Dict[str, Any]:
        """空闲则调 handler 开跑；忙则入队。"""
        if not isinstance(spec, dict):
            return {"is_triggered": False, "queued": False, "reason": "spec 必须为对象"}
        kind = str(spec.get("kind") or "").strip()
        if JobPipeline.has_running_job():
            return JobPipeline.enqueue(spec)
        handler = _HANDLERS.get(kind)
        if handler is None:
            return {
                "is_triggered": False,
                "queued": False,
                "reason": f"未注册 handler: {kind or '(empty)'}",
            }
        try:
            return dict(handler(dict(spec)) or {})
        except Exception as exc:  # noqa: BLE001
            logger.exception("JobPipeline.submit handler failed kind=%s", kind)
            return {"is_triggered": False, "queued": False, "reason": str(exc)}

    @staticmethod
    def advance() -> Optional[Dict[str, Any]]:
        """当前无 running 时弹出队头并交给 handler。供 launcher finally 调用。"""
        with _ADVANCE_LOCK:
            if JobPipeline.has_running_job():
                return None
            head = queue_store.pop_next()
            if head is None:
                return None
            kind = str(head.get("kind") or "").strip()
            handler = _HANDLERS.get(kind)
            if handler is None:
                logger.error("JobPipeline.advance: no handler for kind=%s", kind)
                return {
                    "is_triggered": False,
                    "reason": f"未注册 handler: {kind}",
                    "job_id": head.get("job_id"),
                }
            try:
                return dict(handler(dict(head)) or {})
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "JobPipeline.advance handler failed kind=%s job_id=%s",
                    kind,
                    head.get("job_id"),
                )
                return {
                    "is_triggered": False,
                    "reason": str(exc),
                    "job_id": head.get("job_id"),
                }
