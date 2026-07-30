"""Version implementer: workbench snapshot-cache clear (DbCache rows).

Version read / apply-settings still via stack until this package is fully migrated.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class StrategyVersionImplementer:
    def __init__(self) -> None:
        self._DiscoveryService = None
        self._WorkbenchCacheClear = None

    def lazy_load(self) -> "StrategyVersionImplementer":
        if self._WorkbenchCacheClear is None:
            from core.modules.strategy.core.services.discovery import DiscoveryService
            from core.modules.strategy.core.services.workbench_cache_clear import (
                WorkbenchCacheClear,
            )

            self._DiscoveryService = DiscoveryService
            self._WorkbenchCacheClear = WorkbenchCacheClear
        return self

    def resolve_strategy_name(self, strategy_key_or_name: str) -> str:
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
