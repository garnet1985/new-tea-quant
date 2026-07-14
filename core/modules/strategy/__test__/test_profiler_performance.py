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
                ENUM_PERF_KEY: {
                    "phases": {
                        "load_data": 0.4,
                        "enumerate": 0.5,
                        "flush_csv": 0.1,
                        "enum_pit_until": 0.2,
                        "enum_contract_until": 0.18,
                        "enum_scan": 0.15,
                        "enum_context_fill": 0.05,
                        "enum_process_tick": 0.02,
                        "load_contract_issue": 0.3,
                        "load_apply_indicators": 0.05,
                    },
                    "storage": {
                        "load_calls": 4,
                        "load_time_seconds": 0.35,
                        "loads_by_slot": {"stock.kline.daily": 0.2},
                    },
                    "contract": {
                        "until_calls": 120,
                        "until_time_seconds": 0.18,
                        "until_by_slot": {"stock.kline.daily": 0.1},
                    },
                },
            },
        )
    )
    manager.profiler.collect(
        _FakeJobReport(
            job_id="job-2",
            success=True,
            data={
                ENGINE_PERF_KEY: {"init_sec": 0.1, "execute_sec": 0.8, "complete_sec": 0.2},
                ENUM_PERF_KEY: {
                    "phases": {
                        "load_data": 0.3,
                        "enumerate": 0.4,
                        "flush_csv": 0.05,
                        "enum_pit_until": 0.1,
                        "enum_contract_until": 0.09,
                        "enum_scan": 0.08,
                        "enum_context_fill": 0.03,
                        "enum_process_tick": 0.01,
                        "load_contract_issue": 0.25,
                        "load_apply_indicators": 0.03,
                    },
                    "storage": {
                        "load_calls": 4,
                        "load_time_seconds": 0.25,
                        "loads_by_slot": {"stock.kline.daily": 0.15},
                    },
                    "contract": {
                        "until_calls": 80,
                        "until_time_seconds": 0.09,
                        "until_by_slot": {"stock.kline.daily": 0.05},
                    },
                },
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
    assert phase_totals["enum_pit_until"] == 0.3
    assert phase_totals["enum_contract_until"] == 0.27
    assert phase_totals["enum_scan"] == 0.23
    assert phase_totals["load_contract_issue"] == 0.55
    assert phase_totals["load_apply_indicators"] == 0.08
    storage_totals = summary["storage_totals"]
    assert storage_totals["load_calls"] == 8
    assert storage_totals["load_time_seconds"] == 0.6
    assert storage_totals["loads_by_slot"]["stock.kline.daily"] == 0.35
    contract_totals = summary["contract_totals"]
    assert contract_totals["until_calls"] == 200
    assert contract_totals["until_time_seconds"] == 0.27
    assert contract_totals["until_by_slot"]["stock.kline.daily"] == 0.15

    v1 = summary["v1_compat"]
    assert v1["wall_clock_seconds"] == 10.0
    assert v1["job_batch_hydrate_seconds"] == 0.63
    assert v1["sum_worker_total_seconds"] == 0.79
    assert v1["parallelism_factor"] == 0.08
    assert v1["worker_phase_sums_seconds"]["enumerate"] == 0.64
    assert v1["worker_phase_sums_seconds"]["save_csv"] == 0.15
    assert v1["worker_phase_sums_seconds"]["load_contracts"] == 0.0
    assert v1["storage"]["sum_load_time_seconds"] == 0.6


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
