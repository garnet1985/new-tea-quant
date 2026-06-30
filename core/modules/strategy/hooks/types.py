#!/usr/bin/env python3
"""Strategy hooks — shared context types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.types import (
    CalendarAsOfContext,
)


class HookPhase(str, Enum):
    RUN = "run"
    BATCH = "batch"
    ENTITY = "entity"
    SCAN = "scan"
    CALENDAR_ASOF = "calendar_asof"
    PRICE_FACTOR = "price_factor"


@dataclass(frozen=True)
class RunScope:
    run_name: str
    output_dir: Optional[Path]
    total_entities: int
    execution_mode: str


@dataclass(frozen=True)
class BatchScope:
    batch_job_id: str
    stock_ids: List[str]
    report: Any = None
    progress: Any = None


@dataclass(frozen=True)
class EntityScope:
    stock_id: str
    job_payload: Dict[str, Any]
    stock_info: Dict[str, Any]
    data_manager: Any = None


@dataclass(frozen=True)
class ScanScope:
    data: Dict[str, Any]
    scan_date: Optional[str] = None
    opportunity: Optional[Opportunity] = None


@dataclass(frozen=True)
class PriceFactorScope:
    stock_id: str
    config: Dict[str, Any]
    opportunities: Optional[List[Dict[str, Any]]] = None
    opportunity_row: Optional[Dict[str, Any]] = None
    target_row: Optional[Dict[str, Any]] = None
    stock_summary: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class StrategyHookContext:
    phase: HookPhase
    strategy_name: str
    settings: StrategySettingsView

    run: Optional[RunScope] = None
    batch: Optional[BatchScope] = None
    entity: Optional[EntityScope] = None
    scan: Optional[ScanScope] = None
    calendar: Optional[CalendarAsOfContext] = None
    price_factor: Optional[PriceFactorScope] = None

    def settings_dict(self) -> Dict[str, Any]:
        return self.settings.to_dict()


__all__ = [
    "BatchScope",
    "CalendarAsOfContext",
    "EntityScope",
    "HookPhase",
    "PriceFactorScope",
    "RunScope",
    "ScanScope",
    "StrategyHookContext",
]
