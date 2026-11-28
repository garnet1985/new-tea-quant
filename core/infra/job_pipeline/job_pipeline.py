"""JobPipeline 门面：只读任务表 + 串行入队 / running 槽 / advance。"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Callable, Dict, List, Optional

from .contracts import JobStatus, VALID_KINDS
from .core import liveness
from .core import queue_store
from .core import progress_view
from .core import registry_store
from .core.progress_view import ImportProgressReader
from .core.running_lease import RunningLease
from .core.running_reader import read_running_job

logger = logging.getLogger(__name__)

Handler = Callable[[Dict[str, Any]], Dict[str, Any]]

_HANDLERS: Dict[str, Handler] = {}
_ADVANCE_LOCK = threading.Lock()


class JobPipeline:
    """长任务登记 / 排队 / 进度视图的唯一对外入口。"""

    @staticmethod
    def set_import_progress_reader(reader: Optional[ImportProgressReader]) -> None:
        """注入 ``import_data`` 进度读函数（避免本模块硬依赖 ``infra.setup``）。"""
        progress_view.set_import_progress_reader(reader)

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
        """当前唯一 running 任务；没有则 ``None``。无心跳过久时 ``status=stale``。"""
        return liveness.annotate_stale(progress_view.attach_progress(read_running_job()))

    @staticmethod
    def has_running_job() -> bool:
        return read_running_job() is not None

    @staticmethod
    def recover() -> Dict[str, Any]:
        """清掉死 pid 占槽并泵队列。读面轮询时可调用。"""
        cleared = registry_store.clear_dead_holder()
        if not cleared:
            return {"recovered": False}
        JobPipeline.notify_job_finished()
        return {
            "recovered": True,
            "reason": "dead_pid",
            "cleared_job_id": cleared.get("job_id"),
            "cleared_kind": cleared.get("kind"),
        }

    @staticmethod
    def abandon(job_id: str) -> Dict[str, Any]:
        """强制释放当前 running（僵死任务），并泵下一条。"""
        needle = str(job_id or "").strip()
        if not needle:
            return {"abandoned": False, "reason": "job_id 无效"}
        running = read_running_job()
        if not running or str(running.get("job_id") or "") != needle:
            return {"abandoned": False, "reason": "任务不在运行或不匹配", "job_id": needle}
        released = registry_store.release_running(needle)
        if not released:
            return {"abandoned": False, "reason": "释放 running 槽失败", "job_id": needle}
        try:
            from core.infra.progress import Progress

            Progress.fail(needle, detail="用户放弃僵死任务")
        except Exception:
            logger.debug("Progress.fail skipped for abandoned job_id=%s", needle, exc_info=True)
        JobPipeline.notify_job_finished()
        return {
            "abandoned": True,
            "job_id": needle,
            "reason": "已放弃该任务并释放管道",
            "job": running,
        }

    @staticmethod
    def running_lease(
        *,
        kind: str,
        job_id: str,
        resource_key: str = "",
        label: str = "",
        domains: Optional[list] = None,
    ) -> RunningLease:
        """占用全局 running 槽（filelock + 自管表）。"""
        return RunningLease(
            kind=kind,
            job_id=job_id,
            resource_key=resource_key,
            label=label,
            domains=domains,
        )

    @staticmethod
    def list_jobs() -> List[Dict[str, Any]]:
        """running（0～1）+ pending 队列。"""
        out: List[Dict[str, Any]] = []
        running = JobPipeline.get_running_job()
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
                "cancel_requested": False,
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
    def cancel(job_id: str) -> Dict[str, Any]:
        """取消 pending，或对 running 发出协作取消请求。"""
        needle = str(job_id or "").strip()
        if not needle:
            return {"cancelled": False, "reason": "job_id 无效"}
        running = read_running_job()
        if running and str(running.get("job_id") or "") == needle:
            if running.get("cancel_requested"):
                return {
                    "cancelled": True,
                    "cancel_requested": True,
                    "job_id": needle,
                    "reason": "已在取消中，等待任务退出",
                    "job": progress_view.attach_progress(running),
                }
            marked = registry_store.request_cancel(needle)
            if not marked.get("ok"):
                return {
                    "cancelled": False,
                    "reason": marked.get("reason") or "无法请求取消",
                    "job_id": needle,
                }
            try:
                from core.infra.progress import Progress

                Progress.cancel(needle, detail="用户取消")
            except Exception:
                logger.debug("Progress.cancel skipped for job_id=%s", needle, exc_info=True)
            return {
                "cancelled": True,
                "cancel_requested": True,
                "job_id": needle,
                "reason": "已请求取消，等待任务协作退出",
                "job": progress_view.attach_progress(marked.get("job") or running),
            }
        result = queue_store.remove_pending(needle)
        if not result.get("ok"):
            return {
                "cancelled": False,
                "reason": result.get("reason") or "取消失败",
                "job_id": needle,
            }
        return {
            "cancelled": True,
            "job_id": needle,
            "job": result.get("job"),
        }

    @staticmethod
    def is_cancel_requested(job_id: str) -> bool:
        """后台线程轮询：用户是否请求取消该 running。"""
        return registry_store.is_cancel_requested(job_id)

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

    @staticmethod
    def notify_job_finished() -> None:
        """launcher finally 调用：尝试泵下一条；失败只打日志。"""
        try:
            JobPipeline.advance()
        except Exception:
            logger.exception("JobPipeline.notify_job_finished / advance failed")
