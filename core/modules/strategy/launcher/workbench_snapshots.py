"""Workbench snapshot read APIs for UI (V2-01 / V2-03 / V2-08).

Consumers: ``core.bff.APIs.strategy.routes.version`` (and report/settings apply).

Reads ``sys_strategy_workbench_snapshot`` + discovery disk settings.
Does not key by fingerprint (that is ``SimulationCacheManager`` write/hit path).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.modules.data_manager import DataManager
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery import DiscoveryService
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    StrategyInfo,
)

from .report_hydrate import hydrate_workbench_result_report

logger = logging.getLogger(__name__)

_MAX_ROW_REPAIR_LOOPS = 5
_DROPDOWN_LIMIT = 10


class WorkbenchSnapshots:
    """UI workbench snapshot catalog / latest / by-version."""

    @staticmethod
    def parse_version_id(version_id: str) -> Optional[int]:
        """Accept ``v3`` / ``3`` forms."""
        from core.modules.strategy.core.helpers.version_id import WorkbenchVersionId

        return WorkbenchVersionId.parse(version_id)

    @classmethod
    def fetch_latest(cls, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Latest persisted row, or cold-start synthetic row (version=0, not written)."""
        name = str(strategy_name or "").strip()
        if not name:
            return None

        info = cls._find_strategy(name)
        if info is None:
            return None

        model = cls._snapshot_model()
        if model is None:
            logger.error("Workbench snapshot table is not registered")
            return None

        for _ in range(_MAX_ROW_REPAIR_LOOPS):
            row = cls._load_latest_row(model, name)
            if not row:
                break
            if cls._row_usable(row):
                return cls._enrich_row(name, info, row)
            sid = int(row.get("version") or 0)
            if sid <= 0:
                logger.warning("Unusable snapshot row for %s (missing version)", name)
                break
            logger.warning(
                "Removing unusable workbench snapshot row strategy=%s version=%s",
                name,
                sid,
            )
            try:
                model.delete_version_row(name, sid)
            except Exception:
                logger.exception("Failed to delete unusable snapshot %s v%s", name, sid)
                break

        return cls._synthetic_cold_start_row(name, dict(info.settings or {}))

    @classmethod
    def fetch_by_version(
        cls,
        strategy_name: str,
        version: int,
    ) -> Optional[Dict[str, Any]]:
        name = str(strategy_name or "").strip()
        sid = int(version)
        if not name or sid <= 0:
            return None

        info = cls._find_strategy(name)
        if info is None:
            return None

        model = cls._snapshot_model()
        if model is None:
            logger.error("Workbench snapshot table is not registered")
            return None

        row = model.load_by_strategy_version(name, sid)
        if not row or not cls._row_usable(row):
            return None
        return cls._enrich_row(name, info, dict(row))

    @classmethod
    def list_dropdown(
        cls,
        strategy_name: str,
        *,
        limit: int = _DROPDOWN_LIMIT,
    ) -> List[Dict[str, Any]]:
        name = str(strategy_name or "").strip()
        if not name:
            return []
        model = cls._snapshot_model()
        if model is None:
            return []
        rows = model.list_by_strategy(name, limit=max(1, int(limit)))
        items: List[Dict[str, Any]] = []
        for row in rows:
            sid = int(row.get("version") or 0)
            if sid <= 0:
                continue
            items.append(
                {
                    "version_id": f"v{sid}",
                    "version": sid,
                    "updated_at": cls._iso(row.get("updated_at")),
                    "created_at": cls._iso(row.get("created_at")),
                }
            )
        return items

    @classmethod
    def ui_flags(cls, strategy_name: str, row: Dict[str, Any]) -> Dict[str, bool]:
        sid = int(row.get("version") or 0)
        model = cls._snapshot_model()
        n = 0
        if model is not None:
            n = len(model.list_by_strategy(str(strategy_name).strip(), limit=500) or [])
        return {
            "has_persisted_snapshot": sid > 0,
            "has_other_versions": sid > 0 and n >= 2,
        }

    # --- internals ---------------------------------------------------------

    @classmethod
    def _enrich_row(
        cls,
        strategy_name: str,
        info: StrategyInfo,
        row: Dict[str, Any],
    ) -> Dict[str, Any]:
        out = dict(row)
        settings_diff = out.get("settings_diff")
        if isinstance(settings_diff, dict):
            disk_settings = dict(info.settings or {})
            out["settings_snapshot"] = StrategySettings.merge_disk_with_diff(
                disk_settings,
                settings_diff,
            )
        elif not isinstance(out.get("settings_snapshot"), dict):
            out["settings_snapshot"] = dict(info.settings or {})

        rr = out.get("result_report") or out.get("reports") or {}
        if isinstance(rr, dict):
            out["result_report"] = hydrate_workbench_result_report(
                strategy_name,
                rr,
                workbench_version=int(out.get("version") or 0),
            )
        return out

    @classmethod
    def _find_strategy(cls, key_or_id: str) -> Optional[StrategyInfo]:
        needle = str(key_or_id or "").strip()
        if not needle:
            return None
        for info in DiscoveryService.discover_strategies():
            if info.id() == needle or info.key == needle:
                return info
        return None

    @staticmethod
    def _snapshot_model():
        try:
            return DataManager().get_table("sys_strategy_workbench_snapshot")
        except Exception:
            logger.exception("Failed to resolve workbench snapshot table")
            return None

    @staticmethod
    def _load_latest_row(model: Any, strategy_name: str) -> Optional[Dict[str, Any]]:
        rows = model.list_by_strategy(str(strategy_name), limit=1)
        if not rows:
            return None
        return dict(rows[0] or {})

    @staticmethod
    def _row_usable(row: Dict[str, Any]) -> bool:
        return isinstance(row.get("settings_diff"), dict)

    @staticmethod
    def _synthetic_cold_start_row(
        strategy_name: str,
        settings_api: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "strategy_name": str(strategy_name or "").strip(),
            "version": 0,
            "settings_snapshot": dict(settings_api or {}),
            "reports": {},
            "result_report": {},
            "settings_finger_print_id": "",
            "env_fingerprint_id": "",
        }

    @staticmethod
    def _iso(dt: Any) -> Optional[str]:
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt.isoformat(sep=" ", timespec="seconds")
        return str(dt)


__all__ = ["WorkbenchSnapshots"]
