"""Slice probe unit tests."""
from __future__ import annotations

import pytest

from core.modules.backtest_engine.core.slice_based.probe import SliceProbe


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
    jobs = [{"id": "j1", "payload": {"entity_ids": ["000001.SZ"], "open_dates": ["20240102"]}}]
    assert SliceProbe.should_run(jobs, {}) is False

    jobs_with_hooks = [
        {
            "id": "j1",
            "payload": {
                "entity_ids": ["000001.SZ"],
                "open_dates": ["20240102"],
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
                "open_dates": ["20240102"],
                "strategy_info": {"hooks_module_path": "userspace.strategies.demo.hooks"},
            },
        }
    ]
    assert SliceProbe.should_run(jobs, {"dispatch_probe": False}) is False
    assert SliceProbe.should_run(jobs, {"slice_probe": False}) is False
    assert SliceProbe.should_run(jobs, {"preload_depth": 4}) is False
    assert SliceProbe.should_run(jobs, {"mb_per_slice_staged": 12.0}) is False
    assert SliceProbe.should_run(jobs, {"preload_depth": "auto"}) is True


def test_build_probe_payload_keeps_all_entities() -> None:
    jobs = [
        {
            "id": "tag_calendar_slice",
            "payload": {
                "entity_ids": ["a", "b", "c", "d"],
                "open_dates": [f"202401{d:02d}" for d in range(1, 31)],
                "strategy_info": {"hooks_module_path": "x.hooks"},
            },
        }
    ]
    payload = SliceProbe.build_probe_payload(
        jobs,
        {
            "probe_slice_count": 2,
            "slice_open_days": 5,
            "probe_entity_count": 2,  # ignored — must keep full universe
        },
    )
    assert payload["entity_ids"] == ["a", "b", "c", "d"]
    assert len(payload["open_dates"]) == 10  # 2 * 5
    assert payload["_slice_head_sample_slices"] == 2
    assert payload["_slice_open_days"] == 5


def test_annotate_preserves_full_calendar() -> None:
    payload = {
        "entity_ids": ["a", "b"],
        "open_dates": [f"202401{d:02d}" for d in range(1, 21)],
    }
    out = SliceProbe.annotate_payload_for_head_sampling(
        payload,
        slice_open_days=20,
        probe_slice_count=2,
        sample_enabled=True,
    )
    assert len(out["open_dates"]) == 20
    assert out["_slice_head_sample_slices"] == 2


def test_extract_slice_probe_metrics_from_runtime_plan() -> None:
    metrics = SliceProbe._extract_metrics_from_plan(
        _sample_orchestrator_result(),
        safety_factor=1.0,
    )
    assert metrics["slices_sampled"] == 2.0
    assert metrics["mb_per_slice_payload"] == pytest.approx(48.0, rel=0.01)
    assert metrics["sec_per_slice_reader"] == pytest.approx(0.45, rel=0.01)
    assert metrics["sec_per_slice_compute"] == pytest.approx(0.225, rel=0.01)


def test_result_from_execute_report() -> None:
    result = SliceProbe.result_from_execute_report(
        _sample_orchestrator_result(),
        performance={},
        safety_factor=1.0,
    )
    assert result.slices_sampled == 2
    assert result.sec_per_slice_reader > 0
