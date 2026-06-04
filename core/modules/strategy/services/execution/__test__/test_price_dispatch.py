from __future__ import annotations

import math

import pytest

from core.infra.worker.dispatch_time_planner import resolve_time_dispatch_plan
from core.modules.strategy.engines.simulator.price_factor.data_classes.settings import (
    DEFAULT_PRICE_ENTITIES_PER_JOB,
    StrategyPriceSimulatorSettings,
)
from core.modules.strategy.services.execution.price_dispatch import (
    resolve_price_dispatch_plan,
)


def test_default_entities_per_job_and_pool_workers():
    settings = StrategyPriceSimulatorSettings.from_strategy_root({})
    settings.validate()
    assert settings.entities_per_job == DEFAULT_PRICE_ENTITIES_PER_JOB
    plan = resolve_price_dispatch_plan(total_stocks=4109, config=settings)
    assert plan.entities_per_job == 1000
    assert plan.dispatch_jobs == math.ceil(4109 / 1000)
    assert 1 <= plan.max_workers <= plan.dispatch_jobs
    assert plan.run_in_main_process is False


def test_explicit_entities_per_job_plan():
    settings = StrategyPriceSimulatorSettings.from_strategy_root(
        {"price_simulator": {"entities_per_job": 50}}
    )
    plan = resolve_price_dispatch_plan(total_stocks=200, config=settings)
    assert plan.entities_per_job == 50
    assert plan.dispatch_jobs == 4
    assert plan.max_workers <= 4


def test_legacy_max_workers_in_settings_is_ignored():
    from unittest.mock import patch

    from core.infra.job_pipeline.probe import WorkerProbe

    settings = StrategyPriceSimulatorSettings.from_strategy_root(
        {
            "price_simulator": {
                "entities_per_job": 50,
                "max_workers": 2,
            }
        }
    )
    report = settings.validate()
    assert any("worker.json" in (w.get("message") or "") for w in report.warnings)
    with patch.object(WorkerProbe, "resolve", return_value=9):
        plan = resolve_price_dispatch_plan(total_stocks=200, config=settings)
    assert plan.dispatch_jobs == 4
    assert plan.max_workers == 4


def test_auto_mode_uses_time_planner_without_cap():
    plan = resolve_time_dispatch_plan(
        total_entities=4109,
        performance={"reserve_cores": 1},
        sec_per_entity=0.0017,
        sec_per_job_overhead=0.15,
    )
    assert plan.run_in_main_process is False
    assert plan.max_workers >= 2


def test_auto_without_probe_raises():
    settings = StrategyPriceSimulatorSettings.from_strategy_root(
        {"price_simulator": {"entities_per_job": "auto", "dispatch_probe": False}}
    )
    with pytest.raises(ValueError, match="dispatch_probe"):
        resolve_price_dispatch_plan(total_stocks=100, config=settings)
