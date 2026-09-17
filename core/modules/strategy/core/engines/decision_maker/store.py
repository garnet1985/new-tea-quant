"""决策者会话磁盘：``{vid}/decision/meta.json`` + ``{dm_id}/session.json``。

本文件:
- DecisionStore: 分配自增 id、列出/读写/删除会话；记下 last_session_id；从不覆盖已完成局
  边界: 只管本 version 下的 decision 目录；不读 enum、不跑资金层
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.modules.strategy.core.services.artifacts.io import ArtifactIO

DECISION_DIR = "decision"
META_FILE = "meta.json"
SESSION_FILE = "session.json"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"


def _now() -> str:
    return datetime.now().isoformat()


class DecisionStore:
    """一份 simulation version 下的决策者会话袋。"""

    def __init__(self, version_dir: Union[str, Path]) -> None:
        self.version_dir = Path(version_dir)
        self.root = self.version_dir / DECISION_DIR

    @classmethod
    def at(cls, version_dir: Union[str, Path]) -> "DecisionStore":
        return cls(version_dir)

    def meta_path(self) -> Path:
        return self.root / META_FILE

    def session_dir(self, dm_id: str) -> Path:
        return self.root / str(dm_id).strip()

    def session_path(self, dm_id: str) -> Path:
        return self.session_dir(dm_id) / SESSION_FILE

    def _empty_meta(self) -> Dict[str, Any]:
        return {"next_session_id": 1, "sessions": {}, "last_session_id": ""}

    def _read_meta(self) -> Dict[str, Any]:
        path = self.meta_path()
        if not path.is_file():
            return self._empty_meta()
        try:
            raw = ArtifactIO.read_json(path)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return self._empty_meta()
        if not isinstance(raw, dict):
            return self._empty_meta()
        sessions = raw.get("sessions")
        if not isinstance(sessions, dict):
            sessions = {}
        try:
            nxt = max(int(raw.get("next_session_id") or 1), 1)
        except (TypeError, ValueError):
            nxt = 1
        last = str(raw.get("last_session_id") or "").strip()
        if last and last not in sessions:
            last = ""
        return {
            "next_session_id": nxt,
            "sessions": sessions,
            "last_session_id": last,
        }

    def _write_meta(self, payload: Dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        ArtifactIO.write_json(self.meta_path(), payload)

    def list_index(self) -> List[Dict[str, Any]]:
        """按 dm_id 数字序。"""
        meta = self._read_meta()
        sessions = meta.get("sessions") or {}
        rows: List[Dict[str, Any]] = []
        for key, raw in sessions.items():
            dm_id = str(key).strip()
            entry = dict(raw) if isinstance(raw, dict) else {}
            entry["dm_id"] = dm_id
            rows.append(entry)
        rows.sort(key=lambda row: _id_sort_key(str(row.get("dm_id") or "")))
        return rows

    def unfinished(self) -> List[Dict[str, Any]]:
        return [
            row
            for row in self.list_index()
            if str(row.get("status") or "") == STATUS_IN_PROGRESS
        ]

    def last_session_id(self) -> str:
        return str(self._read_meta().get("last_session_id") or "").strip()

    def mark_last(self, dm_id: str) -> None:
        """记下用户上次打开的局；进本 version 时默认续这里。"""
        vid = str(dm_id or "").strip()
        if not vid:
            return
        meta = self._read_meta()
        if str(meta.get("last_session_id") or "") == vid:
            return
        meta["last_session_id"] = vid
        self._write_meta(meta)

    def get_index(self, dm_id: str) -> Optional[Dict[str, Any]]:
        vid = str(dm_id or "").strip()
        if not vid:
            return None
        meta = self._read_meta()
        raw = (meta.get("sessions") or {}).get(vid)
        if not isinstance(raw, dict):
            return None
        out = dict(raw)
        out["dm_id"] = vid
        return out

    def exists(self, dm_id: str) -> bool:
        return self.session_path(str(dm_id or "").strip()).is_file()

    def allocate_id(self) -> str:
        """新开一局：自增号，不复用已完成 / 未完成 id。"""
        meta = self._read_meta()
        nxt = int(meta.get("next_session_id") or 1)
        dm_id = str(nxt)
        while self.exists(dm_id) or dm_id in (meta.get("sessions") or {}):
            nxt += 1
            dm_id = str(nxt)
        meta["next_session_id"] = nxt + 1
        sessions = dict(meta.get("sessions") or {})
        sessions[dm_id] = {
            "status": STATUS_IN_PROGRESS,
            "current_date": "",
            "updated_at": _now(),
        }
        meta["sessions"] = sessions
        self._write_meta(meta)
        self.session_dir(dm_id).mkdir(parents=True, exist_ok=True)
        return dm_id

    def load_session(self, dm_id: str) -> Dict[str, Any]:
        path = self.session_path(dm_id)
        if not path.is_file():
            raise FileNotFoundError(f"决策者会话不存在: {dm_id}")
        raw = ArtifactIO.read_json(path)
        if not isinstance(raw, dict):
            raise ValueError(f"session.json 损坏: {path}")
        return raw

    def save_session(self, dm_id: str, payload: Dict[str, Any]) -> Path:
        vid = str(dm_id or "").strip()
        body = dict(payload or {})
        body["dm_id"] = vid
        body["updated_at"] = _now()
        path = ArtifactIO.write_json(self.session_path(vid), body)
        self._touch_index(
            vid,
            status=str(body.get("status") or STATUS_IN_PROGRESS),
            current_date=str(body.get("current_date") or ""),
            updated_at=str(body.get("updated_at") or _now()),
        )
        return path

    def _touch_index(
        self,
        dm_id: str,
        *,
        status: str,
        current_date: str,
        updated_at: str,
    ) -> None:
        meta = self._read_meta()
        sessions = dict(meta.get("sessions") or {})
        sessions[dm_id] = {
            "status": status,
            "current_date": current_date,
            "updated_at": updated_at,
        }
        meta["sessions"] = sessions
        meta["last_session_id"] = dm_id
        try:
            nxt = int(meta.get("next_session_id") or 1)
        except (TypeError, ValueError):
            nxt = 1
        try:
            as_int = int(dm_id)
        except (TypeError, ValueError):
            as_int = 0
        if as_int >= nxt:
            meta["next_session_id"] = as_int + 1
        self._write_meta(meta)

    def delete(self, dm_id: str) -> bool:
        vid = str(dm_id or "").strip()
        if not vid:
            return False
        directory = self.session_dir(vid)
        existed = directory.is_dir() or self.exists(vid)
        if directory.is_dir():
            shutil.rmtree(directory, ignore_errors=True)
        meta = self._read_meta()
        sessions = dict(meta.get("sessions") or {})
        sessions.pop(vid, None)
        meta["sessions"] = sessions
        if str(meta.get("last_session_id") or "") == vid:
            meta["last_session_id"] = _latest_session_id(sessions)
        self._write_meta(meta)
        return existed


def _latest_session_id(sessions: Dict[str, Any]) -> str:
    best_id = ""
    best_ts = ""
    for key, raw in (sessions or {}).items():
        entry = raw if isinstance(raw, dict) else {}
        stamp = str(entry.get("updated_at") or "")
        if stamp > best_ts or (stamp == best_ts and str(key) > best_id):
            best_ts = stamp
            best_id = str(key)
    return best_id


def _id_sort_key(dm_id: str) -> tuple:
    try:
        return (0, int(dm_id))
    except (TypeError, ValueError):
        return (1, dm_id)


__all__ = [
    "DECISION_DIR",
    "DecisionStore",
    "META_FILE",
    "SESSION_FILE",
    "STATUS_COMPLETED",
    "STATUS_IN_PROGRESS",
]
