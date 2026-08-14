"""Slice probe unit tests."""
from __future__ import annotations

import pytest

from core.modules.backtest_engine.core.schedule.slice_based.probe import SliceProbe
from core.modules.backtest_engine.core.shared.jobs import BacktestJob

pytestmark = pytest.mark.force_run


def _sample_orchestrator_result() -> dict:
    return {
        "success": True,
        "performance_metrics": {
            "calendar_slice_runtime_plan": {
                "baseline_rss_mb": 100.0,
                "slice_samples": [
                    {
                        "slice_index": 0,
                        "load_sec": 0.4,
                        "compute_sec": 0.2,
                        "rss_after_mb": 180.0,
                        "payload_bytes": 40 * 1024 * 1024,
                        "payload_mb": 40.0,
                    },
                    {
                        "slice_index": 1,
                        "load_sec": 0.5,
                        "compute_sec": 0.25,
                        "rss_after_mb": 200.0,
                        "payload_bytes": 48 * 1024 * 1024,
                        "payload_mb": 48.0,
                    },
                ],
            }
        },
    }


def test_should_run_requires_hooks() -> None:
    jobs = [
        {
            "id": "j1",
            "payload": {
                "entity_ids": ["000001.SZ"],
                "timeline_point_count": 1,
            },
        }
    ]
    assert SliceProbe.should_run(jobs, {}) is False

    jobs_with_hooks = [
        {
            "id": "j1",
            "payload": {
                "entity_ids": ["000001.SZ"],
                "timeline_point_count": 1,
                "strategy_info": {"hooks_module_path": "userspace.strategies.demo.hooks"},
            },
        }
    ]
    assert SliceProbe.should_run(jobs_with_hooks, {}) is True


def test_should_run_respects_dispatch_probe_flag() -> None:
    jobs = [
        {
            "id": "j1",
            "payload": {
                "entity_ids": ["000001.SZ"],
                "timeline_point_count": 1,
                "strategy_info": {"hooks_module_path": "userspace.strategies.demo.hooks"},
            },
        }
    ]
    assert SliceProbe.should_run(jobs, {"dispatch_probe": False}) is False
    assert SliceProbe.should_run(jobs, {"slice_probe": False}) is False
    assert SliceProbe.should_run(jobs, {"preload_depth": 4}) is False
    assert SliceProbe.should_run(jobs, {"preload_depth": "auto"}) is True


def test_annotate_keeps_all_entities_and_full_calendar() -> None:
    """正式路径：annotate 保留全 entity 与完整 timeline_point_count。"""
    payload = {
        "entity_ids": ["a", "b", "c", "d"],
        "timeline_point_count": 30,
        "strategy_info": {"hooks_module_path": "x.hooks"},
    }
    out = SliceProbe.annotate_payload_for_head_sampling(
        payload,
        slice_open_days=5,
        probe_slice_count=2,
        sample_enabled=True,
    )
    assert out["entity_ids"] == ["a", "b", "c", "d"]
    assert out[BacktestJob.TIMELINE_POINT_COUNT_KEY] == 30
    assert out["_slice_head_sample_slices"] == 2
    assert out["_slice_open_days"] == 5


def test_annotate_preserves_point_count() -> None:
    payload = {
        "entity_ids": ["a", "b"],
        "timeline_point_count": 20,
    }
    out = SliceProbe.annotate_payload_for_head_sampling(
        payload,
        slice_open_days=20,
        probe_slice_count=2,
        sample_enabled=True,
    )
    assert out[BacktestJob.TIMELINE_POINT_COUNT_KEY] == 20
    assert out["_slice_head_sample_slices"] == 2


def test_extract_slice_probe_metrics_from_runtime_plan() -> None:
    metrics = SliceProbe._extract_metrics_from_plan(
        _sample_orchestrator_result(),
        safety_factor=1.0,
    )
    assert metrics["slices_sampled"] == 2.0
    assert metrics["mb_per_slice_payload"] == pytest.approx(48.0, rel=0.01)
    assert metrics["sec_per_slice_reader"] == pytest.approx(0.45, rel=0.01)
