"""Slice probe unit tests."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from core.modules.backtest_engine.core.slice_based.probe import (
    PROBE_EXECUTOR_TAG,
    SliceProbe,
)


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


def test_should_run_requires_worker_for_tag() -> None:
    jobs = [{"id": "j1", "payload": {"entity_ids": ["000001.SZ"], "open_dates": ["20240102"]}}]
    assert SliceProbe.should_run(jobs, {}) is False

    jobs_with_worker = [
        {
            "id": "j1",
            "payload": {
                "entity_ids": ["000001.SZ"],
                "open_dates": ["20240102"],
                "worker_module_path": "userspace.extensions.tags.demo.tag_worker",
            },
        }
    ]
    assert SliceProbe.should_run(jobs_with_worker, {}) is True


def test_should_run_respects_slice_probe_flag() -> None:
    jobs = [
        {
            "id": "j1",
            "payload": {
                "entity_ids": ["000001.SZ"],
                "open_dates": ["20240102"],
                "worker_module_path": "userspace.extensions.tags.demo.tag_worker",
            },
        }
    ]
    assert SliceProbe.should_run(jobs, {"slice_probe": False}) is False


def test_build_probe_payload_truncates_open_dates_and_entities() -> None:
    jobs = [
        {
            "id": "tag_calendar_slice",
            "payload": {
                "tag_execution_mode": "calendar_slice",
                "entity_ids": ["a", "b", "c", "d"],
                "open_dates": [f"202401{d:02d}" for d in range(1, 31)],
                "slice_open_days": "auto",
            },
        }
    ]
    payload = SliceProbe.build_probe_payload(
        jobs,
        {
            "probe_slice_count": 2,
            "probe_slice_open_days": 5,
            "probe_entity_count": 2,
        },
    )
    assert payload["_slice_probe"] is True
    assert payload["_probe_max_slices"] == 2
    assert payload["_probe_slice_open_days"] == 5
    assert payload["entity_ids"] == ["a", "b"]
    assert len(payload["open_dates"]) == 10


def test_extract_slice_probe_metrics_from_runtime_plan() -> None:
    metrics = SliceProbe._extract_metrics_from_plan(
        _sample_orchestrator_result(),
        safety_factor=1.0,
    )
    assert metrics["slices_sampled"] == 2.0
    assert metrics["mb_per_slice_payload"] == pytest.approx(48.0, rel=0.01)
    assert metrics["sec_per_slice_reader"] == pytest.approx(0.45, rel=0.01)
    assert metrics["sec_per_slice_compute"] == pytest.approx(0.225, rel=0.01)
    assert metrics["mb_per_slice_reader"] > 0
    assert metrics["mb_per_slice_compute"] > 0


def test_dispatch_uses_subprocess_and_builds_result() -> None:
    probe_jobs = [
        {
            "id": "probe",
            "payload": SliceProbe.build_probe_payload(
                [{"id": "j1", "payload": {"entity_ids": ["000001.SZ"], "open_dates": ["20240102"]}}],
                {},
            ),
        }
    ]
    raw = {
        "success": True,
        "wall_sec": 1.5,
        "orchestrator_result": _sample_orchestrator_result(),
    }
    with patch.object(SliceProbe, "_run_probe_in_subprocess", return_value=raw):
        result = SliceProbe.dispatch(
            probe_jobs,
            executor=PROBE_EXECUTOR_TAG,
            performance={},
            log_label="test",
        )
    assert result.slices_sampled == 2
    assert result.mb_per_slice_payload > 0


def test_extract_metrics_requires_samples() -> None:
    with pytest.raises(RuntimeError, match="no slice_samples"):
        SliceProbe._extract_metrics_from_plan(
            {"success": True, "performance_metrics": {}},
            safety_factor=1.0,
        )
