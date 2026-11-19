"""Version implementer: disk registry reads + cache clear via Strategy Facade。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.modules.strategy import Strategy
from core.bff.APIs.strategy.helpers.workbench_snapshots import WorkbenchSnapshots


class StrategyVersionImplementer:
    def __init__(self) -> None:
        self._WorkbenchSnapshots = None

    def lazy_load(self) -> "StrategyVersionImplementer":
        if self._WorkbenchSnapshots is None:
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
        sid = Strategy.parse_workbench_version_id(version_id)
        if sid is None:
            raise ValueError("version_id 无效")
        row = self._WorkbenchSnapshots.fetch_by_version(name, sid)
        if row is None:
            raise FileNotFoundError("快照不存在")
        return row

    def clear_cache_all(self) -> Dict[str, Any]:
        return Strategy.clear_all_simulation_results()

    def clear_cache_by_version(
        self, *, strategy_key_or_name: str, version_id: str
    ) -> Dict[str, Any]:
        name = Strategy.resolve(strategy_key_or_name)
        return Strategy.delete_simulation_version(name, version_id)


impl = StrategyVersionImplementer()
