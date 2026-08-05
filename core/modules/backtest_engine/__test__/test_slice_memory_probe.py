"""Tests for slice memory probe + live queue refine."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.modules.backtest_engine.core.schedule.slice_based.probe import SliceProbe
from core.modules.backtest_engine.core.schedule.slice_based.reader_pool import (
    SliceReaderPool,
)


def test_needs_memory_probe_when_both_missing() -> None:
    assert SliceProbe.needs_memory_probe({}) is True
    assert SliceProbe.needs_memory_probe({"probe_mb": 12.0}) is False
    assert SliceProbe.needs_memory_probe({"mb_per_open_day": 1.5}) is False


def test_measure_probe_mb_uses_window_and_rss_delta() -> None:
    jobs = [
        {
            "id": "j",
            "payload": {
                "entity_ids": ["a"],
                "entity_specified": [{"id": "a"}],
                "entity_shared": {"k": {"start": "20200101", "end": "20201231"}},
                "timeline_point_count": 40,
            },
        }
    ]
    timeline = MagicMock()
    timeline.clipped.return_value.points = [f"202401{i:02d}" for i in range(1, 31)]

    with patch(
        "core.modules.backtest_engine.core.timeline.timeline.Timeline.read_for_job",
        return_value=timeline,
    ), patch(
        "core.modules.strategy.core.services.entity_loader.job_bundle_loader.JobBundleLoader.load_per_entity_window",
        return_value={"k": object()},
    ), patch.object(SliceProbe, "_process_rss_mb", side_effect=[100.0, 125.5]):
        mb = SliceProbe.measure_probe_mb(jobs, min_required=20)

    assert mb == pytest.approx(25.5)


def test_refine_queue_from_samples_updates_live_pool() -> None:
    pool = SliceReaderPool(reader_workers=2, queue_depth=6)
    samples = [
        {"load_sec": 2.0, "compute_sec": 1.0, "payload_mb": 50.0},
        {"load_sec": 2.0, "compute_sec": 1.0, "payload_mb": 50.0},
    ]
    # n_ideal=2; n_max = floor(8000*0.8/50 - 2 - 2) = large → 2
    new_n = SliceReaderPool.refine_queue_from_samples(
        pool,
        samples,
        budget_mb=8000.0,
    )
    assert new_n == 2
    assert pool.queue_depth == 2
    pool.shutdown()
