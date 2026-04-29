#!/usr/bin/env python3
"""Shared three-stage flow template for simulator engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )


class BaseSimulationFlow(ABC):
    """Template method: preprocess -> execute -> postprocess."""

    def run(
        self,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"] = None,
    ) -> Any:
        preprocessed = self.preprocess(
            strategy_name=strategy_name, strategy_info=strategy_info
        )
        executed = self.execute(preprocessed)
        return self.postprocess(preprocessed, executed)

    @abstractmethod
    def preprocess(
        self,
        *,
        strategy_name: str,
        strategy_info: Optional["DiscoveredStrategy"],
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def execute(self, preprocessed: Dict[str, Any]) -> Any:
        pass

    @abstractmethod
    def postprocess(self, preprocessed: Dict[str, Any], executed: Any) -> Any:
        pass

