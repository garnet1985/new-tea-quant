"""Workbench simulation cache clear (domain service).

``clear_by_version`` removes disk simulation version dirs + registry entries.
``clear_all`` removes ``results/simulations/`` for every discovered strategy.

Consumers: BFF support + ``temp_cleanup`` (must not depend on ``core.bff``).
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Dict

from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore
from core.modules.strategy.core.services.discovery import DiscoveryService

logger = logging.getLogger(__name__)


class WorkbenchCacheClear:
    """Clear workbench simulation cache on disk."""

    @classmethod
    def clear_all(cls) -> Dict[str, Any]:
        deleted = 0
        try:
            for info in DiscoveryService.discover_strategies():
                folder = Path(info.resolved_folder())
                sim_root = ArtifactStore.simulations_root(folder)
                if sim_root.is_dir():
                    shutil.rmtree(sim_root)
                    deleted += 1
        except Exception as exc:
            logger.exception("clear_all workbench simulation cache failed")
            return {"ok": False, "error": str(exc) or "清理失败", "deleted_count": 0}
        return {"ok": True, "deleted_count": deleted, "cleared": deleted >= 0}

    @classmethod
    def clear_by_version(cls, strategy_name: str, version: int) -> Dict[str, Any]:
        name = str(strategy_name or "").strip()
        sid = int(version)
        if not name or sid <= 0:
            return {"ok": False, "error": "参数无效", "deleted": False}

        try:
            folder = DiscoveryService.resolve_strategy_folder(name)
        except Exception:
            folder = None

        vid = str(sid)
        removed_disk = False
        if folder is not None:
            root = ArtifactStore.simulations_root(folder)
            version_dir = Path(root) / vid
            had_entry = VersionMetaStore.get_registry_entry(root, vid) is not None
            had_dir = version_dir.is_dir()
            if not had_entry and not had_dir:
                return {
                    "ok": False,
                    "error": "快照不存在",
                    "deleted": False,
                    "strategy_name": name,
                    "version": sid,
                }
            VersionMetaStore.remove_version_from_registry(root, vid)
            if had_dir:
                shutil.rmtree(version_dir)
            removed_disk = had_entry or had_dir

        if not removed_disk:
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


__all__ = ["WorkbenchCacheClear"]
