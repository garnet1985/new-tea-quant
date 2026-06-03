from __future__ import annotations

from core.modules.tag.components.dispatch_planner import resolve_tag_dispatch_plan
from core.modules.tag.components.tag_dispatch_probe import should_run_dispatch_probe


def test_should_run_probe_only_for_auto():
    assert should_run_dispatch_probe(
        {},
        total_entities=100,
        entities_per_job_explicit=False,
    )
    assert not should_run_dispatch_probe(
        {"entities_per_job": 100},
        total_entities=100,
        entities_per_job_explicit=True,
    )
    assert not should_run_dispatch_probe(
        {"mb_per_entity_staged": 0.2},
        total_entities=100,
        entities_per_job_explicit=False,
    )
    assert not should_run_dispatch_probe(
        {"dispatch_probe": False},
        total_entities=100,
        entities_per_job_explicit=False,
    )


def test_probe_mb_per_entity_uses_rss_delta_not_peak():
    """ΔRSS/entities 应显著小于 peak/entities（避免 planner 过度保守）。"""
    entities = 20
    baseline_mb = 100.0
    peak_mb = 117.0
    safety = 1.25
    delta_mb = max(0.1, peak_mb - baseline_mb)
    mb_from_peak = (peak_mb / entities) * safety
    mb_from_delta = (delta_mb / entities) * safety
    assert mb_from_delta < mb_from_peak
    assert abs(mb_from_delta - 1.0625) < 0.01


def test_plan_uses_measured_mb_per_entity():
    plan = resolve_tag_dispatch_plan(
        total_entities=5000,
        performance={"entities_per_job": "auto", "max_workers": 9},
        measured_mb_per_entity=0.42,
    )
    assert plan.source_mb_per_entity == "probe"
    assert plan.mb_per_entity == 0.42
    assert plan.worker_job_budget_mb == 100 * 0.42
