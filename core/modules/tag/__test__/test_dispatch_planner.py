from __future__ import annotations

from unittest.mock import patch

from core.infra.worker.dispatch_planner import resolve_dispatch_plan


def test_explicit_entities_per_job():
    plan = resolve_dispatch_plan(
        total_entities=500,
        performance={
            "entities_per_job": 50,
            "mb_per_entity_staged": 0.5,
        },
        log_label="Tag",
    )
    assert plan.entities_per_job == 50
    assert plan.dispatch_jobs == 10
    assert plan.max_workers >= 1
    assert plan.source_max_workers.startswith("profile")
    assert plan.source_entities_per_job == "settings"


@patch(
    "core.infra.worker.dispatch_planner._get_virtual_memory_mb",
    return_value=(16384.0, 8192.0),
)
def test_auto_entities_with_probe_mb(mock_vm):
    plan = resolve_dispatch_plan(
        total_entities=5000,
        performance={
            "entities_per_job": "auto",
            "memory_floor_mb": 1024,
            "worker_memory_fraction": 0.85,
        },
        log_label="Tag",
        measured_mb_per_entity=0.42,
    )
    assert plan.source_entities_per_job == "auto"
    assert plan.source_mb_per_entity == "probe"
    assert plan.memory_floor_mb == 1024.0
    assert 1 <= plan.entities_per_job <= 500


@patch(
    "core.infra.worker.dispatch_planner._get_virtual_memory_mb",
    return_value=(None, None),
)
def test_auto_requires_probe_or_staged(mock_vm):
    import pytest

    with pytest.raises(ValueError, match="探针"):
        resolve_dispatch_plan(
            total_entities=100,
            performance={"entities_per_job": "auto"},
            log_label="test",
        )
