"""ReportManager.profiler 门面单元测试。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from core.modules.backtest_engine.core.performance.profiler import (
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
class _FakeProbe:
    entities_sampled: int = 5
    peak_rss_mb: float = 200.0
    mb_per_entity: float = 8.0
    sec_per_entity: float = 0.5
    pickle_bytes: int = 1024
    wall_sec: float = 2.5


@dataclass
class _FakeEntityPlan:
    entities_per_job: int = 20
    max_workers: int = 4
    dispatch_jobs: int = 2
    prefetch_ahead: int = 1
    memory_budget_mb: float = 1000.0
    worker_job_budget_mb: float = 50.0
    source_entities_per_job: str = "auto"
    source_max_workers: str = "auto"
    probe: Any = None


@dataclass
class _FakeRunResult:
    elapsed_seconds: float = 10.0
    total_jobs: int = 2
    completed_jobs: int = 2
    failed_jobs: int = 0
    job_results: List[Any] | None = None
    plan: Any = None
    monitor_stats: Any = None
    pipeline_phases_sec: Dict[str, float] | None = None


def _sample_jobs() -> List[_FakeJobReport]:
    return [
        _FakeJobReport(
            job_id="job-1",
            success=True,
            data={
                "entities_count": 2,
                "wall_sec": 1.5,
                "peak_rss_mb": 40.0,
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
        ),
        _FakeJobReport(
            job_id="job-2",
            success=True,
            data={
                "entities_count": 2,
                "wall_sec": 1.1,
                "peak_rss_mb": 36.0,
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
        ),
    ]


def test_profiler_summary_default_omits_jobs(tmp_path: Path) -> None:
    manager = ReportManager.open(tmp_path, strategy_key="demo", version_id=1)
    manager.profiler.begin_collect(entity_count=4)
    for report in _sample_jobs():
        manager.profiler.collect(report)
    manager.profiler.build_from_run(
        _FakeRunResult(
            plan=_FakeEntityPlan(probe=_FakeProbe()),
            pipeline_phases_sec={
                "prep": 0.1,
                "plan": 1.2,
                "execute": 10.0,
                "finish": 0.05,
                "wall": 11.35,
            },
        ),
        entity_count=4,
        opportunities_count=4,
    )
    perf_path = manager.profiler.save()
    payload = manager.profiler.load()
    summary = payload["summary"]
    planner = payload["planner"]
    child = payload["child_process"]

    assert perf_path.name == "0_performance.json"
    assert payload["mode"] == "entity_based"
    assert "execution_mode" not in payload
    assert "dispatch" not in payload
    assert "runtime" not in payload
    assert "jobs" not in payload
    assert "mode" not in planner
    assert "v1_compat" not in child

    glance = payload["quick_summary"]
    assert glance["total_sec_spent"] == 11.35
    assert glance["saved_sec"] == round(1.5 + 1.1 - 10.0, 2)
    assert glance["parallelism"] == 0.26
    assert glance["parallelism_efficiency"] == 0.065
    assert glance["total_entity"] == 4
    assert glance["job_batches"]["total"] == 2
    assert glance["job_batches"]["success"] == 2
    assert glance["job_batches"]["success_rate"] == 1.0
    assert glance["plan"]["worker"] == 4
    assert glance["plan"]["entity_per_job"] == 20
    assert "saved_sec" not in glance["plan"]
    assert "parallelism" not in glance["plan"]
    assert glance["process_capacity"]["entity_per_sec"] > 0
    assert glance["process_capacity"]["mb_per_sec"] > 0
    # FakeProbe peak=200, n=5, buffer=0 → entity est=40；epj=20 → worker=800
    pe = glance["memory"]["per_entity"]
    assert glance["memory"]["unit"] == "MB"
    assert glance["memory"]["overall_available"] == 1000.0
    assert abs(float(pe["estimated"]) - 40.0) < 0.01
    assert pe["buffer_rate"] == 0.0
    assert pe["estimate_accuracy"] is not None
    assert pe["peak_overshoot"] is not None
    assert "peak_OOM_rate" not in pe
    wk = glance["memory"]["worker"]
    assert abs(float(wk["estimated"]) - 800.0) < 0.01
    cc = glance["memory"]["concurrent"]
    assert abs(float(cc["estimated"]) - 3200.0) < 0.01
    assert glance["memory"]["avg_usage_rate"] is not None
    assert glance["probe_status"] == "ran"
    td = glance["time_distribution"]
    assert td["unit"] == "sec"
    assert "planning" in td and "load_data" in td and "compute" in td and "report" in td
    assert abs(float(td["planning"]["sec"]) - 1.3) < 0.01  # prep 0.1 + plan 1.2
    assert float(td["load_data"]["pct"]) + float(td["compute"]["pct"]) > 0
    assert "time_share" not in glance

    assert "estimates" not in planner["probe"]
    assert "accuracy" not in planner["probe"]
    assert planner["probe"]["status"] == "ran"
    assert planner["probe"]["detail"]["entities_sampled"] == 5

    assert summary["opportunities_count"] == 4
    assert "elapsed_seconds" not in summary
    assert "parallelism_factor" not in summary
    assert "at_a_glance" not in payload

    assert child["total"]["init_sec"] == 0.3
    assert child["total"]["execute_sec"] == 1.8
    staged = child["staged"]
    assert staged["init"] == 0.3
    assert staged["load_data"] == 0.7
    assert staged["enumerate"] == 0.9
    assert staged["enum_pit_until"] == 0.3
    assert staged["enum_contract_until"] == 0.27
    assert staged["enum_scan"] == 0.23
    assert staged["load_contract_issue"] == 0.55
    assert staged["load_apply_indicators"] == 0.08
    detail = child["detail"]
    assert detail["storage"]["load_calls"] == 8
    assert detail["storage"]["load_time_seconds"] == 0.6
    assert detail["contract"]["until_calls"] == 200
    assert detail["cold_start"]["first_job_wall_sec"] == 1.5
    assert detail["failures"]["failed_jobs"] == 0
    assert detail["memory"]["per_process_peak_rss_mb_median"] > 0
    assert detail["memory"]["estimated_concurrent_rss_mb"] > 0


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
    assert payload["performance_config"]["performance_detail"] == "full"


def test_dispatch_plan_snapshot_entity_and_slice() -> None:
    from core.modules.strategy.core.engines.enumerator.shared.report_manager.profiler import (
        DispatchPlanSnapshot,
    )

    @dataclass
    class _EntityPlan:
        entities_per_job: int = 20
        max_workers: int = 8
        dispatch_jobs: int = 10
        prefetch_ahead: int = 1
        memory_budget_mb: float = 1000.0
        worker_job_budget_mb: float = 50.0
        source_entities_per_job: str = "settings"
        source_max_workers: str = "auto"

    @dataclass
    class _SlicePlan:
        reader_workers: int = 4
        reader_memory_budget_mb: float = 200.0
        compute_processes: int = 1
        compute_memory_budget_mb: float = 300.0
        queue_capacity: int = 8
        preload_depth: int = 2
        slice_open_days: int = 20
        dispatch_jobs: int = 37
        memory_budget_mb: float = 1000.0
        oom_adjusted: bool = False
        probe: dict = None

        def __post_init__(self):
            if self.probe is None:
                self.probe = {
                    "ran": True,
                    "slices_sampled": 2,
                    "sec_per_slice_reader": 0.4,
                    "sec_per_slice_compute": 0.1,
                    "mb_per_slice_reader": 10.0,
                    "mb_per_slice_compute": 15.0,
                    "mb_per_slice_payload": 5.0,
                    "peak_rss_mb_reader": 40.0,
                    "peak_rss_mb_compute": 50.0,
                    "wall_sec": 1.0,
                }

    entity = DispatchPlanSnapshot.from_plan(_EntityPlan())
    assert entity.mode == "entity_based"
    assert entity.entities_per_job == 20
    assert entity.max_workers == 8
    entity_dict = entity.to_dict()
    assert "mode" not in entity_dict
    assert "reader_workers" not in entity_dict
    assert "probe" in entity_dict

    slice_snap = DispatchPlanSnapshot.from_plan(_SlicePlan())
    assert slice_snap.mode == "slice_based"
    assert slice_snap.slice_open_days == 20
    slice_dict = slice_snap.to_dict()
    assert slice_dict["total_slices"] == 37
    assert slice_dict["compute_workers"] == 1
    assert slice_dict["max_queue"] == 8
    assert slice_dict["preload_depth"] == 2
    assert "mode" not in slice_dict
    assert "max_workers" not in slice_dict
    assert slice_dict["probe"]["slices_sampled"] == 2


def test_profiler_slice_quick_summary(tmp_path: Path) -> None:
    @dataclass
    class _SliceProbe:
        ran: bool = True
        slices_sampled: int = 2
        sec_per_slice_reader: float = 0.4
        sec_per_slice_compute: float = 0.1
        mb_per_slice_reader: float = 10.0
        mb_per_slice_compute: float = 15.0
        mb_per_slice_payload: float = 5.0
        peak_rss_mb_reader: float = 40.0
        peak_rss_mb_compute: float = 55.0
        wall_sec: float = 1.0

    @dataclass
    class _SlicePlan:
        reader_workers: int = 4
        reader_memory_budget_mb: float = 80.0
        compute_processes: int = 1
        compute_memory_budget_mb: float = 15.0
        queue_capacity: int = 8
        preload_depth: int = 2
        slice_open_days: int = 20
        dispatch_jobs: int = 10
        memory_budget_mb: float = 2000.0
        oom_adjusted: bool = False
        probe: Any = None

        def __post_init__(self):
            if self.probe is None:
                self.probe = _SliceProbe()

    @dataclass
    class _SliceMonitor:
        completed_slices: int = 10
        evaluation_count: int = 1
        sec_per_slice_reader_hat: float = 0.45
        sec_per_slice_compute_hat: float = 0.12
        mb_per_slice_reader_hat: float = 11.0
        mb_per_slice_compute_hat: float = 16.0
        mb_per_slice_payload_hat: float = 5.5
        peak_rss_mb: float = 120.0

    manager = ReportManager.open(tmp_path, strategy_key="demo_slice", version_id=1)
    manager.profiler.begin_collect(entity_count=100)
    manager.profiler.collect(
        _FakeJobReport(
            job_id="bulk-1",
            success=True,
            data={
                "entities_count": 100,
                "wall_sec": 20.0,
                "peak_rss_mb": 120.0,
                ENGINE_PERF_KEY: {"init_sec": 0.1, "execute_sec": 19.0, "complete_sec": 0.1},
                ENUM_PERF_KEY: {"phases": {"load_data": 12.0, "enumerate": 7.0}},
            },
        )
    )
    manager.profiler.build_from_run(
        _FakeRunResult(
            elapsed_seconds=10.0,
            total_jobs=1,
            completed_jobs=1,
            plan=_SlicePlan(),
            monitor_stats=_SliceMonitor(),
            pipeline_phases_sec={
                "prep": 0.01,
                "plan": 0.5,
                "execute": 9.0,
                "finish": 0.1,
                "wall": 9.61,
            },
        ),
        entity_count=100,
        opportunities_count=0,
    )
    manager.profiler.save()
    payload = manager.profiler.load()
    assert payload["mode"] == "slice_based"
    glance = payload["quick_summary"]
    assert glance["total_slices"] == 10
    assert glance["plan"]["reader_workers"] == 4
    assert glance["plan"]["compute_workers"] == 1
    assert glance["plan"]["max_queue"] == 8
    assert abs(float(glance["plan"]["reader_compute_ratio"]) - 4.0) < 0.01
    assert abs(float(glance["plan"]["ideal_readers"]) - 4.0) < 0.01
    assert "plan_accuracy" in glance
    assert glance["plan_accuracy"]["estimated"]["compute_wait_for_reader_sec"] is not None
    assert "read" in glance["time_distribution"]
    assert "load_data" not in glance["time_distribution"]
    planner = payload["planner"]
    assert planner["total_slices"] == 10
    assert planner["compute_workers"] == 1
    assert planner["probe"]["status"] == "ran"


def test_overall_goal_fill_excludes_simulate_end() -> None:
    from core.modules.strategy.core.engines.enumerator.shared.report_manager.overall_report import (
        OverallReport,
    )

    assert OverallReport._is_goal_fill("stop_loss", "stop_loss")
    assert OverallReport._is_goal_fill("take_profit", "tp1")
    assert not OverallReport._is_goal_fill("simulate_end", "simulate_end")
    assert not OverallReport._is_goal_fill("expired", "expiration")


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
    payload = manager.profiler.load()
    job = payload["jobs"][0]
    assert job["job_id"] == "j"
    assert not job["success"]
    assert job["error"] == "boom"
    assert payload["child_process"]["detail"]["failures"]["failed_jobs"] == 1
    assert payload["child_process"]["detail"]["failures"]["failed_job_samples"][0]["error"] == "boom"


def test_slice_memory_estimates_from_plan_budgets_without_probe(tmp_path: Path) -> None:
    """探针跳过时，仍应用 planner budget 回填 estimated，避免一堆 null。"""

    @dataclass
    class _SlicePlanNoProbe:
        reader_workers: int = 8
        reader_memory_budget_mb: float = 160.0
        compute_processes: int = 1
        compute_memory_budget_mb: float = 15.0
        queue_capacity: int = 8
        preload_depth: int = 2
        slice_open_days: int = 20
        dispatch_jobs: int = 37
        memory_budget_mb: float = 6144.0
        oom_adjusted: bool = False
        probe: dict | None = None

    manager = ReportManager.open(tmp_path, strategy_key="demo_slice_defaults", version_id=1)
    manager.profiler.begin_collect(entity_count=500)
    manager.profiler.collect(
        _FakeJobReport(
            job_id="bulk-1",
            success=True,
            data={
                "entities_count": 500,
                "wall_sec": 11.0,
                "peak_rss_mb": 540.0,
                ENGINE_PERF_KEY: {"init_sec": 0.0, "execute_sec": 11.0, "complete_sec": 0.0},
            },
        )
    )
    manager.profiler.build_from_run(
        _FakeRunResult(
            elapsed_seconds=11.0,
            total_jobs=1,
            completed_jobs=1,
            plan=_SlicePlanNoProbe(),
            pipeline_phases_sec={
                "prep": 0.0,
                "plan": 0.01,
                "execute": 11.0,
                "finish": 0.0,
                "wall": 11.01,
            },
        ),
        entity_count=500,
        opportunities_count=0,
    )
    manager.profiler.save()
    payload = manager.profiler.load()
    mem = payload["quick_summary"]["memory"]
    assert mem["estimate_source"] == "plan_defaults"
    assert abs(float(mem["per_slice"]["reader"]["estimated"]) - 10.0) < 0.01
    assert abs(float(mem["per_slice"]["compute"]["estimated"]) - 15.0) < 0.01
    assert abs(float(mem["per_slice"]["payload"]["estimated"]) - 5.0) < 0.01
    assert abs(float(mem["concurrent"]["reader"]["estimated"]) - 160.0) < 0.01
    assert abs(float(mem["concurrent"]["compute"]["estimated"]) - 15.0) < 0.01
    assert abs(float(mem["concurrent"]["payload"]["estimated"]) - 40.0) < 0.01
    assert mem["concurrent"]["total"]["estimated"] is not None
    assert payload["quick_summary"]["probe_status"] == "defaults"
