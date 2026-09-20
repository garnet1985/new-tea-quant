"""Setup Trace events (never affect install outcome)."""

from __future__ import annotations

import re
from typing import Any, Literal, Mapping, Optional

from core.infra.trace.core.services.sanitize_service import TraceSanitizeService

InstallEntry = Literal["ui", "cli"]
AppEntry = Literal["ui", "cli", "devcli"]


def _classify_error(message: str, *, exc: Optional[BaseException] = None) -> str:
    if isinstance(exc, KeyboardInterrupt):
        return "interrupt"
    text = str(message or "")
    lower = text.lower()
    if "conflicting" in lower or "lock" in lower or "already open" in lower:
        return "lock"
    if "只允许存在 1 个" in text or ("zip" in lower and "多个" in text):
        return "multi_zip"
    if "badzipfile" in lower or "is not a zip" in lower:
        return "bad_zip"
    if "未找到 .zip" in text or "未找到任何" in text:
        return "empty_archive"
    if "数据库不可用" in text:
        return "db_unavailable"
    if "部分表导入失败" in text:
        return "table_import"
    if "被中断" in text or "keyboardinterrupt" in lower:
        return "interrupt"
    if "exit=" in lower:
        return "exit_nonzero"
    return "other"


def _failed_tables(message: str) -> list[str]:
    found = re.findall(r"\('([^']+)'", str(message or ""))
    out: list[str] = []
    for name in found:
        token = str(name).strip()
        if token and token not in out and len(token) <= 64:
            out.append(token)
        if len(out) >= 8:
            break
    return out


def _import_progress_hint() -> dict[str, Any]:
    try:
        from core.infra.setup.core.steps.import_data.installer import (
            PROGRESS_FILE,
            default_init_data_dir,
        )

        path = default_init_data_dir() / PROGRESS_FILE
        if not path.is_file():
            return {}
        import json

        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {}
        hint: dict[str, Any] = {}
        in_progress = str(raw.get("in_progress_table") or "").strip()
        if in_progress:
            hint["failed_table"] = in_progress[:64]
        total = raw.get("total_tables")
        if isinstance(total, int) and total >= 0:
            hint["tables_total"] = total
        completed = raw.get("completed_tables")
        if isinstance(completed, dict):
            hint["tables_done"] = sum(1 for value in completed.values() if value == "done")
        return hint
    except Exception:
        return {}


class SetupTrace:
    """Setup / runtime Trace helpers（静态 API，勿实例化）。"""

    @staticmethod
    def ensure_install_id() -> None:
        try:
            from core.infra.trace.core.services.identity_service import TraceIdentityService

            TraceIdentityService.get_or_create()
        except Exception:
            pass

    @staticmethod
    def install_complete(
        *,
        success: bool,
        entry: InstallEntry,
        error_code: Optional[str] = None,
    ) -> None:
        try:
            from core.infra.trace import Trace

            body: dict[str, Any] = {
                "success": bool(success),
                "entry": entry,
            }
            if error_code:
                body["error_code"] = str(error_code)[:128]
            Trace.track_setup("install.complete", body)
        except Exception:
            pass

    @staticmethod
    def install_step_failed(
        *,
        step: str,
        entry: InstallEntry,
        message: str = "",
        exc: Optional[BaseException] = None,
        extra: Optional[Mapping[str, Any]] = None,
    ) -> None:
        try:
            from core.infra.trace import Trace

            step_id = str(step or "").strip()[:64]
            raw_message = str(message or (exc if exc is not None else "") or "")
            body: dict[str, Any] = {
                "step": step_id,
                "entry": entry,
                "error_class": _classify_error(raw_message, exc=exc),
            }
            if exc is not None:
                body["exc_type"] = type(exc).__name__[:64]
            safe = TraceSanitizeService.message_safe(raw_message)
            if safe:
                body["message_safe"] = safe
            tables = _failed_tables(raw_message)
            if tables:
                body["failed_tables"] = tables
            if step_id == "import_data":
                for key, value in _import_progress_hint().items():
                    body.setdefault(key, value)
            if extra:
                for key, value in extra.items():
                    if key in body or value is None:
                        continue
                    body[key] = value
            Trace.track_setup("install.step_failed", body)
        except Exception:
            pass

    @staticmethod
    def app_start(*, entry: AppEntry, command: Optional[str] = None) -> None:
        """Emit ``app.start`` when launcher / cli / devcli is used.

        For CLI, callers may pass ``command`` (e.g. ``cli.py sp --strategy …``)
        and should only call this for strategy/tag run commands.
        """
        try:
            from core.infra.trace import Trace

            body: dict[str, Any] = {"entry": entry}
            text = str(command or "").strip()
            if text:
                body["command"] = text[:256]
            Trace.track("app.start", body)
        except Exception:
            pass


__all__ = ["SetupTrace"]
