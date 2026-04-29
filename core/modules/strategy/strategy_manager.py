#!/usr/bin/env python3
"""Top-level strategy orchestrator (new-module entry)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from core.infra.project_context import PathManager
from core.modules.data_contract.cache import ContractCacheManager
from core.modules.data_contract.data_contract_manager import DataContractManager
from core.modules.data_manager import DataManager
from core.modules.strategy.engines.shared.data_classes.strategy_info import StrategyInfo
from core.modules.strategy.engines.scanner.manager import ScannerManager
from core.modules.strategy.engines.simulator.capital_allocation.manager import (
    CapitalAllocationManager,
)
from core.modules.strategy.engines.simulator.price_factor.manager import PriceFactorManager
from core.modules.strategy.services.discovery import StrategyDiscoveryHelper

logger = logging.getLogger(__name__)


class StrategyManager:
    """Strategy module entry orchestrator."""

    def __init__(self, is_verbose: bool = False):
        self.is_verbose = is_verbose
        self._contract_cache = ContractCacheManager()
        self._data_contract_manager = DataContractManager(
            contract_cache=self._contract_cache
        )
        self.data_mgr = DataManager(is_verbose=False)
        self.validated_strategies = StrategyDiscoveryHelper.discover_strategies()

    def lookup_strategy_info(self, strategy_name: str) -> Optional[StrategyInfo]:
        info = self.validated_strategies.get(strategy_name)
        if info is not None:
            return info
        folder = PathManager.userspace() / "strategies" / strategy_name
        if not folder.is_dir():
            return None
        return StrategyDiscoveryHelper.load_strategy(folder)

    def list_strategies(self) -> List[str]:
        return list(self.validated_strategies.keys())

    def get_strategy_info(self, strategy_name: str) -> Optional[StrategyInfo]:
        return self.lookup_strategy_info(strategy_name)

    def scan(self, strategy_name: str = None, date: str = None):
        if date is None:
            date = datetime.now().strftime("%Y%m%d")

        targets = self._resolve_targets(strategy_name, enabled_only=True)
        if not targets:
            logger.warning("没有可扫描的策略")
            return {}

        results: Dict[str, dict] = {}
        for info in targets:
            scanner = ScannerManager(
                strategy_name=info.name,
                data_manager=self.data_mgr,
                is_verbose=self.is_verbose,
            )
            results[info.name] = scanner.scan()
        return results

    def simulate(self, strategy_name: str = None, session_id: str = None, date: str = None):
        targets = self._resolve_targets(strategy_name, enabled_only=True)
        if not targets:
            logger.warning("没有可模拟的策略")
            return {}

        if session_id or date:
            logger.info(
                "simulate(session_id/date) 在新入口暂未接管，当前由引擎内部规则处理"
            )

        results: Dict[str, dict] = {}
        for info in targets:
            price_result = PriceFactorManager(is_verbose=self.is_verbose).run(info.name)
            capital_result = CapitalAllocationManager(is_verbose=self.is_verbose).run(
                info.name
            )
            results[info.name] = {
                "price_factor": price_result,
                "capital_allocation": capital_result,
            }
        return results

    @property
    def contract_cache(self) -> ContractCacheManager:
        return self._contract_cache

    def clear_contract_cache(self) -> None:
        self._contract_cache.clear_all()

    def _resolve_targets(
        self, strategy_name: str = None, enabled_only: bool = True
    ) -> List[StrategyInfo]:
        if strategy_name:
            info = self.lookup_strategy_info(strategy_name)
            if not info:
                return []
            if enabled_only and not info.is_enabled:
                return []
            return [info]
        if enabled_only:
            return [i for i in self.validated_strategies.values() if i.is_enabled]
        return list(self.validated_strategies.values())
