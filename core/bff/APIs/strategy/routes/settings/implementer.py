"""Settings implementer: option catalogs + restore version freeze → userspace settings.py."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.modules.strategy.core.helpers.version_id import WorkbenchVersionId
from core.modules.strategy import Strategy


class StrategySettingsImplementer:
    def __init__(self) -> None:
        self._Options = None
        self._Apply = None

    def lazy_load(self) -> "StrategySettingsImplementer":
        if self._Options is None:
            from core.bff.APIs.strategy.routes.settings.apply import WorkbenchApplySettings
            from core.bff.APIs.strategy.routes.settings.options import (
                StrategySettingsOptions,
            )

            self._Options = StrategySettingsOptions
            self._Apply = WorkbenchApplySettings
        return self

    def items_portfolio(self) -> List[Dict[str, Any]]:
        assert self._Options is not None
        return self._Options.items_portfolio()

    def items_sampling(self) -> List[Dict[str, Any]]:
        assert self._Options is not None
        return self._Options.items_sampling()

    def items_simulation(self) -> List[Dict[str, Any]]:
        assert self._Options is not None
        return self._Options.items_simulation()

    def items_risk_control(self) -> List[Dict[str, Any]]:
        assert self._Options is not None
        return self._Options.items_risk_control()

    def items_market_rules(self) -> List[Dict[str, Any]]:
        assert self._Options is not None
        return self._Options.items_market_rules()

    def apply_to_userspace(
        self,
        *,
        strategy_key_or_name: str,
        version_id: str,
        pretty: bool = False,
        expected_rev: Optional[str] = None,
        force: bool = False,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        assert self._Apply is not None
        name = Strategy.resolve(strategy_key_or_name)
        sid = WorkbenchVersionId.parse(version_id)
        if sid is None:
            return None, "version_id 无效"
        return self._Apply.apply(
            strategy_name=name,
            version=sid,
            pretty=bool(pretty),
            expected_rev=expected_rev,
            force=bool(force),
        )

    def persist_editor_settings(
        self,
        *,
        strategy_key_or_name: str,
        settings: Dict[str, Any],
        pretty: bool = True,
        expected_rev: Optional[str] = None,
        force: bool = False,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        assert self._Apply is not None
        name = Strategy.resolve(strategy_key_or_name)
        return self._Apply.persist_editor_settings(
            strategy_name=name,
            settings=settings,
            pretty=bool(pretty),
            expected_rev=expected_rev,
            force=bool(force),
        )

    def fetch_current_occupancy(self, strategy_key_or_name: str) -> Dict[str, Any]:
        name = Strategy.resolve(strategy_key_or_name)
        from core.bff.APIs.strategy.helpers.settings_occupancy import (
            SettingsOccupancy,
        )

        occupancy = SettingsOccupancy.read(name)
        occupancy["strategy_name"] = name
        return occupancy


impl = StrategySettingsImplementer()
