"""Settings implementer: option catalogs + apply snapshot → userspace."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


class StrategySettingsImplementer:
    def __init__(self) -> None:
        self._DiscoveryService = None
        self._Options = None
        self._Apply = None

    def lazy_load(self) -> "StrategySettingsImplementer":
        if self._Options is None:
            from core.modules.strategy.core.services.discovery import DiscoveryService

            from core.bff.APIs.strategy.routes.settings.apply import WorkbenchApplySettings
            from core.bff.APIs.strategy.routes.settings.options import (
                StrategySettingsOptions,
            )

            self._DiscoveryService = DiscoveryService
            self._Options = StrategySettingsOptions
            self._Apply = WorkbenchApplySettings
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
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        assert self._Apply is not None
        name = self.resolve_strategy_name(strategy_key_or_name)
        sid = self.parse_version_id(version_id)
        if sid is None:
            return None, "version_id 无效"
        return self._Apply.apply(
            strategy_name=name, version=sid, pretty=bool(pretty)
        )


impl = StrategySettingsImplementer()
