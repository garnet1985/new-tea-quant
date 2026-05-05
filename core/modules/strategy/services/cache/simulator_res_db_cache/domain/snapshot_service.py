#!/usr/bin/env python3
"""Workbench snapshot service (domain). 表列 ``version`` 在含义上就是 ``snapshot_id``（整型）。"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional, Tuple

from ..audit.result_summary_audit import with_initial_write_count
from ..settings import StrategySettingsService
from core.tables.ui_bff.strategy_workbench_snapshot.model import SysStrategyWorkbenchSnapshotModel


def _row_snapshot_id(row: Optional[dict]) -> int:
    if not row:
        return 0
    return int(row.get("snapshot_id") or row.get("version") or 0)


class StrategyWorkbenchSnapshotService:
    """Domain operations for snapshot lifecycle and compare resolution."""

    def __init__(self) -> None:
        self._model = SysStrategyWorkbenchSnapshotModel()

    @staticmethod
    def format_snapshot_id(snapshot_id: int) -> str:
        """用户可见 id，如 v3。"""
        return f"v{int(snapshot_id)}"

    format_version_id = format_snapshot_id

    @staticmethod
    def parse_snapshot_id(snapshot_id: str) -> Optional[int]:
        raw = str(snapshot_id or "").strip().lower()
        if not raw:
            return None
        if raw.startswith("v"):
            raw = raw[1:]
        if not raw.isdigit():
            return None
        return int(raw)

    parse_version_id = parse_snapshot_id

    @staticmethod
    def to_iso_or_empty(value: Any) -> str:
        if value is None:
            return ""
        try:
            if hasattr(value, "isoformat"):
                return value.isoformat()
            return str(value)
        except Exception:
            return ""

    @staticmethod
    def stable_json_hash(value: Any) -> str:
        try:
            canonical = json.dumps(
                value if value is not None else {},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except Exception:
            canonical = "{}"
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def list_versions(self, strategy_name: str, limit: int = 100) -> list[dict]:
        rows = self._model.list_by_strategy(strategy_name, limit=limit)
        versions = []
        for row in rows or []:
            sid = _row_snapshot_id(row)
            if sid <= 0:
                continue
            versions.append(
                {
                    "snapshot_id": sid,
                    "version_id": self.format_snapshot_id(sid),
                    "created_at": self.to_iso_or_empty(row.get("created_at")),
                    "updated_at": self.to_iso_or_empty(row.get("updated_at")),
                }
            )
        return versions

    def list_version_ids(self, strategy_name: str, limit: int = 100) -> list[str]:
        version_ids = []
        for item in self.list_versions(strategy_name, limit=limit):
            vid = str(item.get("version_id") or "").strip()
            if vid:
                version_ids.append(vid)
        return version_ids

    def load_version_detail(self, strategy_name: str, snapshot_id: int) -> Optional[dict]:
        row = self._model.load_by_strategy_snapshot_id(strategy_name, snapshot_id)
        if not row:
            return None
        return {
            "version_id": self.format_snapshot_id(snapshot_id),
            "settings": row.get("settings_snapshot") or {},
            "result_summary": row.get("result_summary") or {},
        }

    def load_latest_settings_snapshot(self, strategy_name: str) -> Optional[dict]:
        rows = self._model.list_by_strategy(strategy_name, limit=1)
        if not rows:
            return None
        row = rows[0]
        settings_snapshot = row.get("settings_snapshot")
        if not isinstance(settings_snapshot, dict) or not settings_snapshot:
            return None
        sid = _row_snapshot_id(row)
        return {
            "settings": settings_snapshot,
            "snapshot_id": sid,
            "version_id": self.format_snapshot_id(sid) if sid > 0 else "",
        }

    def load_result_summary_by_snapshot_id(
        self, strategy_name: str, snapshot_id: int
    ) -> Optional[dict]:
        row = self._model.load_by_strategy_snapshot_id(strategy_name, snapshot_id)
        if not row:
            return None
        summary = row.get("result_summary")
        return summary if isinstance(summary, dict) else {}

    def load_result_summary_by_version(self, strategy_name: str, version: int) -> Optional[dict]:
        """兼容旧名：参数 ``version`` 即数据库 ``version`` 列 / ``snapshot_id``。"""
        return self.load_result_summary_by_snapshot_id(strategy_name, int(version))

    def load_latest_result_summary(self, strategy_name: str) -> Optional[dict]:
        rows = self._model.list_by_strategy(strategy_name, limit=1)
        if not rows:
            return None
        summary = rows[0].get("result_summary")
        return summary if isinstance(summary, dict) else {}

    def save_or_merge_settings_snapshot(self, strategy_name: str, settings_api: Dict[str, Any]) -> dict:
        target_hash = self.stable_json_hash(settings_api)
        rows = self._model.list_by_strategy(strategy_name, limit=200)
        for row in rows or []:
            snap = row.get("settings_snapshot") if isinstance(row.get("settings_snapshot"), dict) else None
            if not isinstance(snap, dict):
                continue
            if self.stable_json_hash(snap) != target_hash:
                continue
            existing = _row_snapshot_id(row)
            if existing > 0:
                return {"saved": True, "merged": True, "snapshot_id": existing}
        created = self._model.create_snapshot(
            strategy_name=strategy_name,
            settings_snapshot=settings_api,
            result_summary=with_initial_write_count({}),
        )
        sid = int(created.get("snapshot_id") or 0)
        return {"saved": True, "merged": False, "snapshot_id": sid}

    def create_snapshot_from_api_settings(self, strategy_name: str, settings_api: Dict[str, Any]) -> int:
        created = self._model.create_snapshot(
            strategy_name=strategy_name,
            settings_snapshot=settings_api,
            result_summary=with_initial_write_count({}),
        )
        return int(created.get("snapshot_id") or 0)

    def create_version_from_api_settings(self, strategy_name: str, settings_api: Dict[str, Any]) -> int:
        """兼容旧名。"""
        return self.create_snapshot_from_api_settings(strategy_name, settings_api)

    def resolve_compare_snapshot(
        self, strategy_name: str, compare_version: str
    ) -> Tuple[Optional[dict], str, Optional[str]]:
        raw = str(compare_version or "").strip().lower()
        if not raw:
            return None, "compare_version 不能为空", None
        if raw == "latest":
            rows = self._model.list_by_strategy(strategy_name, limit=1)
            if not rows:
                return None, f"对比版本不存在: {compare_version}", None
            row = rows[0]
            sid = _row_snapshot_id(row)
            if sid <= 0:
                return None, f"对比版本不存在: {compare_version}", None
            return row, "", self.format_snapshot_id(sid)
        sid = self.parse_snapshot_id(compare_version)
        if sid is None:
            return None, f"compare_version 无效: {compare_version}", None
        row = self._model.load_by_strategy_snapshot_id(strategy_name, sid)
        if not row:
            return None, f"对比版本不存在: {compare_version}", None
        return row, "", self.format_snapshot_id(sid)

    def restore_version(self, strategy_name: str, version_id: str) -> dict:
        sid = self.parse_snapshot_id(version_id)
        if sid is None:
            return {
                "ok": False,
                "reason": "invalid_version_id",
                "source_snapshot_id": None,
                "new_snapshot_id": 0,
            }
        row = self._model.load_by_strategy_snapshot_id(strategy_name, sid)
        if not row:
            return {
                "ok": False,
                "reason": "version_not_found",
                "source_snapshot_id": sid,
                "new_snapshot_id": 0,
            }
        settings_snapshot = row.get("settings_snapshot") or {}
        normalized, _ = StrategySettingsService.normalize_runtime_settings(
            strategy_name=strategy_name,
            api_settings=settings_snapshot,
        )
        if normalized is None:
            return {
                "ok": False,
                "reason": "invalid_snapshot_settings",
                "source_snapshot_id": sid,
                "new_snapshot_id": 0,
            }
        api_settings = StrategySettingsService.runtime_to_api(normalized)
        new_sid = self.create_snapshot_from_api_settings(strategy_name, api_settings)
        if new_sid <= 0:
            return {
                "ok": False,
                "reason": "create_failed",
                "source_snapshot_id": sid,
                "new_snapshot_id": 0,
            }
        return {
            "ok": True,
            "reason": "",
            "source_snapshot_id": sid,
            "new_snapshot_id": new_sid,
        }


__all__ = ["StrategyWorkbenchSnapshotService"]
