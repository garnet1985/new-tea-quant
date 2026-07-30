"""Version implementer: workbench snapshot reads + DbCache clear.

Reads go through launcher ``WorkbenchSnapshots`` (cold-start / hydrate stay there).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


class StrategyVersionImplementer:
    def __init__(self) -> None:
        self._DiscoveryService = None
        self._WorkbenchCacheClear = None
        self._WorkbenchSnapshots = None

    def lazy_load(self) -> "StrategyVersionImplementer":
        if self._WorkbenchSnapshots is None:
            from core.modules.strategy.core.services.discovery import DiscoveryService
            from core.modules.strategy.core.services.workbench_cache_clear import (
                WorkbenchCacheClear,
            )
            from core.modules.strategy.launcher.workbench_snapshots import (
                WorkbenchSnapshots,
            )

            self._DiscoveryService = DiscoveryService
            self._WorkbenchCacheClear = WorkbenchCacheClear
            self._WorkbenchSnapshots = WorkbenchSnapshots
        return self

    def resolve_strategy_name(self, strategy_key_or_name: str) -> str:
        """``meta.key`` 或 path name → userspace 相对 path（快照表主键）。"""
        assert self._DiscoveryService is not None
        needle = str(strategy_key_or_name or "").strip()
        if not needle:
            raise ValueError("strategy_key_or_name 不能为空")
        for info in self._DiscoveryService.discover_strategies():
            if info.key == needle or info.id() == needle:
                return str(info.id())
        raise FileNotFoundError(f"策略不存在: {needle!r}")

    @staticmethod
    def parse_version_id(version_id: str) -> Optional[int]:
        text = str(version_id or "").strip()
        if not text:
            return None
        if text.lower().startswith("v"):
            text = text[1:]
        try:
            n = int(text)
            return n if n > 0 else None
        except ValueError:
            return None

    def fetch_latest(
        self, strategy_key_or_name: str
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, bool]]:
        """Latest row (or cold-start synthetic) + V2-01 ``ui_flags``."""
        assert self._WorkbenchSnapshots is not None
        name = self.resolve_strategy_name(strategy_key_or_name)
        row = self._WorkbenchSnapshots.fetch_latest(name)
        if row is None:
            return None, {}
        flags = self._WorkbenchSnapshots.ui_flags(name, row)
        return row, flags

    def list_versions(self, strategy_key_or_name: str) -> List[Dict[str, Any]]:
        assert self._WorkbenchSnapshots is not None
        name = self.resolve_strategy_name(strategy_key_or_name)
        return self._WorkbenchSnapshots.list_dropdown(name)

    def fetch_by_version(
        self, *, strategy_key_or_name: str, version_id: str
    ) -> Dict[str, Any]:
        assert self._WorkbenchSnapshots is not None
        name = self.resolve_strategy_name(strategy_key_or_name)
        sid = self.parse_version_id(version_id)
        if sid is None:
            raise ValueError("version_id 无效")
        row = self._WorkbenchSnapshots.fetch_by_version(name, sid)
        if row is None:
            raise FileNotFoundError("快照不存在")
        return row

    def clear_cache_all(self) -> Dict[str, Any]:
        assert self._WorkbenchCacheClear is not None
        return self._WorkbenchCacheClear.clear_all()

    def clear_cache_by_version(
        self, *, strategy_key_or_name: str, version_id: str
    ) -> Dict[str, Any]:
        assert self._WorkbenchCacheClear is not None
        name = self.resolve_strategy_name(strategy_key_or_name)
        sid = self.parse_version_id(version_id)
        if sid is None:
            raise ValueError("version_id 无效")
        return self._WorkbenchCacheClear.clear_by_version(name, sid)


impl = StrategyVersionImplementer()
