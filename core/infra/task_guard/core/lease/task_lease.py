"""Global long-running task lease (single active job)."""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional

from core.infra.project_context import ProjectContext
from core.infra.task_guard.contracts import VALID_KINDS, TaskLeaseBusyError

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()


class TaskLease:
    """Context manager: acquire on enter, release on exit."""

    @staticmethod
    def lease_path() -> Path:
        return (
            ProjectContext.path.get_userspace_ntq_directory()
            / "runtime"
            / "task_guard_active.json"
        )

    @staticmethod
    def _iso_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _atomic_write(path: Path, payload: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as tmp:
            tmp.write(json.dumps(payload, ensure_ascii=False, indent=2))
            tmp_path = Path(tmp.name)
        os.replace(str(tmp_path), str(path))

    @staticmethod
    def read_status() -> Dict[str, Any]:
        """返回空闲或仍由存活进程持有的租约。进程已退出的锁会被删掉。"""
        with _LOCK:
            raw = TaskLease._live_lease(TaskLease.lease_path())
            if raw is None:
                return TaskLease._idle_message()
            return {
                "busy": True,
                "kind": raw.get("kind"),
                "job_id": raw.get("job_id"),
                "resource_key": raw.get("resource_key"),
                "label": raw.get("label"),
                "domains": list(raw.get("domains") or []),
                "started_at": raw.get("started_at"),
            }

    @staticmethod
    def _holder_alive(payload: Dict[str, Any]) -> bool:
        """租约里的 pid 仍在运行。没有 pid 的旧文件视为已失效。"""
        try:
            pid = int(payload.get("pid"))
        except (TypeError, ValueError):
            return False
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    @staticmethod
    def _live_lease(path: Path) -> Optional[Dict[str, Any]]:
        """读租约文件。持有进程已退出时删除文件并返回空。"""
        if not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
            return None
        if not isinstance(raw, dict) or not raw.get("job_id"):
            return None
        if TaskLease._holder_alive(raw):
            return raw
        logger.warning(
            "丢弃过期任务锁 kind=%s job_id=%s pid=%s",
            raw.get("kind"),
            raw.get("job_id"),
            raw.get("pid"),
        )
        path.unlink(missing_ok=True)
        return None

    @staticmethod
    def _idle_message() -> Dict[str, Any]:
        return {
            "busy": False,
            "kind": None,
            "job_id": None,
            "resource_key": None,
            "label": None,
            "domains": [],
            "started_at": None,
        }

    def __init__(
        self,
        *,
        kind: str,
        job_id: str,
        resource_key: str = "",
        label: str = "",
        domains: Optional[List[str]] = None,
    ) -> None:
        self.kind = str(kind or "").strip()
        self.job_id = str(job_id or "").strip()
        self.resource_key = str(resource_key or "").strip()
        self.label = str(label or "").strip()
        self.domains = list(domains or [])
        self._held = False

    def acquire(self) -> None:
        if self.kind not in VALID_KINDS:
            raise ValueError(f"invalid task kind: {self.kind!r}")
        if not self.job_id:
            raise ValueError("job_id required for task lease")

        with _LOCK:
            path = TaskLease.lease_path()
            existing = TaskLease._live_lease(path)
            if existing is not None:
                raise TaskLeaseBusyError(existing)

            payload = {
                "kind": self.kind,
                "job_id": self.job_id,
                "resource_key": self.resource_key,
                "label": self.label or self.resource_key or self.kind,
                "domains": self.domains,
                "pid": os.getpid(),
                "started_at": TaskLease._iso_now(),
            }
            TaskLease._atomic_write(path, payload)
            self._held = True

    def release(self) -> None:
        with _LOCK:
            path = TaskLease.lease_path()
            if not self._held:
                return
            if path.is_file():
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
                    raw = {}
                if isinstance(raw, dict) and str(raw.get("job_id") or "") == self.job_id:
                    path.unlink(missing_ok=True)
            self._held = False

    def __enter__(self) -> "TaskLease":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
