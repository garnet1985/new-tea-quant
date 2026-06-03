from __future__ import annotations

from unittest.mock import patch

from core.modules.tag.components.dispatch_planner import resolve_tag_dispatch_plan


def test_explicit_entities_per_job():
    plan = resolve_tag_dispatch_plan(
        total_entities=500,
        performance={"entities_per_job": 50, "max_workers": 4},
    )
    assert plan.entities_per_job == 50
    assert plan.dispatch_jobs == 10
    assert plan.max_workers == 4
    assert plan.source_entities_per_job == "settings"


@patch(
    "core.modules.tag.components.dispatch_planner._get_available_memory_mb",
    return_value=8192.0,
)
def test_auto_entities_and_memory_cap_workers(mock_avail):
    plan = resolve_tag_dispatch_plan(
        total_entities=5000,
        performance={
            "entities_per_job": "auto",
            "max_workers": "auto",
            "reserve_cores": 1,
            "mb_per_entity_staged": 0.25,
            "worker_memory_fraction": 0.65,
            "main_process_reserve_mb": 512,
        },
    )
    assert plan.source_entities_per_job == "auto"
    assert 10 <= plan.entities_per_job <= 100
    assert plan.max_workers >= 1
    assert plan.dispatch_jobs == (5000 + plan.entities_per_job - 1) // plan.entities_per_job


@patch(
    "core.modules.tag.components.dispatch_planner._get_available_memory_mb",
    return_value=None,
)
def test_no_psutil_falls_back_budget(mock_avail):
    plan = resolve_tag_dispatch_plan(
        total_entities=100,
        performance={"entities_per_job": "auto"},
    )
    assert plan.entities_per_job >= 10
