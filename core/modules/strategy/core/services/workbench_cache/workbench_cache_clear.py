"""Workbench simulation cache clear (domain service).

Deletes rows in ``sys_strategy_workbench_snapshot`` only (not disk simulation dirs).
Consumers: BFF support + ``temp_cleanup`` (must not depend on ``core.bff``).
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from core.modules.data_manager import DataManager

logger = logging.getLogger(__name__)


class WorkbenchCacheClear:
    """Clear workbench snapshot DB cache (all / by version)."""

    @classmethod
    def clear_all(cls) -> Dict[str, Any]:
        model = cls._snapshot_model()
        if model is None:
            return {"ok": False, "error": "存储不可用", "deleted_count": 0}
        try:
            model._ensure_table_ready()
            deleted = int(model.delete_all() or 0)
        except Exception as exc:
            logger.exception("clear_all workbench snapshot cache failed")
            return {"ok": False, "error": str(exc) or "清理失败", "deleted_count": 0}
        return {"ok": True, "deleted_count": deleted, "cleared": deleted >= 0}

    @classmethod
    def clear_by_version(cls, strategy_name: str, version: int) -> Dict[str, Any]:
        name = str(strategy_name or "").strip()
        sid = int(version)
        if not name or sid <= 0:
            return {"ok": False, "error": "参数无效", "deleted": False}

        model = cls._snapshot_model()
        if model is None:
            return {"ok": False, "error": "存储不可用", "deleted": False}

        try:
            model._ensure_table_ready()
            row = model.load_by_strategy_version(name, sid)
            if not row:
                return {
                    "ok": False,
                    "error": "快照不存在",
                    "deleted": False,
                    "strategy_name": name,
                    "version": sid,
                }
            n = int(model.delete_version_row(name, sid) or 0)
        except Exception as exc:
            logger.exception(
                "clear_by_version failed strategy=%s version=%s", name, sid
            )
            return {"ok": False, "error": str(exc) or "删除失败", "deleted": False}

        if n <= 0:
            return {
                "ok": False,
                "error": "快照不存在",
                "deleted": False,
                "strategy_name": name,
                "version": sid,
            }
        return {
            "ok": True,
            "deleted": True,
            "strategy_name": name,
            "version_id": f"v{sid}",
        }

    @staticmethod
    def _snapshot_model():
        try:
            return DataManager().get_table("sys_strategy_workbench_snapshot")
        except Exception:
            logger.exception("Failed to resolve workbench snapshot table")
            return None


__all__ = ["WorkbenchCacheClear"]
