"""策略磁盘中间值保留（simulations / scan），与 workbench DB 缓存独立。

触发：allocate / scan 写盘路径会自动 prune；本服务供 Facade 显式调用。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.scanner.helpers.cache_manager import (
    ScanCacheManager,
)
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.discovery import DiscoveryService

logger = logging.getLogger(__name__)


class ResultsRetention:
    """按 ``data.json`` retention 清理策略磁盘中间值。"""

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
        cap = max_versions
        if cap is None:
            cap = ProjectContext.config.get_scan_results_max_versions()
        cache = ScanCacheManager(folder, max_cache_days=int(cap))
        before = cls._scan_version_count(cache.cache_base_dir)
        cache.cleanup_old_cache()
        after = cls._scan_version_count(cache.cache_base_dir)
        deleted = max(0, before - after)
        return {
            "ok": True,
            "strategy_folder": str(folder),
            "deleted_count": deleted,
            "max_versions": int(cap),
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

    @staticmethod
    def _scan_version_count(cache_base_dir: Union[str, Path]) -> int:
        root = Path(cache_base_dir)
        if not root.is_dir():
            return 0
        return sum(
            1
            for d in root.iterdir()
            if d.is_dir() and d.name.isdigit() and len(d.name) == 8
        )


__all__ = ["ResultsRetention"]
