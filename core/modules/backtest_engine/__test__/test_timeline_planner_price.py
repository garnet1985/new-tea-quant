"""Timeline planner — price_factor dispatch from strategy dispatch.yaml."""
from __future__ import annotations

import math

import pytest

from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.backtest_engine.core.shared.performance import resolve_entity_based_performance
from core.modules.backtest_engine.core.timeline_based.planner import TimelinePlanner
from core.modules.strategy.services.execution.worker_profile import (
    profile_price_factor_dispatch_config,
)


def _engine_jobs(n: int) -> list[dict]:
    return [{"id": f"s{i}", "payload": {"stock_id": f"s{i}"}} for i in range(n)]


def test_price_explicit_entities_per_job_from_dispatch() -> None:
    performance = resolve_entity_based_performance(profile_price_factor_dispatch_config())
    assert performance["entities_per_job"] == 1000
    assert performance.get("dispatch_probe") is False

    plan, batches, _monitor = TimelinePlanner.plan_jobs(
        _engine_jobs(4109),
        performance,
        executor="strategy.price",
        log_label="price",
    )

    assert plan.entities_per_job == 1000
    assert plan.dispatch_jobs == math.ceil(4109 / 1000)
    assert len(batches) == plan.dispatch_jobs
    assert sum(batch.entities_count for batch in batches) == 4109


def test_price_resolve_entities_per_job_respects_explicit_override() -> None:
    epj, source = TimelinePlanner._resolve_entities_per_job(
        total_entities=200,
        mb_per_entity=1.0,
        memory_budget_mb=3500.0,
        performance={"entities_per_job": 50},
        log_label="price",
    )
    assert epj == 50
    assert source == "settings"


def test_validate_many_rejects_flat_stock_rows() -> None:
    with pytest.raises(ValueError, match="BacktestEngine job"):
        BacktestJob.validate_many([{"stock_id": "000001.SZ"}])
