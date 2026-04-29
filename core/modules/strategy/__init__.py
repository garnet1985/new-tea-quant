#!/usr/bin/env python3
"""Strategy module public entrypoints."""

from .strategy_manager import StrategyManager
from .base_strategy_worker import BaseStrategyWorker
from .engines.shared.data_classes.opportunity import Opportunity
from .engines.scanner.helpers import ScannerStatisticsHelper
from .engines.shared.helpers import JobBuilderHelper, StockSamplingHelper
from .engines.simulator.helpers import SimulatorStatisticsHelper
from .enums import ExecutionMode, OpportunityStatus, SellReason
from .services import (
    StrategyDataInjectionService,
    StrategyOutputReaderService,
    StrategyDiscoveryHelper,
    build_settings,
    normalize_and_validate,
    validate_settings,
)

__all__ = [
    "StrategyManager",
    "BaseStrategyWorker",
    "Opportunity",
    "ExecutionMode",
    "OpportunityStatus",
    "SellReason",
    "JobBuilderHelper",
    "ScannerStatisticsHelper",
    "SimulatorStatisticsHelper",
    "StockSamplingHelper",
    "StrategyDataInjectionService",
    "StrategyOutputReaderService",
    "StrategyDiscoveryHelper",
    "build_settings",
    "validate_settings",
    "normalize_and_validate",
]

