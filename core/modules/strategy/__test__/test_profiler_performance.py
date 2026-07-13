"""ReportManager.profiler 门面单元测试。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from core.modules.backtest_engine.core.shared.profiler import (
    ENGINE_PERF_KEY,
    ENUM_PERF_KEY,
)
from core.modules.strategy.core.engines.enumerator.shared.report_manager import (
    ReportManager,
)


@dataclass
class _FakeJobReport:
    job_id: str
    success: bool
    data: Dict[str, Any] | None = None
    error: str = ""


@dataclass
class _FakeRunResult:
    elapsed_seconds: float = 10.0
    total_jobs: int = 2
    completed_jobs: int = 2
    failed_jobs: int = 0
    job_results: List[Any] | None = None
    plan: Any = None
    monitor_stats: Any = None


def test_profiler_summary_default_omits_jobs(tmp_path: Path) -> None:
    manager = ReportManager.open(tmp_path, strategy_key="demo", version_id=1)
    manager.profiler.begin_collect(entity_count=4)
    manager.profiler.collect(
        _FakeJobReport(
            job_id="job-1",
            success=True,
            data={
                ENGINE_PERF_KEY: {"init_sec": 0.2, "execute_sec": 1.0, "complete_sec": 0.3},
                ENUM_PERF_KEY: {"phases": {"load_data": 0.4, "enumerate": 0.5, "flush_csv": 0.1}},
            },
        )
    )
    manager.profiler.collect(
        _FakeJobReport(
            job_id="job-2",
            success=True,
            data={
                ENGINE_PERF_KEY: {"init_sec": 0.1, "execute_sec": 0.8, "complete_sec": 0.2},
                ENUM_PERF_KEY: {"phases": {"load_data": 0.3, "enumerate": 0.4, "flush_csv": 0.05}},
            },
        )
    )
    manager.profiler.build_from_run(
        _FakeRunResult(),
        entity_count=4,
        opportunities_count=4,
    )
    perf_path = manager.profiler.save()
    payload = manager.profiler.load()
    summary = payload["summary"]

    assert perf_path.name == "0_performance.json"
    assert "jobs" not in payload
    assert summary["opportunities_count"] == 4
    phase_totals = summary["phase_totals_sec"]
    assert phase_totals["engine_init"] == 0.3
    assert phase_totals["engine_execute"] == 1.8


def test_profiler_full_includes_jobs(tmp_path: Path) -> None:
    manager = ReportManager.open(tmp_path, strategy_key="demo", version_id=1)
    manager.profiler.begin_collect(entity_count=4)
    manager.profiler.collect(
        _FakeJobReport(
            job_id="job-1",
            success=True,
            data={
                ENGINE_PERF_KEY: {"init_sec": 0.2, "execute_sec": 1.0, "complete_sec": 0.3},
                ENUM_PERF_KEY: {"phases": {"enumerate": 0.5}},
            },
        )
    )
    manager.profiler.build_from_run(
        _FakeRunResult(total_jobs=1, completed_jobs=1),
        entity_count=4,
        opportunities_count=3,
        performance_config={"performance_detail": "full"},
    )
    manager.profiler.save()
    payload = manager.profiler.load()
    assert len(payload["jobs"]) == 1
    assert payload["jobs"][0]["engine_perf"]["execute_sec"] == 1.0


def test_profiler_full_records_failed_job(tmp_path: Path) -> None:
    manager = ReportManager.open(tmp_path, strategy_key="demo", version_id=1)
    manager.profiler.begin_collect(entity_count=1)
    manager.profiler.collect(
        _FakeJobReport(
            job_id="j",
            success=False,
            error="boom",
            data={
                ENGINE_PERF_KEY: {"init_sec": 0.1, "execute_sec": 0.0, "complete_sec": 0.0},
                ENUM_PERF_KEY: {"phases": {"enumerate": 0.0}},
            },
        )
    )
    manager.profiler.build_from_run(
        _FakeRunResult(total_jobs=1, completed_jobs=0, failed_jobs=1),
        entity_count=1,
        opportunities_count=0,
        performance_config={"performance_detail": "full"},
    )
    manager.profiler.save()
    job = manager.profiler.load()["jobs"][0]
    assert job["job_id"] == "j"
    assert not job["success"]
    assert job["error"] == "boom"
