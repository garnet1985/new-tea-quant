from __future__ import annotations

import pytest

from core.infra.worker.dispatch_time_planner import resolve_time_dispatch_plan
from core.modules.strategy.engines.simulator.price_factor.data_classes.settings import (
    StrategyPriceSimulatorSettings,
)
from core.modules.strategy.services.execution.price_dispatch import (
    resolve_price_dispatch_plan,
)


def test_main_process_when_compute_cheaper_than_overhead():
    plan = resolve_time_dispatch_plan(
        total_entities=10,
        performance={"max_workers_cap": 4, "reserve_cores": 1},
        sec_per_entity=0.0125,
        sec_per_job_overhead=0.15,
    )
    assert plan.run_in_main_process is True
    assert plan.max_workers == 1
    assert plan.entities_per_job == 10


def test_auto_picks_parallel_workers_when_beneficial():
    plan = resolve_time_dispatch_plan(
        total_entities=4109,
        performance={"max_workers_cap": 4, "reserve_cores": 1},
        sec_per_entity=0.0017,
        sec_per_job_overhead=0.15,
    )
    assert plan.run_in_main_process is False
    assert plan.max_workers >= 2
    assert plan.entities_per_job >= 1


def test_explicit_entities_per_job():
    settings = StrategyPriceSimulatorSettings.from_strategy_root(
        {
            "price_simulator": {
                "entities_per_job": 50,
                "max_workers": 2,
                "dispatch_probe": False,
                "sec_per_entity_staged": 0.002,
                "sec_per_job_overhead_staged": 0.2,
            }
        }
    )
    plan = resolve_price_dispatch_plan(
        total_stocks=200,
        config=settings,
    )
    assert plan.entities_per_job == 50
    assert plan.max_workers == 2


def test_auto_without_probe_raises():
    settings = StrategyPriceSimulatorSettings.from_strategy_root(
        {"price_simulator": {"entities_per_job": "auto", "dispatch_probe": False}}
    )
    with pytest.raises(ValueError, match="dispatch_probe"):
        resolve_price_dispatch_plan(total_stocks=100, config=settings)
