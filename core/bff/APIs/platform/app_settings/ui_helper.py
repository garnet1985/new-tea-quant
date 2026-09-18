"""Global helper 关闭账本：读写 ``userspace/system/config/ui_helper.json``。"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from core.infra.discovery import Discovery
from core.infra.project_context import ProjectContext
from core.bff.shared.file_ops import atomic_write_text

logger = logging.getLogger(__name__)

UI_HELPER_FILENAME = "ui_helper.json"
ALLOWED_SOURCES = frozenset({"ack", "skip"})
HELP_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def _ledger_path() -> Path:
    return ProjectContext.path.get_user_config_root() / UI_HELPER_FILENAME


def _empty_ledger() -> Dict[str, Any]:
    return {"dismissed": {}}


def _parse_help_id(value: Any) -> Optional[str]:
    help_id = str(value or "").strip()
    if not help_id or not HELP_ID_PATTERN.match(help_id):
        return None
    return help_id


def _parse_version(value: Any) -> Optional[int]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        version = int(value)
    except (TypeError, ValueError):
        return None
    if str(value).strip() != str(version) and not isinstance(value, int):
        return None
    if version < 1:
        return None
    return version


def _parse_source(value: Any) -> Optional[str]:
    source = str(value or "").strip().lower()
    if source not in ALLOWED_SOURCES:
        return None
    return source


def _normalize_entry(raw: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    version = _parse_version(raw.get("version"))
    source = _parse_source(raw.get("source"))
    if version is None or source is None:
        return None
    return {
        "version": version,
        "at": str(raw.get("at") or "").strip(),
        "source": source,
    }


def _read_dismissed(raw: Any) -> Dict[str, Dict[str, Any]]:
    if not isinstance(raw, dict):
        return {}
    dismissed: Dict[str, Dict[str, Any]] = {}
    for key, value in raw.items():
        help_id = _parse_help_id(key)
        entry = _normalize_entry(value)
        if help_id is None or entry is None:
            continue
        dismissed[help_id] = entry
    return dismissed


def get_ui_helper() -> Dict[str, Any]:
    """读关闭账本。缺文件或损坏时返回空 ``dismissed``，不抛给 UI。"""
    path = _ledger_path()
    if not path.is_file():
        return _empty_ledger()
    loaded = Discovery.file.load_json(path)
    if not isinstance(loaded, dict):
        return _empty_ledger()
    return {"dismissed": _read_dismissed(loaded.get("dismissed"))}


def save_ui_helper(payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """关闭一份 help。未知 ``helpId`` 原样写入；不对照 FED 目录。"""
    raw_id = payload.get("helpId") if payload.get("helpId") not in (None, "") else payload.get("help_id")
    if raw_id is None or str(raw_id).strip() == "":
        return None, "缺少 helpId"
    help_id = _parse_help_id(raw_id)
    if help_id is None:
        return None, "helpId 须为字母、数字、下划线或连字符"
    if "version" not in payload or payload.get("version") is None:
        return None, "缺少 version"
    version = _parse_version(payload.get("version"))
    if version is None:
        return None, "version 须为正整数"
    if "source" not in payload or payload.get("source") in (None, ""):
        return None, "缺少 source"
    source = _parse_source(payload.get("source"))
    if source is None:
        return None, "source 须为 ack 或 skip"

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    ledger = get_ui_helper()
    ledger["dismissed"][help_id] = {
        "version": version,
        "at": now,
        "source": source,
    }
    path = _ledger_path()
    text = json.dumps(ledger, ensure_ascii=False, indent=2) + "\n"
    atomic_write_text(path, text, encoding="utf-8")
    logger.info("[bff.settings] wrote ui helper dismissal helpId=%s version=%s", help_id, version)
    return ledger, None
