"""自管 running 槽：filelock 跨进程互斥 + 任务快照落盘。"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional

from filelock import FileLock, Timeout

from core.infra.job_pipeline.contracts import JobRunningBusyError, JobStatus, VALID_KINDS
from core.infra.job_pipeline.core.pipeline_constants import FILE_LOCK_TIMEOUT_SEC

logger = logging.getLogger(__name__)

_THREAD_LOCK = threading.Lock()


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _runtime_dir() -> Path:
    from core.infra.project_context import ProjectContext

    return ProjectContext.path.get_userspace_ntq_directory() / "runtime"


def registry_path() -> Path:
    return _runtime_dir() / "job_pipeline_running.json"


def registry_lock_path() -> Path:
    return _runtime_dir() / "job_pipeline_running.lock"


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


def _holder_alive(payload: Dict[str, Any]) -> bool:
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


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return None
    return raw if isinstance(raw, dict) else None


def _live_payload(path: Path) -> Optional[Dict[str, Any]]:
    raw = _read_json(path)
    if not raw or not str(raw.get("job_id") or "").strip():
        return None
    if _holder_alive(raw):
        return raw
    logger.warning(
        "丢弃过期 running 槽 kind=%s job_id=%s pid=%s",
        raw.get("kind"),
        raw.get("job_id"),
        raw.get("pid"),
    )
    path.unlink(missing_ok=True)
    return None


def clear_dead_holder() -> Optional[Dict[str, Any]]:
    """若 running 槽 pid 已死则删除；返回被清掉的快照，否则 ``None``。"""
    with _THREAD_LOCK:
        try:
            lock = FileLock(str(registry_lock_path()), timeout=FILE_LOCK_TIMEOUT_SEC)
            with lock:
                path = registry_path()
                raw = _read_json(path)
                if not raw or not str(raw.get("job_id") or "").strip():
                    return None
                if _holder_alive(raw):
                    return None
                snap = _to_public_snapshot(raw)
                logger.warning(
                    "clear_dead_holder kind=%s job_id=%s pid=%s",
                    raw.get("kind"),
                    raw.get("job_id"),
                    raw.get("pid"),
                )
                path.unlink(missing_ok=True)
                return snap
        except Timeout:
            logger.warning("registry_store.clear_dead_holder: filelock timeout")
            return None


def _to_public_snapshot(raw: Dict[str, Any]) -> Dict[str, Any]:
    domains = raw.get("domains")
    if not isinstance(domains, list):
        domains = []
    return {
        "job_id": str(raw.get("job_id") or ""),
        "kind": raw.get("kind"),
        "resource_key": str(raw.get("resource_key") or ""),
        "label": str(raw.get("label") or raw.get("resource_key") or raw.get("kind") or ""),
        "status": JobStatus.RUNNING,
        "domains": [str(d) for d in domains],
        "started_at": raw.get("started_at"),
        "progress": None,
        "pid": raw.get("pid"),
        "cancel_requested": bool(raw.get("cancel_requested")),
    }


def read_running() -> Optional[Dict[str, Any]]:
    """读自管 running 槽。"""
    with _THREAD_LOCK:
        try:
            lock = FileLock(str(registry_lock_path()), timeout=FILE_LOCK_TIMEOUT_SEC)
            with lock:
                live = _live_payload(registry_path())
                return _to_public_snapshot(live) if live is not None else None
        except Timeout:
            logger.warning("registry_store.read_running: filelock timeout")
            live = _live_payload(registry_path())
            return _to_public_snapshot(live) if live is not None else None


def acquire_running(row: Dict[str, Any]) -> Dict[str, Any]:
    """占用全局 running 槽。忙则抛 ``JobRunningBusyError``。"""
    kind = str(row.get("kind") or "").strip()
    jid = str(row.get("job_id") or "").strip()
    if kind not in VALID_KINDS:
        raise ValueError(f"invalid job kind: {kind!r}")
    if not jid:
        raise ValueError("job_id required")

    payload = {
        "kind": kind,
        "job_id": jid,
        "resource_key": str(row.get("resource_key") or "").strip(),
        "label": str(row.get("label") or "").strip()
        or str(row.get("resource_key") or "").strip()
        or kind,
        "domains": list(row.get("domains") or []),
        "pid": os.getpid(),
        "started_at": _iso_now(),
    }

    with _THREAD_LOCK:
        try:
            lock = FileLock(str(registry_lock_path()), timeout=FILE_LOCK_TIMEOUT_SEC)
            with lock:
                existing = _live_payload(registry_path())
                if existing is not None:
                    raise JobRunningBusyError(_to_public_snapshot(existing))
                _atomic_write(registry_path(), payload)
                return _to_public_snapshot(payload)
        except Timeout as exc:
            raise JobRunningBusyError({"kind": kind, "job_id": jid}) from exc


def release_running(job_id: str) -> bool:
    """释放 running 槽（仅当 job_id 匹配）。"""
    needle = str(job_id or "").strip()
    if not needle:
        return False

    with _THREAD_LOCK:
        try:
            lock = FileLock(str(registry_lock_path()), timeout=FILE_LOCK_TIMEOUT_SEC)
            with lock:
                path = registry_path()
                raw = _read_json(path)
                if not raw or str(raw.get("job_id") or "") != needle:
                    return False
                path.unlink(missing_ok=True)
                return True
        except Timeout:
            logger.warning("registry_store.release_running: filelock timeout job_id=%s", needle)
            return False


def request_cancel(job_id: str) -> Dict[str, Any]:
    """给当前 running 打上 ``cancel_requested``；非当前 running 则失败。"""
    needle = str(job_id or "").strip()
    if not needle:
        return {"ok": False, "reason": "job_id 无效"}

    with _THREAD_LOCK:
        try:
            lock = FileLock(str(registry_lock_path()), timeout=FILE_LOCK_TIMEOUT_SEC)
            with lock:
                path = registry_path()
                live = _live_payload(path)
                if live is None or str(live.get("job_id") or "") != needle:
                    return {"ok": False, "reason": "任务不在运行或不匹配"}
                live["cancel_requested"] = True
                _atomic_write(path, live)
                return {"ok": True, "job": _to_public_snapshot(live)}
        except Timeout:
            return {"ok": False, "reason": "取消请求超时，请重试"}


def is_cancel_requested(job_id: str) -> bool:
    needle = str(job_id or "").strip()
    if not needle:
        return False
    raw = _read_json(registry_path())
    if isinstance(raw, dict) and str(raw.get("job_id") or "") == needle:
        return bool(raw.get("cancel_requested"))
    return False
