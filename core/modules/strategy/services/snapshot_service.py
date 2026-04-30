#!/usr/bin/env python3
"""Workbench snapshot/version service (domain-side)."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional, Tuple

from core.tables.ui_bff.strategy_workbench_snapshot.model import SysStrategyWorkbenchSnapshotModel

from .settings_service import StrategySettingsService


class StrategyWorkbenchSnapshotService:
    """Domain operations for snapshot lifecycle and compare resolution."""

    def __init__(self) -> None:
        self._model = SysStrategyWorkbenchSnapshotModel()

    @staticmethod
    def format_version_id(version: int) -> str:
        return f"v{int(version)}"

    @staticmethod
    def parse_version_id(version_id: str) -> Optional[int]:
        raw = str(version_id or "").strip().lower()
        if not raw:
            return None
        if raw.startswith("v"):
            raw = raw[1:]
        if not raw.isdigit():
            return None
        return int(raw)

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
            v = int(row.get("version") or 0)
            if v <= 0:
                continue
            versions.append(
                {
                    "version_id": self.format_version_id(v),
                    "version": v,
                    "created_at": self.to_iso_or_empty(row.get("created_at")),
                    "updated_at": self.to_iso_or_empty(row.get("updated_at")),
                }
            )
        return versions

    def list_version_ids(self, strategy_name: str, limit: int = 100) -> list[str]:
        version_ids = []
        for item in self.list_versions(strategy_name, limit=limit):
            version_id = str(item.get("version_id") or "").strip()
            if version_id:
                version_ids.append(version_id)
        return version_ids

    def load_version_detail(self, strategy_name: str, version: int) -> Optional[dict]:
        row = self._model.load_by_strategy_version(strategy_name, version)
        if not row:
            return None
        return {
            "version_id": self.format_version_id(version),
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
        v = int(row.get("version") or 0)
        return {
            "settings": settings_snapshot,
            "version": v,
            "version_id": self.format_version_id(v) if v > 0 else "",
        }

    def load_result_summary_by_version(self, strategy_name: str, version: int) -> Optional[dict]:
        row = self._model.load_by_strategy_version(strategy_name, version)
        if not row:
            return None
        summary = row.get("result_summary")
        return summary if isinstance(summary, dict) else {}

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
            existing_v = int(row.get("version") or 0)
            if existing_v > 0:
                return {"saved": True, "merged": True, "version": existing_v}
        created = self._model.create_version(
            strategy_name=strategy_name,
            settings_snapshot=settings_api,
            result_summary={},
        )
        return {"saved": True, "merged": False, "version": int(created.get("version") or 0)}

    def create_version_from_api_settings(self, strategy_name: str, settings_api: Dict[str, Any]) -> int:
        created = self._model.create_version(
            strategy_name=strategy_name,
            settings_snapshot=settings_api,
            result_summary={},
        )
        return int(created.get("version") or 0)

    def resolve_compare_snapshot(self, strategy_name: str, compare_version: str) -> Tuple[Optional[dict], str, Optional[str]]:
        raw = str(compare_version or "").strip().lower()
        if not raw:
            return None, "compare_version 不能为空", None
        if raw == "latest":
            rows = self._model.list_by_strategy(strategy_name, limit=1)
            if not rows:
                return None, f"对比版本不存在: {compare_version}", None
            row = rows[0]
            v = int(row.get("version") or 0)
            if v <= 0:
                return None, f"对比版本不存在: {compare_version}", None
            return row, "", self.format_version_id(v)
        v = self.parse_version_id(compare_version)
        if v is None:
            return None, f"compare_version 无效: {compare_version}", None
        row = self._model.load_by_strategy_version(strategy_name, v)
        if not row:
            return None, f"对比版本不存在: {compare_version}", None
        return row, "", self.format_version_id(v)

    def restore_version(self, strategy_name: str, version_id: str) -> dict:
        v = self.parse_version_id(version_id)
        if v is None:
            return {"ok": False, "reason": "invalid_version_id", "source_version": None, "new_version": 0}
        row = self._model.load_by_strategy_version(strategy_name, v)
        if not row:
            return {"ok": False, "reason": "version_not_found", "source_version": v, "new_version": 0}
        settings_snapshot = row.get("settings_snapshot") or {}
        normalized, _ = StrategySettingsService.normalize_runtime_settings(
            strategy_name=strategy_name,
            api_settings=settings_snapshot,
        )
        if normalized is None:
            return {"ok": False, "reason": "invalid_snapshot_settings", "source_version": v, "new_version": 0}
        api_settings = StrategySettingsService.runtime_to_api(normalized)
        new_v = self.create_version_from_api_settings(strategy_name, api_settings)
        if new_v <= 0:
            return {"ok": False, "reason": "create_failed", "source_version": v, "new_version": 0}
        return {"ok": True, "reason": "", "source_version": v, "new_version": new_v}


__all__ = ["StrategyWorkbenchSnapshotService"]
