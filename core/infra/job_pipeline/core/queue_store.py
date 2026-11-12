"""串行 pending 队列落盘（userspace/.ntq/runtime/job_pipeline_queue.json）。"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
DEFAULT_MAX_PENDING = 8


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def queue_path() -> Path:
    from core.infra.project_context import ProjectContext

    return (
        ProjectContext.path.get_userspace_ntq_directory()
        / "runtime"
        / "job_pipeline_queue.json"
    )


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


def _read_unlocked(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {"pending": []}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
        return {"pending": []}
    if not isinstance(raw, dict):
        return {"pending": []}
    pending = raw.get("pending")
    if not isinstance(pending, list):
        pending = []
    clean = [row for row in pending if isinstance(row, dict) and row.get("job_id")]
    return {"pending": clean}


def list_pending() -> List[Dict[str, Any]]:
    with _LOCK:
        return list(_read_unlocked(queue_path()).get("pending") or [])


def get_pending(job_id: str) -> Optional[Dict[str, Any]]:
    needle = str(job_id or "").strip()
    if not needle:
        return None
    for row in list_pending():
        if str(row.get("job_id") or "") == needle:
            return dict(row)
    return None


def enqueue(
    row: Dict[str, Any],
    *,
    max_pending: int = DEFAULT_MAX_PENDING,
) -> Dict[str, Any]:
    """追加 pending。满员或同 kind+resource 已在队则返回拒绝结果。"""
    kind = str(row.get("kind") or "").strip()
    resource = str(row.get("resource_key") or "").strip()
    jid = str(row.get("job_id") or "").strip()
    if not kind or not resource or not jid:
        return {"ok": False, "reason": "enqueue 需要 kind / resource_key / job_id"}

    with _LOCK:
        path = queue_path()
        doc = _read_unlocked(path)
        pending: List[Dict[str, Any]] = list(doc.get("pending") or [])
        if len(pending) >= int(max_pending):
            return {
                "ok": False,
                "reason": f"管道队列已满（最多 {max_pending} 条），请稍后再试",
            }
        for old in pending:
            if (
                str(old.get("kind") or "") == kind
                and str(old.get("resource_key") or "") == resource
            ):
                return {
                    "ok": False,
                    "reason": "同类任务已在队列中，请等待执行",
                    "job_id": str(old.get("job_id") or ""),
                }
        entry = dict(row)
        entry["status"] = "pending"
        entry.setdefault("enqueued_at", _iso_now())
        pending.append(entry)
        _atomic_write(path, {"pending": pending})
        return {"ok": True, "job": dict(entry)}


def pop_next() -> Optional[Dict[str, Any]]:
    """取出队头 pending（并写回剩余）。"""
    with _LOCK:
        path = queue_path()
        doc = _read_unlocked(path)
        pending: List[Dict[str, Any]] = list(doc.get("pending") or [])
        if not pending:
            return None
        head = dict(pending[0])
        _atomic_write(path, {"pending": pending[1:]})
        return head


def remove_pending(job_id: str) -> Dict[str, Any]:
    """按 id 删除尚未执行的 pending。找不到则 ``ok=False``。"""
    needle = str(job_id or "").strip()
    if not needle:
        return {"ok": False, "reason": "job_id 无效"}
    with _LOCK:
        path = queue_path()
        doc = _read_unlocked(path)
        pending: List[Dict[str, Any]] = list(doc.get("pending") or [])
        keep: List[Dict[str, Any]] = []
        removed: Optional[Dict[str, Any]] = None
        for row in pending:
            if removed is None and str(row.get("job_id") or "") == needle:
                removed = dict(row)
                continue
            keep.append(row)
        if removed is None:
            return {"ok": False, "reason": "队列中无此任务（可能已开始执行）"}
        _atomic_write(path, {"pending": keep})
        return {"ok": True, "job": removed}
