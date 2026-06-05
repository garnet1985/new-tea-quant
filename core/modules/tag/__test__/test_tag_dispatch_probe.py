from __future__ import annotations

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
