#!/usr/bin/env python3
"""Factory helpers for ``StrategyHookContext``."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.types import (
    CalendarAsOfContext,
)

from .types import (
    BatchScope,
    EntityScope,
    HookPhase,
    PriceFactorScope,
    RunScope,
    ScanScope,
    StrategyHookContext,
)


def run_context(
    *,
    strategy_name: str,
    settings: StrategySettingsView,
    run_name: str,
    output_dir: Optional[Path],
    total_entities: int,
    execution_mode: str,
) -> StrategyHookContext:
    return StrategyHookContext(
        phase=HookPhase.RUN,
        strategy_name=strategy_name,
        settings=settings,
        run=RunScope(
            run_name=run_name,
            output_dir=output_dir,
            total_entities=total_entities,
            execution_mode=execution_mode,
        ),
    )


def batch_context(
    *,
    strategy_name: str,
    settings: StrategySettingsView,
    batch_job_id: str,
    stock_ids: List[str],
    report: Any = None,
    progress: Any = None,
) -> StrategyHookContext:
    return StrategyHookContext(
        phase=HookPhase.BATCH,
        strategy_name=strategy_name,
        settings=settings,
        batch=BatchScope(
            batch_job_id=batch_job_id,
            stock_ids=list(stock_ids),
            report=report,
            progress=progress,
        ),
    )


def entity_context(
    *,
    strategy_name: str,
    settings: StrategySettingsView,
    stock_id: str,
    job_payload: Dict[str, Any],
    stock_info: Dict[str, Any],
    data_manager: Any = None,
) -> StrategyHookContext:
    return StrategyHookContext(
        phase=HookPhase.ENTITY,
        strategy_name=strategy_name,
        settings=settings,
        entity=EntityScope(
            stock_id=stock_id,
            job_payload=dict(job_payload),
            stock_info=dict(stock_info),
            data_manager=data_manager,
        ),
    )


def scan_context(
    *,
    strategy_name: str,
    settings: StrategySettingsView,
    stock_id: str,
    job_payload: Dict[str, Any],
    stock_info: Dict[str, Any],
    data: Dict[str, Any],
    scan_date: Optional[str] = None,
    opportunity: Optional[Opportunity] = None,
    data_manager: Any = None,
) -> StrategyHookContext:
    return StrategyHookContext(
        phase=HookPhase.SCAN,
        strategy_name=strategy_name,
        settings=settings,
        entity=EntityScope(
            stock_id=stock_id,
            job_payload=dict(job_payload),
            stock_info=dict(stock_info),
            data_manager=data_manager,
        ),
        scan=ScanScope(
            data=data,
            scan_date=scan_date,
            opportunity=opportunity,
        ),
    )


def calendar_asof_context(
    *,
    strategy_name: str,
    settings: StrategySettingsView,
    calendar: CalendarAsOfContext,
    job_payload: Optional[Dict[str, Any]] = None,
) -> StrategyHookContext:
    entity = None
    if job_payload is not None:
        stock_ids = list(calendar.stocks.keys())
        anchor = stock_ids[0] if stock_ids else ""
        entity = EntityScope(
            stock_id=anchor,
            job_payload=dict(job_payload),
            stock_info={"id": anchor, "name": anchor},
        )
    return StrategyHookContext(
        phase=HookPhase.CALENDAR_ASOF,
        strategy_name=strategy_name,
        settings=settings,
        calendar=calendar,
        entity=entity,
    )


def price_factor_context(
    *,
    strategy_name: str,
    settings: StrategySettingsView,
    stock_id: str,
    config: Dict[str, Any],
    opportunities: Optional[List[Dict[str, Any]]] = None,
    opportunity_row: Optional[Dict[str, Any]] = None,
    target_row: Optional[Dict[str, Any]] = None,
    stock_summary: Optional[Dict[str, Any]] = None,
) -> StrategyHookContext:
    return StrategyHookContext(
        phase=HookPhase.PRICE_FACTOR,
        strategy_name=strategy_name,
        settings=settings,
        price_factor=PriceFactorScope(
            stock_id=stock_id,
            config=dict(config),
            opportunities=opportunities,
            opportunity_row=opportunity_row,
            target_row=target_row,
            stock_summary=stock_summary,
        ),
    )


__all__ = [
    "batch_context",
    "calendar_asof_context",
    "entity_context",
    "price_factor_context",
    "run_context",
    "scan_context",
]
