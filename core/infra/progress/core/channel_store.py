"""频道化 job 快照落盘（无业务语义）。

路径：``{progress_dir}/{channel}/{file_key}.json``
与树形进度共用 ``NTQ_PROGRESS_DIR`` / userspace ``tmp/progress``。
调用方自定 channel / file_key；本模块不识别 strategy / tag 等业务名。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional

from core.infra.progress.core.paths import resolve_progress_directory


def build_path(channel: str, file_key: str) -> Path:
    ch = str(channel or "").strip()
    key = str(file_key or "").strip()
    if not ch or not key:
        raise ValueError("channel 与 file_key 不能为空")
    if "/" in ch or "\\" in ch or "\x00" in ch:
        raise ValueError("channel 不能含路径分隔符")
    if "\x00" in key or key in {".", ".."} or ".." in Path(key).parts:
        raise ValueError("file_key 无效")
    # file_key 可含 ``/``（如 strategy/tag 业务键），落在 channel 子目录下
    return _directory() / ch / f"{key}.json"


def write(channel: str, file_key: str, payload: Dict[str, Any]) -> Path:
    path = build_path(channel, file_key)
    body = dict(payload or {})
    body["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as tmp:
        tmp.write(json.dumps(body, ensure_ascii=False, indent=2))
        tmp_path = Path(tmp.name)
    os.replace(str(tmp_path), str(path))
    return path


def read(channel: str, file_key: str) -> Optional[Dict[str, Any]]:
    path = build_path(channel, file_key)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def clear(channel: str, file_key: str) -> None:
    path = build_path(channel, file_key)
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


def _directory() -> Path:
    return resolve_progress_directory()


__all__ = ["build_path", "write", "read", "clear"]
