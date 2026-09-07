"""产物生命周期：keep-N prune 与显式删除。

- prune_*：按 retention 上限裁剪 simulations / scan
- clear_*：用户/BFF 主动删（单 version 或全策略 simulations）
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.services.discovery import DiscoveryService

from .store import ArtifactStore
from .version_meta import VersionMetaStore

logger = logging.getLogger(__name__)


class ArtifactRetention:
    """策略磁盘产物的条件清理与显式删除。"""

    @classmethod
    def prune_simulation_results(
        cls,
        key_or_id: str,
        *,
        kind: Optional[str] = None,
        max_versions: Optional[int] = None,
    ) -> Dict[str, Any]:
        """对单个策略的 simulations 目录做 keep-N。

        ``kind`` 为 ``enumerate`` / ``price_factor`` / ``portfolio``
        （缩写 ``enum`` / ``price`` 也可）；``None`` 表示三步都清。
        """
        folder = cls._resolve_folder(key_or_id)
        return ArtifactStore.prune(
            folder, kind=kind, max_versions=max_versions
        )

    @classmethod
    def prune_scan_results(
        cls,
        key_or_id: str,
        *,
        max_versions: Optional[int] = None,
    ) -> Dict[str, Any]:
        """对单个策略的 scan 日期目录做 keep-N。"""
        folder = cls._resolve_folder(key_or_id)
        return ArtifactStore.prune_scan(folder, max_versions=max_versions)

    @classmethod
    def clear_all(cls) -> Dict[str, Any]:
        """删除所有已发现策略的 ``results/simulations/``。"""
        deleted = 0
        try:
            for info in DiscoveryService.discover_strategies():
                folder = Path(info.resolved_folder())
                sim_root = ArtifactStore.simulations_root(folder)
                if sim_root.is_dir():
                    shutil.rmtree(sim_root)
                    deleted += 1
        except Exception as exc:
            logger.exception("clear_all simulation artifacts failed")
            return {"ok": False, "error": str(exc) or "清理失败", "deleted_count": 0}
        return {"ok": True, "deleted_count": deleted, "cleared": deleted >= 0}

    @classmethod
    def clear_by_version(cls, strategy_name: str, version: int) -> Dict[str, Any]:
        """删除单个策略的一个 simulation version 目录 + registry 条目。"""
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
        was_pinned = False
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
            was_pinned = vid in set(VersionMetaStore.read_pinned_ids(root))
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
            "was_pinned": was_pinned,
        }

    @classmethod
    def set_pinned(
        cls,
        strategy_name: str,
        version: int,
        pinned: bool,
    ) -> Dict[str, Any]:
        """固定 / 取消固定一份 simulation version（只改 meta.pinned）。"""
        name = str(strategy_name or "").strip()
        sid = int(version)
        if not name or sid <= 0:
            return {"ok": False, "error": "参数无效"}

        try:
            folder = DiscoveryService.resolve_strategy_folder(name)
        except Exception:
            folder = None
        if folder is None:
            return {"ok": False, "error": "策略不存在"}

        root = ArtifactStore.simulations_root(folder)
        try:
            ids = VersionMetaStore.set_version_pinned(root, str(sid), bool(pinned))
        except ValueError as exc:
            return {"ok": False, "error": str(exc) or "version_id 无效"}
        except FileNotFoundError:
            return {"ok": False, "error": "快照不存在"}
        return {
            "ok": True,
            "pinned": bool(pinned),
            "strategy_name": name,
            "version_id": f"v{sid}",
            "pinned_ids": [f"v{item}" for item in ids],
        }

    @staticmethod
    def _resolve_folder(key_or_id: str) -> Path:
        info = DiscoveryService.find_strategy(key_or_id)
        if info is not None:
            folder = getattr(info, "folder", None)
            if folder:
                return Path(folder)
            if hasattr(info, "resolved_folder"):
                return Path(info.resolved_folder())
        return ProjectContext.path.coerce_strategy_folder(str(key_or_id).strip())


__all__ = ["ArtifactRetention"]
