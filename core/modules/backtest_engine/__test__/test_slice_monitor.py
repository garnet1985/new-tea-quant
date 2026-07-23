"""Slice run monitor unit tests."""
from __future__ import annotations

from core.modules.backtest_engine.core.shared.types import JobReport
from core.modules.backtest_engine.core.schedule.slice_based.monitor import (
    SliceMonitorConfig,
    SliceMonitorPlanSnapshot,
    SliceProgressSample,
    SliceRunMonitor,
)


def _plan_snapshot() -> SliceMonitorPlanSnapshot:
    return SliceMonitorPlanSnapshot(
        reader_workers=2,
        queue_capacity=4,
        preload_depth=2,
        slice_open_days=20,
        dispatch_slices=10,
        reader_memory_budget_mb=80.0,
        compute_memory_budget_mb=30.0,
        payload_memory_budget_mb=20.0,
        memory_budget_mb=4096.0,
    )


def _orchestrator_report(*, slices: int = 6) -> JobReport:
    samples = []
    for index in range(slices):
        samples.append(
            {
                "slice_index": index,
                "load_sec": 0.4,
                "compute_sec": 0.2,
                "rss_after_mb": 500.0 + index * 10,
                "payload_mb": 40.0,
            }
        )
    return JobReport(
        job_id="calendar_slice",
        success=True,
        data={
            "performance_metrics": {
                "calendar_slice_runtime_plan": {
                    "baseline_rss_mb": 100.0,
                    "reader_workers": 2,
                    "current_preload_depth": 2,
                    "slice_samples": samples,
                }
            }
        },
    )


def test_record_from_job_report_aggregates_slices() -> None:
    monitor = SliceRunMonitor(
        _plan_snapshot(),
        SliceMonitorConfig(evaluation_slice_interval=3, warmup_slices=0),
        available_memory_mb=1000.0,
    )
    monitor.record_from_job_report(_orchestrator_report(slices=6))
    monitor.flush()
    stats = monitor.stats
    assert stats.completed_slices == 6
    assert stats.peak_rss_mb == 550.0
    assert stats.mb_per_slice_payload_hat == 40.0
    assert stats.runtime_preload_depth == 2
    assert len(stats.slice_samples) == 6


def test_memory_pressure_recommends_lower_preload() -> None:
    monitor = SliceRunMonitor(
        _plan_snapshot(),
        SliceMonitorConfig(
            evaluation_slice_interval=2,
            warmup_slices=0,
            memory_high_watermark=0.10,
        ),
        available_memory_mb=100.0,
    )
    for index in range(4):
        monitor.record(
            SliceProgressSample(
                slice_index=index,
                load_sec=0.5,
                compute_sec=0.2,
                rss_after_mb=200.0,
                payload_mb=50.0,
            )
        )
    monitor.flush()
    assert monitor.stats.memory_pressure_detected is True
    assert monitor.stats.recommended_preload_depth == 1


def test_warmup_skips_memory_policy() -> None:
    monitor = SliceRunMonitor(
        _plan_snapshot(),
        SliceMonitorConfig(evaluation_slice_interval=2, warmup_slices=5),
        available_memory_mb=100.0,
    )
    for index in range(4):
        monitor.record(
            SliceProgressSample(
                slice_index=index,
                load_sec=0.5,
                compute_sec=0.2,
                rss_after_mb=500.0,
                payload_mb=50.0,
            )
        )
    monitor.flush()
    assert monitor.stats.evaluation_count == 0
    assert monitor.stats.memory_pressure_detected is False
