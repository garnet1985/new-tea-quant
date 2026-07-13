"""枚举 run 性能快照：汇总调度与 job 指标，落盘 performance.json。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.enumerator.shared.report_manager.report_manager import (
        ReportManager,
    )

from core.modules.backtest_engine.core.entity_based.monitor import EntityMonitorStats
from core.modules.backtest_engine.core.shared.profiler import (
    ENGINE_PERF_KEY,
    ENUM_PERF_KEY,
    WorkerTaskPerf,
)
from core.modules.strategy.core.engines.enumerator.shared.report_manager.report_consts import (
    PERFORMANCE_DETAIL_FULL,
    PERFORMANCE_FILE,
    resolve_performance_detail,
)


@dataclass
class DispatchPlanSnapshot:
    entities_per_job: int = 0
    max_workers: int = 0
    dispatch_jobs: int = 0
    prefetch_ahead: int = 0
    memory_budget_mb: float = 0.0
    worker_job_budget_mb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities_per_job": self.entities_per_job,
            "max_workers": self.max_workers,
            "dispatch_jobs": self.dispatch_jobs,
            "prefetch_ahead": self.prefetch_ahead,
            "memory_budget_mb": self.memory_budget_mb,
            "worker_job_budget_mb": self.worker_job_budget_mb,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "DispatchPlanSnapshot":
        data = raw or {}
        return cls(
            entities_per_job=int(data.get("entities_per_job") or 0),
            max_workers=int(data.get("max_workers") or 0),
            dispatch_jobs=int(data.get("dispatch_jobs") or 0),
            prefetch_ahead=int(data.get("prefetch_ahead") or 0),
            memory_budget_mb=float(data.get("memory_budget_mb") or 0.0),
            worker_job_budget_mb=float(data.get("worker_job_budget_mb") or 0.0),
        )

    @classmethod
    def from_plan(cls, plan: Any) -> "DispatchPlanSnapshot":
        if plan is None:
            return cls()
        return cls(
            entities_per_job=int(getattr(plan, "entities_per_job", 0) or 0),
            max_workers=int(getattr(plan, "max_workers", 0) or 0),
            dispatch_jobs=int(getattr(plan, "dispatch_jobs", 0) or 0),
            prefetch_ahead=int(getattr(plan, "prefetch_ahead", 0) or 0),
            memory_budget_mb=float(getattr(plan, "memory_budget_mb", 0.0) or 0.0),
            worker_job_budget_mb=float(getattr(plan, "worker_job_budget_mb", 0.0) or 0.0),
        )


@dataclass
class MonitorStatsSnapshot:
    completed_jobs: int = 0
    completed_entities: int = 0
    evaluation_count: int = 0
    current_in_flight: int = 0
    mb_per_entity_hat: float = 0.0
    wall_per_entity_hat: float = 0.0
    sunk_cost_sec_hat: float = 0.0
    margin_cost_sec_per_entity_hat: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "completed_jobs": self.completed_jobs,
            "completed_entities": self.completed_entities,
            "evaluation_count": self.evaluation_count,
            "current_in_flight": self.current_in_flight,
            "mb_per_entity_hat": self.mb_per_entity_hat,
            "wall_per_entity_hat": self.wall_per_entity_hat,
            "sunk_cost_sec_hat": self.sunk_cost_sec_hat,
            "margin_cost_sec_per_entity_hat": self.margin_cost_sec_per_entity_hat,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "MonitorStatsSnapshot":
        data = raw or {}
        return cls(
            completed_jobs=int(data.get("completed_jobs") or 0),
            completed_entities=int(data.get("completed_entities") or 0),
            evaluation_count=int(data.get("evaluation_count") or 0),
            current_in_flight=int(data.get("current_in_flight") or 0),
            mb_per_entity_hat=float(data.get("mb_per_entity_hat") or 0.0),
            wall_per_entity_hat=float(data.get("wall_per_entity_hat") or 0.0),
            sunk_cost_sec_hat=float(data.get("sunk_cost_sec_hat") or 0.0),
            margin_cost_sec_per_entity_hat=float(
                data.get("margin_cost_sec_per_entity_hat") or 0.0
            ),
        )

    @classmethod
    def from_stats(cls, stats: Any) -> "MonitorStatsSnapshot":
        if stats is None:
            return cls()
        if isinstance(stats, EntityMonitorStats):
            return cls(
                completed_jobs=stats.completed_jobs,
                completed_entities=stats.completed_entities,
                evaluation_count=stats.evaluation_count,
                current_in_flight=stats.current_in_flight,
                mb_per_entity_hat=stats.mb_per_entity_hat,
                wall_per_entity_hat=stats.wall_per_entity_hat,
                sunk_cost_sec_hat=stats.sunk_cost_sec_hat,
                margin_cost_sec_per_entity_hat=stats.margin_cost_sec_per_entity_hat,
            )
        return cls.from_dict(dict(stats) if isinstance(stats, dict) else {})


@dataclass
class JobPerformance:
    job_id: str
    success: bool
    entities_count: int = 0
    opportunities_count: int = 0
    entities_with_opportunities: int = 0
    wall_sec: float = 0.0
    peak_rss_mb: float = 0.0
    error: str = ""
    engine_perf: WorkerTaskPerf = field(default_factory=WorkerTaskPerf)
    enum_perf: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "success": self.success,
            "entities_count": self.entities_count,
            "opportunities_count": self.opportunities_count,
            "entities_with_opportunities": self.entities_with_opportunities,
            "wall_sec": self.wall_sec,
            "peak_rss_mb": self.peak_rss_mb,
            "error": self.error,
            ENGINE_PERF_KEY: self.engine_perf.to_dict(),
            ENUM_PERF_KEY: dict(self.enum_perf or {}),
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "JobPerformance":
        data = raw or {}
        engine_raw = data.get(ENGINE_PERF_KEY) or {}
        enum_raw = data.get(ENUM_PERF_KEY) or {}
        return cls(
            job_id=str(data.get("job_id") or ""),
            success=bool(data.get("success", False)),
            entities_count=int(data.get("entities_count") or 0),
            opportunities_count=int(data.get("opportunities_count") or 0),
            entities_with_opportunities=int(data.get("entities_with_opportunities") or 0),
            wall_sec=float(data.get("wall_sec") or 0.0),
            peak_rss_mb=float(data.get("peak_rss_mb") or 0.0),
            error=str(data.get("error") or ""),
            engine_perf=WorkerTaskPerf.from_dict(engine_raw),
            enum_perf=dict(enum_raw) if isinstance(enum_raw, dict) else {},
        )

    @classmethod
    def from_job_report(cls, report: Any) -> "JobPerformance":
        data = report.data if isinstance(getattr(report, "data", None), dict) else {}
        peak_rss = data.get("peak_rss_mb")
        engine_raw = data.get(ENGINE_PERF_KEY) or {}
        enum_raw = data.get(ENUM_PERF_KEY) or {}
        wall_sec = float(data.get("wall_sec") or engine_raw.get("wall_sec") or 0.0)
        return cls(
            job_id=str(getattr(report, "job_id", "") or ""),
            success=bool(getattr(report, "success", False)),
            entities_count=int(data.get("entities_count") or 0),
            opportunities_count=int(data.get("opportunities_count") or 0),
            entities_with_opportunities=int(data.get("entities_with_opportunities") or 0),
            wall_sec=wall_sec,
            peak_rss_mb=float(peak_rss) if peak_rss is not None else float(
                engine_raw.get("peak_rss_mb") or 0.0
            ),
            error=str(getattr(report, "error", "") or data.get("error") or ""),
            engine_perf=WorkerTaskPerf.from_dict(engine_raw),
            enum_perf=dict(enum_raw) if isinstance(enum_raw, dict) else {},
        )


@dataclass
class SavedPerformanceArtifact:
    performance_path: Path


@dataclass
class ProfilerPerformance:
    """一次枚举 run 的性能汇总（调度 + job 墙钟 / 内存）。"""

    PERFORMANCE_FILE = PERFORMANCE_FILE

    strategy_key: str
    version_id: int
    elapsed_seconds: float
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    entity_count: int
    opportunities_count: int
    dispatch: DispatchPlanSnapshot = field(default_factory=DispatchPlanSnapshot)
    monitor: MonitorStatsSnapshot = field(default_factory=MonitorStatsSnapshot)
    performance_config: Dict[str, Any] = field(default_factory=dict)
    jobs: List[JobPerformance] = field(default_factory=list)
    created_at: str = ""

    # ── 工厂 ──

    @classmethod
    def build(
        cls,
        *,
        strategy_key: str,
        version_id: int,
        elapsed_seconds: float,
        total_jobs: int,
        completed_jobs: int,
        failed_jobs: int,
        entity_count: int,
        opportunities_count: int,
        job_results: Optional[List[Any]] = None,
        plan: Any = None,
        monitor_stats: Any = None,
        performance_config: Optional[Dict[str, Any]] = None,
    ) -> "ProfilerPerformance":
        jobs = [_coerce_job_performance(item) for item in (job_results or [])]
        return cls(
            strategy_key=str(strategy_key or ""),
            version_id=int(version_id or 0),
            elapsed_seconds=max(0.0, float(elapsed_seconds or 0.0)),
            total_jobs=max(0, int(total_jobs or 0)),
            completed_jobs=max(0, int(completed_jobs or 0)),
            failed_jobs=max(0, int(failed_jobs or 0)),
            entity_count=max(0, int(entity_count or 0)),
            opportunities_count=max(0, int(opportunities_count or 0)),
            dispatch=DispatchPlanSnapshot.from_plan(plan),
            monitor=MonitorStatsSnapshot.from_stats(monitor_stats),
            performance_config=dict(performance_config or {}),
            jobs=jobs,
            created_at=datetime.now().isoformat(),
        )

    @classmethod
    def build_from_run(
        cls,
        *,
        strategy_key: str,
        version_id: int,
        entity_count: int,
        opportunities_count: int,
        run_result: Any,
        performance_config: Optional[Dict[str, Any]] = None,
    ) -> "ProfilerPerformance":
        return cls.build(
            strategy_key=strategy_key,
            version_id=version_id,
            elapsed_seconds=float(getattr(run_result, "elapsed_seconds", 0.0) or 0.0),
            total_jobs=int(getattr(run_result, "total_jobs", 0) or 0),
            completed_jobs=int(getattr(run_result, "completed_jobs", 0) or 0),
            failed_jobs=int(getattr(run_result, "failed_jobs", 0) or 0),
            entity_count=entity_count,
            opportunities_count=opportunities_count,
            job_results=list(getattr(run_result, "job_results", []) or []),
            plan=getattr(run_result, "plan", None),
            monitor_stats=getattr(run_result, "monitor_stats", None),
            performance_config=performance_config,
        )

    @classmethod
    def load(cls, output_dir: Path) -> "ProfilerPerformance":
        path = output_dir / cls.PERFORMANCE_FILE
        if not path.is_file():
            legacy = output_dir / "performance.json"
            if legacy.is_file():
                path = legacy
        return cls.from_dict(cls._read_json(path))

    # ── 落盘 ──

    def save(self, output_dir: Path) -> SavedPerformanceArtifact:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = self._write_json(output_dir / self.PERFORMANCE_FILE, self.to_dict())
        return SavedPerformanceArtifact(performance_path=path)

    # ── 序列化 ──

    def to_dict(self) -> Dict[str, Any]:
        job_wall_sum = sum(job.wall_sec for job in self.jobs)
        entities_with_opportunities = sum(
            job.entities_with_opportunities for job in self.jobs
        )
        phase_totals = _aggregate_phase_totals(self.jobs)
        storage_totals = _aggregate_storage_totals(self.jobs)
        contract_totals = _aggregate_contract_totals(self.jobs)
        payload: Dict[str, Any] = {
            "strategy_key": self.strategy_key,
            "version_id": self.version_id,
            "created_at": self.created_at,
            "summary": {
                "elapsed_seconds": self.elapsed_seconds,
                "total_jobs": self.total_jobs,
                "completed_jobs": self.completed_jobs,
                "failed_jobs": self.failed_jobs,
                "entity_count": self.entity_count,
                "opportunities_count": self.opportunities_count,
                "entities_with_opportunities": entities_with_opportunities,
                "avg_seconds_per_job": self._avg(self.elapsed_seconds, self.completed_jobs),
                "avg_seconds_per_entity": self._avg(self.elapsed_seconds, self.entity_count),
                "opportunities_per_entity": self._avg(
                    float(self.opportunities_count),
                    self.entity_count,
                ),
                "sum_job_wall_seconds": job_wall_sum,
                "parallelism_factor": self._parallelism_factor(job_wall_sum),
                "phase_totals_sec": phase_totals,
                "storage_totals": storage_totals,
                "contract_totals": contract_totals,
            },
            "dispatch": self.dispatch.to_dict(),
            "monitor": self.monitor.to_dict(),
            "performance_config": dict(self.performance_config or {}),
        }
        if resolve_performance_detail(self.performance_config) == PERFORMANCE_DETAIL_FULL:
            payload["jobs"] = [job.to_dict() for job in self.jobs]
        return payload

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ProfilerPerformance":
        data = raw or {}
        summary = data.get("summary") or {}
        jobs_raw = data.get("jobs") or []
        return cls(
            strategy_key=str(data.get("strategy_key") or ""),
            version_id=int(data.get("version_id") or 0),
            elapsed_seconds=float(summary.get("elapsed_seconds") or 0.0),
            total_jobs=int(summary.get("total_jobs") or 0),
            completed_jobs=int(summary.get("completed_jobs") or 0),
            failed_jobs=int(summary.get("failed_jobs") or 0),
            entity_count=int(summary.get("entity_count") or 0),
            opportunities_count=int(summary.get("opportunities_count") or 0),
            dispatch=DispatchPlanSnapshot.from_dict(data.get("dispatch") or {}),
            monitor=MonitorStatsSnapshot.from_dict(data.get("monitor") or {}),
            performance_config=dict(data.get("performance_config") or {}),
            jobs=[JobPerformance.from_dict(item) for item in jobs_raw if isinstance(item, dict)],
            created_at=str(data.get("created_at") or ""),
        )

    # ── private ──

    @staticmethod
    def _avg(numerator: float, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return float(numerator) / float(denominator)

    def _parallelism_factor(self, job_wall_sum: float) -> float:
        if self.elapsed_seconds <= 0:
            return 0.0
        return round(job_wall_sum / self.elapsed_seconds, 2)

    @staticmethod
    def _write_json(path: Path, payload: Dict[str, Any]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))


class _ProfilerCollectSession:
    """主进程侧：通过 BacktestEngine on_single_task_result 收集 job 性能。"""

    def __init__(self, *, strategy_key: str, version_id: int, entity_count: int) -> None:
        self.strategy_key = str(strategy_key or "")
        self.version_id = int(version_id or 0)
        self.entity_count = max(0, int(entity_count))
        self._jobs: List[JobPerformance] = []

    def collect(self, report: Any) -> None:
        self._jobs.append(JobPerformance.from_job_report(report))

    def build(
        self,
        run_result: Any,
        *,
        opportunities_count: int,
        performance_config: Optional[Dict[str, Any]] = None,
    ) -> ProfilerPerformance:
        return ProfilerPerformance.build(
            strategy_key=self.strategy_key,
            version_id=self.version_id,
            elapsed_seconds=float(getattr(run_result, "elapsed_seconds", 0.0) or 0.0),
            total_jobs=int(getattr(run_result, "total_jobs", 0) or 0),
            completed_jobs=int(getattr(run_result, "completed_jobs", 0) or 0),
            failed_jobs=int(getattr(run_result, "failed_jobs", 0) or 0),
            entity_count=self.entity_count,
            opportunities_count=max(0, int(opportunities_count)),
            job_results=self._jobs or list(getattr(run_result, "job_results", []) or []),
            plan=getattr(run_result, "plan", None),
            monitor_stats=getattr(run_result, "monitor_stats", None),
            performance_config=performance_config,
        )


class ProfilerReport:
    """ReportManager.profiler 门面：采集 / 构建 / 落盘 performance.json。"""

    def __init__(self, manager: "ReportManager") -> None:
        self._manager = manager
        self._session: Optional[_ProfilerCollectSession] = None
        self._snapshot: Optional[ProfilerPerformance] = None

    def begin_collect(self, *, entity_count: int) -> None:
        self._session = _ProfilerCollectSession(
            strategy_key=self._manager.strategy_key,
            version_id=self._manager.version_id,
            entity_count=entity_count,
        )

    def collect(self, report: Any) -> None:
        if self._session is None:
            self.begin_collect(entity_count=0)
        assert self._session is not None
        self._session.collect(report)

    def build_from_run(
        self,
        run_result: Any,
        *,
        entity_count: int,
        opportunities_count: int,
        performance_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        if self._session is not None:
            self._snapshot = self._session.build(
                run_result,
                opportunities_count=opportunities_count,
                performance_config=performance_config,
            )
            return
        self._snapshot = ProfilerPerformance.build_from_run(
            strategy_key=self._manager.strategy_key,
            version_id=self._manager.version_id,
            entity_count=entity_count,
            opportunities_count=opportunities_count,
            run_result=run_result,
            performance_config=performance_config,
        )

    def save(self) -> Path:
        if self._snapshot is None:
            raise RuntimeError("profiler.build_from_run() must be called before save()")
        artifact = self._snapshot.save(self._manager.output_dir)
        return artifact.performance_path

    def load(self) -> Dict[str, Any]:
        path = self._manager.output_dir / ProfilerPerformance.PERFORMANCE_FILE
        if not path.is_file():
            legacy = self._manager.output_dir / "performance.json"
            if legacy.is_file():
                path = legacy
        return ProfilerPerformance._read_json(path)

    def summary(self) -> Dict[str, Any]:
        return dict(self.load().get("summary") or {})


def _coerce_job_performance(item: Any) -> JobPerformance:
    if isinstance(item, JobPerformance):
        return item
    if isinstance(item, dict):
        return JobPerformance.from_dict(item)
    return JobPerformance.from_job_report(item)


def _aggregate_phase_totals(jobs: List[JobPerformance]) -> Dict[str, float]:
    totals: Dict[str, float] = {
        "engine_init": 0.0,
        "engine_execute": 0.0,
        "engine_complete": 0.0,
        "load_data": 0.0,
        "enumerate": 0.0,
        "flush_csv": 0.0,
        "enum_pit_until": 0.0,
        "enum_pit_until_unified": 0.0,
        "enum_contract_until": 0.0,
        "enum_process_tick": 0.0,
        "enum_context_fill": 0.0,
        "enum_scan": 0.0,
        "load_contract_issue": 0.0,
        "load_apply_indicators": 0.0,
    }
    for job in jobs:
        totals["engine_init"] += job.engine_perf.init_sec
        totals["engine_execute"] += job.engine_perf.execute_sec
        totals["engine_complete"] += job.engine_perf.complete_sec
        phases = (job.enum_perf or {}).get("phases") or {}
        if isinstance(phases, dict):
            for key in (
                "load_data",
                "enumerate",
                "flush_csv",
                "load_contract_issue",
                "load_apply_indicators",
                "enum_pit_until",
                "enum_pit_until_unified",
                "enum_contract_until",
                "enum_process_tick",
                "enum_context_fill",
                "enum_scan",
            ):
                totals[key] += float(phases.get(key) or 0.0)
    return {key: round(value, 4) for key, value in totals.items()}


def _aggregate_storage_totals(jobs: List[JobPerformance]) -> Dict[str, Any]:
    load_calls = 0
    load_time_seconds = 0.0
    loads_by_slot: Dict[str, float] = {}
    for job in jobs:
        storage = (job.enum_perf or {}).get("storage") or {}
        if not isinstance(storage, dict):
            continue
        load_calls += int(storage.get("load_calls") or 0)
        load_time_seconds += float(storage.get("load_time_seconds") or 0.0)
        slot_map = storage.get("loads_by_slot") or {}
        if isinstance(slot_map, dict):
            for slot, seconds in slot_map.items():
                loads_by_slot[str(slot)] = loads_by_slot.get(str(slot), 0.0) + float(
                    seconds or 0.0
                )
    return {
        "load_calls": load_calls,
        "load_time_seconds": round(load_time_seconds, 4),
        "loads_by_slot": {key: round(value, 4) for key, value in loads_by_slot.items()},
    }


def _aggregate_contract_totals(jobs: List[JobPerformance]) -> Dict[str, Any]:
    until_calls = 0
    until_time_seconds = 0.0
    until_by_slot: Dict[str, float] = {}
    unified_until_calls = 0
    unified_until_time_seconds = 0.0
    for job in jobs:
        contract = (job.enum_perf or {}).get("contract") or {}
        if not isinstance(contract, dict):
            continue
        until_calls += int(contract.get("until_calls") or 0)
        until_time_seconds += float(contract.get("until_time_seconds") or 0.0)
        unified_until_calls += int(contract.get("unified_until_calls") or 0)
        unified_until_time_seconds += float(
            contract.get("unified_until_time_seconds") or 0.0
        )
        slot_map = contract.get("until_by_slot") or {}
        if isinstance(slot_map, dict):
            for slot, seconds in slot_map.items():
                until_by_slot[str(slot)] = until_by_slot.get(str(slot), 0.0) + float(
                    seconds or 0.0
                )
    return {
        "until_calls": until_calls,
        "until_time_seconds": round(until_time_seconds, 4),
        "until_by_slot": {key: round(value, 4) for key, value in until_by_slot.items()},
        "unified_until_calls": unified_until_calls,
        "unified_until_time_seconds": round(unified_until_time_seconds, 4),
    }


__all__ = [
    "ProfilerReport",
]
