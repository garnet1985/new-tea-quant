"""Version implementer: workbench snapshot reads + DbCache clear.

Reads go through BFF ``WorkbenchSnapshots`` (UI snapshot read model).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.modules.strategy.core.helpers.version_id import WorkbenchVersionId
from core.modules.strategy import Strategy


class StrategyVersionImplementer:
    def __init__(self) -> None:
        self._WorkbenchCacheClear = None
        self._WorkbenchSnapshots = None

    def lazy_load(self) -> "StrategyVersionImplementer":
        if self._WorkbenchSnapshots is None:
            from core.modules.strategy.core.services.workbench_cache_clear import (
                WorkbenchCacheClear,
            )
            from core.bff.APIs.strategy.helpers.workbench_snapshots import (
                WorkbenchSnapshots,
            )

            self._WorkbenchCacheClear = WorkbenchCacheClear
            self._WorkbenchSnapshots = WorkbenchSnapshots
        return self

    def fetch_latest(
        self, strategy_key_or_name: str
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, bool]]:
        """Latest row (or cold-start synthetic) + V2-01 ``ui_flags``."""
        assert self._WorkbenchSnapshots is not None
        name = Strategy.resolve(strategy_key_or_name)
        row = self._WorkbenchSnapshots.fetch_latest(name)
        if row is None:
            return None, {}
        flags = self._WorkbenchSnapshots.ui_flags(name, row)
        return row, flags

    def list_versions(self, strategy_key_or_name: str) -> List[Dict[str, Any]]:
        assert self._WorkbenchSnapshots is not None
        name = Strategy.resolve(strategy_key_or_name)
        return self._WorkbenchSnapshots.list_dropdown(name)

    def fetch_by_version(
        self, *, strategy_key_or_name: str, version_id: str
    ) -> Dict[str, Any]:
        assert self._WorkbenchSnapshots is not None
        name = Strategy.resolve(strategy_key_or_name)
        sid = WorkbenchVersionId.parse(version_id)
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
        name = Strategy.resolve(strategy_key_or_name)
        sid = WorkbenchVersionId.parse(version_id)
        if sid is None:
            raise ValueError("version_id 无效")
        return self._WorkbenchCacheClear.clear_by_version(name, sid)


impl = StrategyVersionImplementer()
