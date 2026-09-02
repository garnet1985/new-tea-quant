"""Workbench snapshot read model for UI (V2-01 / V2-03 / V2-08).

Version catalog and settings snapshots come from disk ``simulations/meta.json``
registry + ``{vid}/settings.json`` / ``effective_settings.json`` + step artifacts.

Consumers: ``routes/version``, ``routes/report``, ``routes/settings/apply``.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.modules.strategy.core.enums import SimulateKind, WorkbenchStep
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore
from core.modules.strategy.core.services.discovery import DiscoveryService
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    StrategyInfo,
)
from core.modules.strategy.core.services.artifacts import SimulationVersionStore

from core.bff.APIs.strategy.helpers.report_hydrate import (
    hydrate_workbench_result_report,
)

logger = logging.getLogger(__name__)

_DROPDOWN_LIMIT = 10

_STEP_SLOTS: Tuple[Tuple[SimulateKind, str], ...] = (
    (SimulateKind.ENUMERATE, WorkbenchStep.ENUM.report_slot),
    (SimulateKind.PRICE_FACTOR, WorkbenchStep.PRICE.report_slot),
    (SimulateKind.PORTFOLIO, WorkbenchStep.PORTFOLIO.report_slot),
)


class WorkbenchSnapshots:
    """UI workbench snapshot catalog / latest / by-version (disk registry)."""

    @staticmethod
    def parse_version_id(version_id: str) -> Optional[int]:
        """Accept ``v3`` / ``3`` forms."""
        from core.modules.strategy.core.helpers.version_id import WorkbenchVersionId

        return WorkbenchVersionId.parse(version_id)

    @classmethod
    def fetch_latest(cls, strategy_name: str) -> Optional[Dict[str, Any]]:
        """Latest disk version row, or cold-start synthetic row (version=0)."""
        name = str(strategy_name or "").strip()
        if not name:
            return None

        info = cls._find_strategy(name)
        if info is None:
            return None

        root = cls._simulations_root(info)
        version_ids = cls._sorted_version_ids(root, descending=True)
        for vid in version_ids:
            row = cls._build_disk_row(name, info, int(vid))
            if row is not None:
                return row

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

        return cls._build_disk_row(name, info, sid)

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

        info = cls._find_strategy(name)
        if info is None:
            return []

        root = cls._simulations_root(info)
        items: List[Dict[str, Any]] = []
        for vid in cls._sorted_version_ids(root, descending=True)[: max(1, int(limit))]:
            entry = VersionMetaStore.get_registry_entry(root, vid) or {}
            sid = int(vid)
            items.append(
                {
                    "version_id": f"v{sid}",
                    "version": sid,
                    "env_invalid": VersionMetaStore.is_env_invalid(
                        entry,
                        cls._current_env_fp(info),
                    ),
                    "updated_at": cls._iso(entry.get("updated_at") or entry.get("created_at")),
                    "created_at": cls._iso(entry.get("created_at")),
                }
            )
        return items

    @classmethod
    def ui_flags(cls, strategy_name: str, row: Dict[str, Any]) -> Dict[str, bool]:
        sid = int(row.get("version") or 0)
        info = cls._find_strategy(str(strategy_name or "").strip())
        n = 0
        if info is not None:
            n = len(cls._sorted_version_ids(cls._simulations_root(info), descending=True))
        return {
            "has_persisted_snapshot": sid > 0,
            "has_other_versions": sid > 0 and n >= 2,
            "env_invalid": bool(row.get("env_invalid")),
        }

    @classmethod
    def _current_env_fp(cls, info: StrategyInfo) -> str:
        from core.modules.strategy.core.services.fingerprint import (
            FingerprintCalculator,
        )

        # 列 version 只比 env，不要求当前 settings 可跑
        return str(FingerprintCalculator.to_env_fingerprint(info) or "")

    @classmethod
    def _env_invalid_for_entry(
        cls,
        info: StrategyInfo,
        entry: Dict[str, Any],
    ) -> bool:
        return VersionMetaStore.is_env_invalid(entry, cls._current_env_fp(info))

    # --- internals ---------------------------------------------------------

    @classmethod
    def _build_disk_row(
        cls,
        strategy_name: str,
        info: StrategyInfo,
        version: int,
    ) -> Optional[Dict[str, Any]]:
        vid = str(int(version))
        root = cls._simulations_root(info)
        if VersionMetaStore.resolve_version(root, vid) is None:
            return None

        folder = cls._strategy_folder(info)
        entry = VersionMetaStore.get_registry_entry(root, vid) or {}
        settings_snapshot, disk_settings, effective_subset = cls._settings_layers_from_disk(
            info, root, vid
        )
        result_report = cls._result_report_from_disk(folder, root, vid)

        row: Dict[str, Any] = {
            "strategy_name": str(strategy_name or "").strip(),
            "version": int(version),
            "settings_snapshot": settings_snapshot,
            "disk_settings": disk_settings,
            "effective_settings": effective_subset,
            "reports": result_report,
            "result_report": result_report,
            "execute_fp": str(entry.get("execute_fp") or ""),
            "env_fingerprint_id": str(entry.get("env_fp") or ""),
            "env_invalid": cls._env_invalid_for_entry(info, entry),
            "created_at": entry.get("created_at"),
            "updated_at": entry.get("updated_at") or entry.get("created_at"),
        }
        return cls._enrich_row(strategy_name, info, row)

    @classmethod
    def _settings_layers_from_disk(
        cls,
        info: StrategyInfo,
        simulations_root: Path,
        version_id: str,
    ) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        disk_settings = dict(info.settings or {})
        archived = VersionMetaStore.read_settings(simulations_root, version_id) or {}
        effective = VersionMetaStore.read_effective_settings(
            simulations_root, version_id
        ) or {}
        if archived:
            return archived, disk_settings, effective
        if not effective:
            return disk_settings, disk_settings, {}
        snapshot = StrategySettings.merge_disk_with_diff(disk_settings, effective)
        return snapshot, disk_settings, effective

    @classmethod
    def _settings_snapshot_from_disk(
        cls,
        info: StrategyInfo,
        simulations_root: Path,
        version_id: str,
    ) -> Dict[str, Any]:
        snapshot, _, _ = cls._settings_layers_from_disk(
            info, simulations_root, version_id
        )
        return snapshot

    @classmethod
    def _result_report_from_disk(
        cls,
        strategy_folder: Path,
        simulations_root: Path,
        version_id: str,
    ) -> Dict[str, Any]:
        result_report: Dict[str, Any] = {}
        for kind, slot_key in _STEP_SLOTS:
            if not VersionMetaStore.step_has_artifacts(simulations_root, version_id, kind):
                continue
            cached = SimulationVersionStore.get_cache_by_version_id(
                strategy_folder,
                version_id,
                kind,
            )
            if not cached:
                continue
            slot = cached.get(kind.value)
            if isinstance(slot, dict) and slot:
                result_report[slot_key] = dict(slot)
        return result_report

    @classmethod
    def _sorted_version_ids(cls, simulations_root: Path, *, descending: bool) -> List[str]:
        ids = VersionMetaStore.list_version_ids(simulations_root)
        return sorted(ids, key=int, reverse=descending)

    @classmethod
    def _simulations_root(cls, info: StrategyInfo) -> Path:
        return ArtifactStore.simulations_root(cls._strategy_folder(info))

    @staticmethod
    def _strategy_folder(info: StrategyInfo) -> Path:
        if hasattr(info, "resolved_folder"):
            folder = info.resolved_folder()
            if folder is not None:
                return Path(folder)
        return Path(info.folder)

    @classmethod
    def _enrich_row(
        cls,
        strategy_name: str,
        info: StrategyInfo,
        row: Dict[str, Any],
    ) -> Dict[str, Any]:
        out = dict(row)
        if not isinstance(out.get("settings_snapshot"), dict):
            out["settings_snapshot"] = dict(info.settings or {})
        if not isinstance(out.get("disk_settings"), dict):
            out["disk_settings"] = dict(info.settings or {})
        if not isinstance(out.get("effective_settings"), dict):
            out["effective_settings"] = {}

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
    def _synthetic_cold_start_row(
        strategy_name: str,
        settings_api: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "strategy_name": str(strategy_name or "").strip(),
            "version": 0,
            "settings_snapshot": dict(settings_api or {}),
            "disk_settings": dict(settings_api or {}),
            "effective_settings": {},
            "reports": {},
            "result_report": {},
            "execute_fp": "",
            "env_fingerprint_id": "",
            "env_invalid": False,
        }

    @staticmethod
    def _iso(dt: Any) -> Optional[str]:
        if dt is None:
            return None
        if isinstance(dt, datetime):
            return dt.isoformat(sep=" ", timespec="seconds")
        return str(dt)


__all__ = ["WorkbenchSnapshots"]
