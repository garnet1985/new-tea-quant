"""枚举 run 性能快照：汇总调度与 job 指标，落盘 performance.json。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.enumerator.common.report_manager.report_manager import (
        ReportManager,
    )

from core.modules.backtest_engine.core.schedule.entity_based.monitor import EntityMonitorStats
from core.modules.backtest_engine.core.performance.profiler import (
    ENGINE_PERF_KEY,
    ENUM_PERF_KEY,
    WorkerTaskPerf,
)
from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    PERFORMANCE_FILE,
)
from core.modules.strategy.core.engines.enumerator.common.report_manager.report_output import (
    ReportOutput,
)


@dataclass
class DispatchPlanSnapshot:
    """BE 调度 plan 落盘快照（entity / slice 共用字段表）。

    边界:
    - 负责: 从 plan 对象抽取可序列化字段；按 mode 裁剪输出
    - 不负责: 制定调度、改 preload
    - 调用方: ProfilerPerformance.build
    """

    mode: str = ""
    dispatch_jobs: int = 0
    memory_budget_mb: float = 0.0
    # entity_based
    entities_per_job: int = 0
    max_workers: int = 0
    prefetch_ahead: int = 0
    worker_job_budget_mb: float = 0.0
    source_entities_per_job: str = ""
    source_max_workers: str = ""
    probe: Dict[str, Any] = field(default_factory=dict)
    # slice_based
    reader_workers: int = 0
    compute_processes: int = 0
    queue_capacity: int = 0
    preload_depth: int = 0
    slice_open_days: int = 0
    reader_memory_budget_mb: float = 0.0
    compute_memory_budget_mb: float = 0.0
    oom_adjusted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """按 mode 只落私有字段；mode 本身写在 performance 顶层，此处不重复。"""
        base: Dict[str, Any] = {
            "dispatch_jobs": self.dispatch_jobs,
            "memory_budget_mb": self.memory_budget_mb,
        }
        if self.mode == "slice_based":
            base.update(
                {
                    "total_slices": self.dispatch_jobs,
                    "slice_open_days": self.slice_open_days,
                    "reader_workers": self.reader_workers,
                    "compute_workers": self.compute_processes,
                    "max_queue": self.queue_capacity,
                    "dispatch_jobs": self.dispatch_jobs,
                    "compute_processes": self.compute_processes,
                    "queue_capacity": self.queue_capacity,
                    "preload_depth": self.preload_depth,
                    "reader_memory_budget_mb": self.reader_memory_budget_mb,
                    "compute_memory_budget_mb": self.compute_memory_budget_mb,
                    "oom_adjusted": self.oom_adjusted,
                    "probe": dict(self.probe or {}),
                }
            )
            return base
        base.update(
            {
                "entities_per_job": self.entities_per_job,
                "max_workers": self.max_workers,
                "prefetch_ahead": self.prefetch_ahead,
                "worker_job_budget_mb": self.worker_job_budget_mb,
                "source_entities_per_job": self.source_entities_per_job,
                "source_max_workers": self.source_max_workers,
                "probe": dict(self.probe or {}),
            }
        )
        return base

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "DispatchPlanSnapshot":
        data = raw or {}
        probe_raw = data.get("probe")
        # detail 可能是瘦身后的 probe；还原用顶层或 detail
        if isinstance(probe_raw, dict) and "detail" in probe_raw and not probe_raw.get(
            "slices_sampled"
        ):
            detail = probe_raw.get("detail")
            if isinstance(detail, dict) and (
                detail.get("slices_sampled") or detail.get("entities_sampled")
            ):
                probe_raw = detail
        dispatch_jobs = int(
            data.get("total_slices") or data.get("dispatch_jobs") or 0
        )
        return cls(
            mode=str(data.get("mode") or "").strip(),
            dispatch_jobs=dispatch_jobs,
            memory_budget_mb=float(data.get("memory_budget_mb") or 0.0),
            entities_per_job=int(data.get("entities_per_job") or 0),
            max_workers=int(data.get("max_workers") or 0),
            prefetch_ahead=int(data.get("prefetch_ahead") or 0),
            worker_job_budget_mb=float(data.get("worker_job_budget_mb") or 0.0),
            source_entities_per_job=str(data.get("source_entities_per_job") or ""),
            source_max_workers=str(data.get("source_max_workers") or ""),
            probe=dict(probe_raw) if isinstance(probe_raw, dict) else {},
            reader_workers=int(data.get("reader_workers") or 0),
            compute_processes=int(
                data.get("compute_workers") or data.get("compute_processes") or 0
            ),
            queue_capacity=int(data.get("max_queue") or data.get("queue_capacity") or 0),
            preload_depth=int(data.get("preload_depth") or 0),
            slice_open_days=int(data.get("slice_open_days") or 0),
            reader_memory_budget_mb=float(data.get("reader_memory_budget_mb") or 0.0),
            compute_memory_budget_mb=float(data.get("compute_memory_budget_mb") or 0.0),
            oom_adjusted=bool(data.get("oom_adjusted") or False),
        )

    @classmethod
    def from_plan(cls, plan: Any) -> "DispatchPlanSnapshot":
        if plan is None:
            return cls()
        # SliceDispatchPlan 有 reader_workers；Entity 计划有 entities_per_job / max_workers
        if getattr(plan, "reader_workers", None) is not None and getattr(
            plan, "slice_open_days", None
        ) is not None:
            return cls(
                mode="slice_based",
                dispatch_jobs=int(getattr(plan, "dispatch_jobs", 0) or 0),
                memory_budget_mb=float(getattr(plan, "memory_budget_mb", 0.0) or 0.0),
                reader_workers=int(getattr(plan, "reader_workers", 0) or 0),
                compute_processes=int(getattr(plan, "compute_processes", 0) or 0),
                queue_capacity=int(getattr(plan, "queue_capacity", 0) or 0),
                preload_depth=int(getattr(plan, "preload_depth", 0) or 0),
                slice_open_days=int(getattr(plan, "slice_open_days", 0) or 0),
                reader_memory_budget_mb=float(
                    getattr(plan, "reader_memory_budget_mb", 0.0) or 0.0
                ),
                compute_memory_budget_mb=float(
                    getattr(plan, "compute_memory_budget_mb", 0.0) or 0.0
                ),
                oom_adjusted=bool(getattr(plan, "oom_adjusted", False)),
                probe=(
                    dict(getattr(plan, "probe") or {})
                    if isinstance(getattr(plan, "probe", None), dict)
                    else _ProfilerBlocks._probe_snapshot(getattr(plan, "probe", None))
                ),
            )
        return cls(
            mode="entity_based",
            dispatch_jobs=int(getattr(plan, "dispatch_jobs", 0) or 0),
            memory_budget_mb=float(getattr(plan, "memory_budget_mb", 0.0) or 0.0),
            entities_per_job=int(getattr(plan, "entities_per_job", 0) or 0),
            max_workers=int(getattr(plan, "max_workers", 0) or 0),
            prefetch_ahead=int(getattr(plan, "prefetch_ahead", 0) or 0),
            worker_job_budget_mb=float(getattr(plan, "worker_job_budget_mb", 0.0) or 0.0),
            source_entities_per_job=str(getattr(plan, "source_entities_per_job", "") or ""),
            source_max_workers=str(getattr(plan, "source_max_workers", "") or ""),
            probe=_ProfilerBlocks._probe_snapshot(getattr(plan, "probe", None)),
        )


@dataclass
class MonitorStatsSnapshot:
    """BE monitor 运行时统计快照（entity / slice hats）。

    边界:
    - 负责: 从 monitor_stats 抽取可序列化字段
    - 不负责: 运行时采样本身
    - 调用方: ProfilerPerformance.build
    """

    completed_jobs: int = 0
    completed_entities: int = 0
    evaluation_count: int = 0
    current_in_flight: int = 0
    mb_per_entity_hat: float = 0.0
    wall_per_entity_hat: float = 0.0
    sunk_cost_sec_hat: float = 0.0
    margin_cost_sec_per_entity_hat: float = 0.0
    # slice_based runtime hats
    mb_per_slice_reader_hat: float = 0.0
    mb_per_slice_compute_hat: float = 0.0
    mb_per_slice_payload_hat: float = 0.0
    sec_per_slice_reader_hat: float = 0.0
    sec_per_slice_compute_hat: float = 0.0
    peak_rss_mb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        out = {
            "completed_jobs": self.completed_jobs,
            "completed_entities": self.completed_entities,
            "evaluation_count": self.evaluation_count,
            "current_in_flight": self.current_in_flight,
            "mb_per_entity_hat": self.mb_per_entity_hat,
            "wall_per_entity_hat": self.wall_per_entity_hat,
            "sunk_cost_sec_hat": self.sunk_cost_sec_hat,
            "margin_cost_sec_per_entity_hat": self.margin_cost_sec_per_entity_hat,
        }
        if (
            self.mb_per_slice_reader_hat
            or self.mb_per_slice_compute_hat
            or self.sec_per_slice_reader_hat
            or self.sec_per_slice_compute_hat
        ):
            out.update(
                {
                    "mb_per_slice_reader_hat": self.mb_per_slice_reader_hat,
                    "mb_per_slice_compute_hat": self.mb_per_slice_compute_hat,
                    "mb_per_slice_payload_hat": self.mb_per_slice_payload_hat,
                    "sec_per_slice_reader_hat": self.sec_per_slice_reader_hat,
                    "sec_per_slice_compute_hat": self.sec_per_slice_compute_hat,
                    "peak_rss_mb": self.peak_rss_mb,
                }
            )
        return out

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
            mb_per_slice_reader_hat=float(data.get("mb_per_slice_reader_hat") or 0.0),
            mb_per_slice_compute_hat=float(data.get("mb_per_slice_compute_hat") or 0.0),
            mb_per_slice_payload_hat=float(data.get("mb_per_slice_payload_hat") or 0.0),
            sec_per_slice_reader_hat=float(data.get("sec_per_slice_reader_hat") or 0.0),
            sec_per_slice_compute_hat=float(data.get("sec_per_slice_compute_hat") or 0.0),
            peak_rss_mb=float(data.get("peak_rss_mb") or 0.0),
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
        if isinstance(stats, dict):
            return cls.from_dict(stats)
        # SliceMonitorStats 等：completed_slices → completed_jobs
        completed = getattr(stats, "completed_jobs", None)
        if completed is None:
            completed = getattr(stats, "completed_slices", 0)
        return cls(
            completed_jobs=int(completed or 0),
            completed_entities=int(getattr(stats, "completed_entities", 0) or 0),
            evaluation_count=int(getattr(stats, "evaluation_count", 0) or 0),
            current_in_flight=int(getattr(stats, "current_in_flight", 0) or 0),
            mb_per_entity_hat=float(
                getattr(stats, "mb_per_entity_hat", None)
                or getattr(stats, "mb_per_slice_payload_hat", 0.0)
                or 0.0
            ),
            wall_per_entity_hat=float(getattr(stats, "wall_per_entity_hat", 0.0) or 0.0),
            sunk_cost_sec_hat=float(getattr(stats, "sunk_cost_sec_hat", 0.0) or 0.0),
            margin_cost_sec_per_entity_hat=float(
                getattr(stats, "margin_cost_sec_per_entity_hat", 0.0) or 0.0
            ),
            mb_per_slice_reader_hat=float(
                getattr(stats, "mb_per_slice_reader_hat", 0.0) or 0.0
            ),
            mb_per_slice_compute_hat=float(
                getattr(stats, "mb_per_slice_compute_hat", 0.0) or 0.0
            ),
            mb_per_slice_payload_hat=float(
                getattr(stats, "mb_per_slice_payload_hat", 0.0) or 0.0
            ),
            sec_per_slice_reader_hat=float(
                getattr(stats, "sec_per_slice_reader_hat", 0.0) or 0.0
            ),
            sec_per_slice_compute_hat=float(
                getattr(stats, "sec_per_slice_compute_hat", 0.0) or 0.0
            ),
            peak_rss_mb=float(getattr(stats, "peak_rss_mb", 0.0) or 0.0),
        )


@dataclass
class JobPerformance:
    """单 job 执行指标（从 JobReport 归一化）。

    边界:
    - 负责: 解析 success/wall/rss/engine_perf/enum_perf
    - 不负责: 跨 job 汇总（见 ProfilerPerformance）
    - 调用方: _ProfilerCollectSession / ProfilerPerformance
    """

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
    """performance.json 写盘结果路径。

    边界:
    - 负责: 携带落盘路径
    - 不负责: 文件内容
    - 调用方: ProfilerPerformance.save / ProfilerReport
    """

    performance_path: Path


@dataclass
class ProfilerPerformance:
    """一次枚举 run 的性能汇总模型（调度 + job 墙钟 / 内存）。

    边界:
    - 负责: 聚合 jobs/plan/monitor → quick_summary / planner / child_process；读写 performance.json
    - 不负责: 运行时采样钩子（见 ProfilerReport / _ProfilerCollectSession）
    - 调用方: ProfilerReport.build_from_run
    """

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
    pipeline_phases_sec: Dict[str, float] = field(default_factory=dict)
    execute_elapsed_seconds: float = 0.0

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
        pipeline_phases_sec: Optional[Dict[str, Any]] = None,
        execute_elapsed_seconds: Optional[float] = None,
    ) -> "ProfilerPerformance":
        jobs = [_ProfilerBlocks._coerce_job_performance(item) for item in (job_results or [])]
        phases = {
            str(key): float(value or 0.0)
            for key, value in dict(pipeline_phases_sec or {}).items()
        }
        execute_elapsed = (
            float(execute_elapsed_seconds)
            if execute_elapsed_seconds is not None
            else float(elapsed_seconds or 0.0)
        )
        wall = float(phases.get("wall") or 0.0) or float(elapsed_seconds or 0.0)
        return cls(
            strategy_key=str(strategy_key or ""),
            version_id=int(version_id or 0),
            elapsed_seconds=max(0.0, wall),
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
            pipeline_phases_sec=phases,
            execute_elapsed_seconds=max(0.0, execute_elapsed),
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
        phases = dict(getattr(run_result, "pipeline_phases_sec", None) or {})
        execute_elapsed = float(getattr(run_result, "elapsed_seconds", 0.0) or 0.0)
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
            pipeline_phases_sec=phases,
            execute_elapsed_seconds=execute_elapsed,
        )

    @classmethod
    def load(cls, output_dir: Path) -> "ProfilerPerformance":
        path = output_dir / cls.PERFORMANCE_FILE
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
        phase_totals = _ProfilerBlocks._aggregate_phase_totals(self.jobs)
        storage_totals = _ProfilerBlocks._aggregate_storage_totals(self.jobs)
        contract_totals = _ProfilerBlocks._aggregate_contract_totals(self.jobs)
        calendar_totals = _ProfilerBlocks._aggregate_calendar_totals(self.jobs)
        memory = _ProfilerBlocks._build_memory_usage(self.jobs, self.monitor, self.dispatch)
        execute_elapsed = self.execute_elapsed_seconds or float(
            (self.pipeline_phases_sec or {}).get("execute") or 0.0
        ) or self.elapsed_seconds
        parallelism_factor = self._parallelism_factor(job_wall_sum, execute_elapsed)
        mode = str(self.dispatch.mode or "").strip()
        probe_block = _ProfilerBlocks._build_probe_block(
            self.dispatch,
            self.jobs,
            self.monitor,
            entity_count=self.entity_count,
            performance_config=self.performance_config,
        )
        # planner：调度字段保留；probe 只留 status/verdict/原始 detail
        planner = self.dispatch.to_dict()
        planner.pop("probe", None)
        planner_probe: Dict[str, Any] = {
            "status": probe_block["status"],
            "reason": probe_block["reason"],
        }
        if probe_block.get("verdict"):
            planner_probe["verdict"] = probe_block["verdict"]
        if probe_block.get("detail"):
            planner_probe["detail"] = probe_block["detail"]
        binding = (probe_block.get("accuracy") or {}).get("binding_constraint")
        if binding:
            planner_probe["binding_constraint"] = binding
        planner["probe"] = planner_probe

        # slice 并行度分母：reader+compute；entity：max_workers
        if mode == "slice_based":
            parallelism_denom = max(
                1,
                int(self.dispatch.reader_workers or 0)
                + int(self.dispatch.compute_processes or 0),
            )
        else:
            parallelism_denom = max(1, int(self.dispatch.max_workers or 0))
        parallelism_efficiency = (
            round(parallelism_factor / float(parallelism_denom), 4)
            if parallelism_denom > 0
            else 0.0
        )

        quick_summary = _ProfilerBlocks._build_quick_summary(
            mode=mode,
            elapsed_seconds=self.elapsed_seconds,
            execute_elapsed_seconds=execute_elapsed,
            entity_count=self.entity_count,
            total_jobs=self.total_jobs,
            completed_jobs=self.completed_jobs,
            failed_jobs=self.failed_jobs,
            dispatch=self.dispatch,
            memory=memory,
            monitor=self.monitor,
            probe_block=probe_block,
            performance_config=self.performance_config,
            parallelism_factor=parallelism_factor,
            parallelism_efficiency=parallelism_efficiency,
            phase_totals=phase_totals,
            job_wall_sum=job_wall_sum,
            pipeline_phases_sec=dict(self.pipeline_phases_sec or {}),
        )

        payload: Dict[str, Any] = {
            "mode": mode,
            "strategy_key": self.strategy_key,
            "version_id": self.version_id,
            "created_at": self.created_at,
            "quick_summary": quick_summary,
            # summary：quick 未覆盖的机会统计；墙钟拆分见 quick.time_distribution
            "summary": {
                "opportunities_count": self.opportunities_count,
                "entities_with_opportunities": entities_with_opportunities,
            },
            "planner": planner,
            "child_process": {
                "total": {
                    "wall_sec": round(job_wall_sum, 4),
                    "init_sec": phase_totals.get("engine_init", 0.0),
                    "execute_sec": phase_totals.get("engine_execute", 0.0),
                    "complete_sec": phase_totals.get("engine_complete", 0.0),
                },
                "staged": _ProfilerBlocks._build_child_staged(phase_totals),
                "detail": {
                    "storage": storage_totals,
                    "contract": contract_totals,
                    "calendar": calendar_totals,
                    "memory": memory,
                    "cold_start": _ProfilerBlocks._build_cold_start(self.jobs),
                    "failures": _ProfilerBlocks._build_failures(self.jobs, failed_jobs=self.failed_jobs),
                },
            },
            "monitor": self.monitor.to_dict(),
        }
        if self.performance_config:
            payload["performance_config"] = dict(self.performance_config)
        if ReportOutput.resolve_performance_detail(self.performance_config) == ReportOutput.DETAIL_FULL:
            payload["jobs"] = [job.to_dict() for job in self.jobs]
        return payload

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ProfilerPerformance":
        data = raw or {}
        summary = data.get("summary") or {}
        glance = data.get("quick_summary") or {}
        planner_raw = data.get("planner") or data.get("dispatch") or {}
        jobs_raw = data.get("jobs") or []
        # 新格式：墙钟段在 quick_summary.time_distribution；旧格式在 summary.pipeline_phases_sec
        phases = dict(summary.get("pipeline_phases_sec") or {})
        if not phases:
            td = dict(glance.get("time_distribution") or {})
            phases = {
                "plan": float((td.get("planning") or {}).get("sec") or 0.0),
                "execute": float((td.get("load_data") or {}).get("sec") or 0.0)
                + float((td.get("compute") or {}).get("sec") or 0.0),
                "finish": float((td.get("report") or {}).get("sec") or 0.0),
                "wall": float(glance.get("total_sec_spent") or 0.0),
            }
        execute_elapsed = float(
            summary.get("execute_elapsed_seconds")
            or phases.get("execute")
            or summary.get("elapsed_seconds")
            or glance.get("total_sec_spent")
            or 0.0
        )
        batches = dict(glance.get("job_batches") or {})
        plan_g = dict(glance.get("plan") or {})
        mode = str(data.get("mode") or data.get("execution_mode") or planner_raw.get("mode") or "")
        if mode and not planner_raw.get("mode"):
            planner_raw = dict(planner_raw)
            planner_raw["mode"] = mode
        return cls(
            strategy_key=str(data.get("strategy_key") or ""),
            version_id=int(data.get("version_id") or 0),
            elapsed_seconds=float(
                summary.get("elapsed_seconds")
                or glance.get("total_sec_spent")
                or 0.0
            ),
            total_jobs=int(summary.get("total_jobs") or batches.get("total") or 0),
            completed_jobs=int(
                summary.get("completed_jobs") or batches.get("success") or 0
            ),
            failed_jobs=int(summary.get("failed_jobs") or batches.get("fail") or 0),
            entity_count=int(
                summary.get("entity_count")
                or glance.get("total_entity")
                or plan_g.get("total_entity")
                or 0
            ),
            opportunities_count=int(summary.get("opportunities_count") or 0),
            dispatch=DispatchPlanSnapshot.from_dict(planner_raw),
            monitor=MonitorStatsSnapshot.from_dict(data.get("monitor") or {}),
            performance_config=dict(data.get("performance_config") or {}),
            jobs=[JobPerformance.from_dict(item) for item in jobs_raw if isinstance(item, dict)],
            created_at=str(data.get("created_at") or ""),
            pipeline_phases_sec=phases,
            execute_elapsed_seconds=execute_elapsed,
        )

    # ── private ──

    @staticmethod
    def _avg(numerator: float, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return float(numerator) / float(denominator)

    def _parallelism_factor(self, job_wall_sum: float, execute_elapsed: float) -> float:
        if execute_elapsed <= 0:
            return 0.0
        return round(job_wall_sum / execute_elapsed, 2)

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
    """主进程侧 job 性能采集会话。

    边界:
    - 负责: 累积 on_task_result 的 JobPerformance；交给 ProfilerPerformance.build
    - 不负责: 落盘、quick_summary 组装
    - 调用方: ProfilerReport
    """

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
        phases = dict(getattr(run_result, "pipeline_phases_sec", None) or {})
        execute_elapsed = float(getattr(run_result, "elapsed_seconds", 0.0) or 0.0)
        return ProfilerPerformance.build(
            strategy_key=self.strategy_key,
            version_id=self.version_id,
            elapsed_seconds=float(phases.get("wall") or execute_elapsed),
            total_jobs=int(getattr(run_result, "total_jobs", 0) or 0),
            completed_jobs=int(getattr(run_result, "completed_jobs", 0) or 0),
            failed_jobs=int(getattr(run_result, "failed_jobs", 0) or 0),
            entity_count=self.entity_count,
            opportunities_count=max(0, int(opportunities_count)),
            job_results=self._jobs or list(getattr(run_result, "job_results", []) or []),
            plan=getattr(run_result, "plan", None),
            monitor_stats=getattr(run_result, "monitor_stats", None),
            performance_config=performance_config,
            pipeline_phases_sec=phases,
            execute_elapsed_seconds=execute_elapsed,
        )


class ProfilerReport:
    """ReportManager.profiler 门面：采集 / 构建 / 落盘 performance.json。

    边界:
    - 负责: job 指标采集、quick_summary / planner / probe 块组装
    - 不负责: 调度决策、CSV investments
    - 调用方: ReportManager
    """

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
        return ProfilerPerformance._read_json(path)

    def summary(self) -> Dict[str, Any]:
        return dict(self.load().get("summary") or {})




class _ProfilerBlocks:
    """performance.json 块组装工具（模块内私有）。

    边界:
    - 负责: quick_summary / probe / memory / time_distribution 等纯函数组装
    - 不负责: 采集会话、文件 IO
    - 调用方: ProfilerPerformance / DispatchPlanSnapshot
    """

    @staticmethod
    def _coerce_job_performance(item: Any) -> JobPerformance:
        if isinstance(item, JobPerformance):
            return item
        if isinstance(item, dict):
            return JobPerformance.from_dict(item)
        return JobPerformance.from_job_report(item)


    @staticmethod
    def _build_child_staged(phase_totals: Dict[str, float]) -> Dict[str, float]:
        """子进程墙钟按阶段合计（跨 job 求和）。"""
        return {
            "init": float(phase_totals.get("engine_init") or 0.0),
            "load_data": float(phase_totals.get("load_data") or 0.0),
            "load_contract_issue": float(phase_totals.get("load_contract_issue") or 0.0),
            "load_apply_indicators": float(phase_totals.get("load_apply_indicators") or 0.0),
            "enumerate": float(phase_totals.get("enumerate") or 0.0),
            "enum_as_of_slice": float(phase_totals.get("enum_as_of_slice") or 0.0),
            "enum_as_of_slice_unified": float(phase_totals.get("enum_as_of_slice_unified") or 0.0),
            "enum_contract_until": float(phase_totals.get("enum_contract_until") or 0.0),
            "enum_scan": float(phase_totals.get("enum_scan") or 0.0),
            "enum_context_fill": float(phase_totals.get("enum_context_fill") or 0.0),
            "enum_process_tick": float(phase_totals.get("enum_process_tick") or 0.0),
            "flush_csv": float(phase_totals.get("flush_csv") or 0.0),
            "complete": float(phase_totals.get("engine_complete") or 0.0),
        }


    @staticmethod
    def _probe_snapshot(probe: Any) -> Dict[str, Any]:
        if probe is None:
            return {
                "ran": False,
                "entities_sampled": 0,
                "mb_per_entity": 0.0,
                "sec_per_entity": 0.0,
                "wall_sec": 0.0,
                "peak_rss_mb": 0.0,
                "pickle_bytes": 0,
            }
        if isinstance(probe, dict):
            # slice probe
            if probe.get("slices_sampled") or probe.get("sec_per_slice_reader") is not None:
                sampled = int(probe.get("slices_sampled") or 0)
                out = {
                    "ran": bool(probe.get("ran")) or sampled > 0,
                    "slices_sampled": sampled,
                    "mb_per_slice_reader": float(probe.get("mb_per_slice_reader") or 0.0),
                    "mb_per_slice_compute": float(probe.get("mb_per_slice_compute") or 0.0),
                    "mb_per_slice_payload": float(probe.get("mb_per_slice_payload") or 0.0),
                    "sec_per_slice_reader": float(probe.get("sec_per_slice_reader") or 0.0),
                    "sec_per_slice_compute": float(probe.get("sec_per_slice_compute") or 0.0),
                    "peak_rss_mb_reader": float(probe.get("peak_rss_mb_reader") or 0.0),
                    "peak_rss_mb_compute": float(probe.get("peak_rss_mb_compute") or 0.0),
                    "wall_sec": float(probe.get("wall_sec") or 0.0),
                }
                return out
            sampled = int(probe.get("entities_sampled") or 0)
            return {
                "ran": sampled > 0,
                "entities_sampled": sampled,
                "mb_per_entity": float(probe.get("mb_per_entity") or 0.0),
                "sec_per_entity": float(probe.get("sec_per_entity") or 0.0),
                "wall_sec": float(probe.get("wall_sec") or 0.0),
                "peak_rss_mb": float(probe.get("peak_rss_mb") or 0.0),
                "pickle_bytes": int(probe.get("pickle_bytes") or 0),
            }
        sampled = int(getattr(probe, "entities_sampled", 0) or 0)
        if hasattr(probe, "slices_sampled") or hasattr(probe, "sec_per_slice_reader"):
            return {
                "ran": True,
                "slices_sampled": int(getattr(probe, "slices_sampled", 0) or 0),
                "mb_per_slice_reader": float(getattr(probe, "mb_per_slice_reader", 0.0) or 0.0),
                "mb_per_slice_compute": float(getattr(probe, "mb_per_slice_compute", 0.0) or 0.0),
                "mb_per_slice_payload": float(getattr(probe, "mb_per_slice_payload", 0.0) or 0.0),
                "sec_per_slice_reader": float(getattr(probe, "sec_per_slice_reader", 0.0) or 0.0),
                "sec_per_slice_compute": float(getattr(probe, "sec_per_slice_compute", 0.0) or 0.0),
                "peak_rss_mb_reader": float(getattr(probe, "peak_rss_mb_reader", 0.0) or 0.0),
                "peak_rss_mb_compute": float(getattr(probe, "peak_rss_mb_compute", 0.0) or 0.0),
                "wall_sec": float(getattr(probe, "wall_sec", 0.0) or 0.0),
            }
        return {
            "ran": sampled > 0,
            "entities_sampled": sampled,
            "mb_per_entity": float(getattr(probe, "mb_per_entity", 0.0) or 0.0),
            "sec_per_entity": float(getattr(probe, "sec_per_entity", 0.0) or 0.0),
            "wall_sec": float(getattr(probe, "wall_sec", 0.0) or 0.0),
            "peak_rss_mb": float(getattr(probe, "peak_rss_mb", 0.0) or 0.0),
            "pickle_bytes": int(getattr(probe, "pickle_bytes", 0) or 0),
        }


    @staticmethod
    def _ratio(actual: float, probe: float) -> float:
        if probe <= 0:
            return 0.0
        return round(float(actual) / float(probe), 4)


    @staticmethod
    def _ratio_or_none(numerator: float, denominator: float) -> Optional[float]:
        if denominator <= 0:
            return None
        return round(float(numerator) / float(denominator), 4)


    @staticmethod
    def _peak_overshoot(actual_peak: float, estimated: float) -> Optional[float]:
        """actual_peak / estimated - 1；负值表示峰值仍低于估计（有安全余量）。"""
        if estimated <= 0:
            return None
        return round(float(actual_peak) / float(estimated) - 1.0, 4)


    @staticmethod
    def _memory_tier(
        *,
        estimated: Optional[float],
        actual: float,
        actual_peak: float,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        est = None if estimated is None else round(float(estimated), 4)
        act = round(float(actual), 4)
        peak = round(float(actual_peak), 4)
        out: Dict[str, Any] = {
            "estimated": est,
            "actual": act,
            "actual_peak": peak,
            "estimate_accuracy": (
                _ProfilerBlocks._ratio_or_none(act, est) if est is not None else None
            ),
            "peak_overshoot": _ProfilerBlocks._peak_overshoot(peak, est) if est is not None else None,
        }
        if extra:
            out.update(extra)
        return out


    @staticmethod
    def _phase_bucket(sec: float, total: float) -> Dict[str, float]:
        pct = round(100.0 * float(sec) / float(total), 1) if total > 0 else 0.0
        return {"sec": round(float(sec), 4), "pct": pct}


    @staticmethod
    def _build_time_distribution(
        *,
        pipeline_phases_sec: Dict[str, float],
        phase_totals: Dict[str, float],
        wall_sec: float,
        mode: str = "entity_based",
        monitor: Optional[MonitorStatsSnapshot] = None,
    ) -> Dict[str, Any]:
        """流水线时间分布（墙钟口径）。

        entity: planning / load_data / compute / report
        slice:  planning / read / compute / report
        """
        phases = dict(pipeline_phases_sec or {})
        prep = float(phases.get("prep") or 0.0)
        plan = float(phases.get("plan") or 0.0)
        execute = float(phases.get("execute") or 0.0)
        finish = float(phases.get("finish") or 0.0)
        wall = float(wall_sec or 0.0) or float(phases.get("wall") or 0.0)
        if wall <= 0:
            wall = prep + plan + execute + finish

        planning_sec = prep + plan
        mon = monitor or MonitorStatsSnapshot()

        if mode == "slice_based":
            read_hat = float(mon.sec_per_slice_reader_hat or 0.0)
            compute_hat = float(mon.sec_per_slice_compute_hat or 0.0)
            work = read_hat + compute_hat
            if work > 0 and execute > 0:
                read_sec = execute * (read_hat / work)
                compute_sec = execute * (compute_hat / work)
            else:
                # fallback：子进程阶段或整段 execute 归 compute
                load_cpu = float(phase_totals.get("load_data") or 0.0)
                enum_cpu = float(phase_totals.get("enumerate") or 0.0)
                work_cpu = load_cpu + enum_cpu
                if work_cpu > 0 and execute > 0:
                    read_sec = execute * (load_cpu / work_cpu)
                    compute_sec = execute * (enum_cpu / work_cpu)
                else:
                    read_sec = 0.0
                    compute_sec = execute
            return {
                "unit": "sec",
                "planning": _ProfilerBlocks._phase_bucket(planning_sec, wall),
                "read": _ProfilerBlocks._phase_bucket(read_sec, wall),
                "compute": _ProfilerBlocks._phase_bucket(compute_sec, wall),
                "report": _ProfilerBlocks._phase_bucket(finish, wall),
                "note": (
                    "planning/report=流水线墙钟；"
                    "read/compute=按 monitor 单片读/算秒数占比拆分 execute；"
                    "细账见 child_process"
                ),
            }

        load_cpu = float(phase_totals.get("load_data") or 0.0)
        compute_cpu = float(phase_totals.get("enumerate") or 0.0)
        work_cpu = load_cpu + compute_cpu
        if work_cpu > 0 and execute > 0:
            load_sec = execute * (load_cpu / work_cpu)
            compute_sec = execute * (compute_cpu / work_cpu)
        else:
            load_sec = 0.0
            compute_sec = execute

        return {
            "unit": "sec",
            "planning": _ProfilerBlocks._phase_bucket(planning_sec, wall),
            "load_data": _ProfilerBlocks._phase_bucket(load_sec, wall),
            "compute": _ProfilerBlocks._phase_bucket(compute_sec, wall),
            "report": _ProfilerBlocks._phase_bucket(finish, wall),
            "note": (
                "planning/report=流水线墙钟；"
                "load_data/compute=按子进程 CPU 占比拆分 execute 墙钟；"
                "细账见 child_process.staged"
            ),
        }


    @staticmethod
    def _compute_wait_for_reader_sec(
        *,
        sec_per_slice_read: float,
        sec_per_slice_compute: float,
        reader_workers: int,
        compute_workers: int,
        total_slices: int,
    ) -> float:
        """估/实测共用：单片「读出间隔 − 算耗」× 片数 ≈ compute 等 reader 总秒。

        inter_arrival ≈ sec_read / readers
        service      ≈ sec_compute / compute_workers
        wait/slice   = max(0, inter_arrival − service)
        """
        readers = max(1, int(reader_workers or 1))
        computes = max(1, int(compute_workers or 1))
        n = max(0, int(total_slices or 0))
        if n <= 0 or sec_per_slice_compute <= 0:
            return 0.0
        inter_arrival = float(sec_per_slice_read) / float(readers)
        service = float(sec_per_slice_compute) / float(computes)
        return round(max(0.0, inter_arrival - service) * float(n), 4)


    @staticmethod
    def _build_slice_quick_summary(
        *,
        elapsed_seconds: float,
        execute_elapsed_seconds: float,
        entity_count: int,
        total_jobs: int,
        completed_jobs: int,
        failed_jobs: int,
        dispatch: DispatchPlanSnapshot,
        memory: Dict[str, Any],
        monitor: MonitorStatsSnapshot,
        probe_block: Dict[str, Any],
        parallelism_factor: float,
        parallelism_efficiency: float,
        phase_totals: Dict[str, float],
        job_wall_sum: float,
        pipeline_phases_sec: Dict[str, float],
    ) -> Dict[str, Any]:
        took = float(elapsed_seconds or 0.0)
        execute_took = float(execute_elapsed_seconds or 0.0) or took
        n_entity = int(entity_count or 0)
        total_slices = max(0, int(dispatch.dispatch_jobs or 0))
        reader_workers = max(0, int(dispatch.reader_workers or 0))
        compute_workers = max(1, int(dispatch.compute_processes or 1))
        max_queue = max(0, int(dispatch.queue_capacity or 0))
        pool_mb = float(memory.get("available_pool_mb") or dispatch.memory_budget_mb or 0.0)

        estimates = dict(probe_block.get("estimates") or {})
        probe = dict(dispatch.probe or {})
        # ran=真探针；plan_defaults / 有 mb 单价也可估内存
        probe_ran = bool(probe.get("ran")) or str(probe_block.get("status") or "") == "ran"
        preload = max(1, int(dispatch.preload_depth or 1))

        sec_read_est = float(
            estimates.get("sec_per_slice_read")
            or probe.get("sec_per_slice_reader")
            or 0.0
        )
        sec_compute_est = float(
            estimates.get("sec_per_slice_compute")
            or probe.get("sec_per_slice_compute")
            or 0.0
        )
        ratio = (
            round(sec_read_est / sec_compute_est, 4)
            if sec_compute_est > 0
            else 0.0
        )
        ideal_readers = round(ratio * float(compute_workers), 2) if ratio > 0 else 0.0

        # 单片内存单价：探针 > estimates > 从 budget 反推 > 默认
        mb_r = float(
            estimates.get("mb_per_slice_reader")
            or probe.get("mb_per_slice_reader")
            or 0.0
        )
        mb_c = float(
            estimates.get("mb_per_slice_compute")
            or probe.get("mb_per_slice_compute")
            or 0.0
        )
        mb_p = float(
            estimates.get("mb_per_slice_payload")
            or probe.get("mb_per_slice_payload")
            or 0.0
        )
        reader_budget = float(dispatch.reader_memory_budget_mb or 0.0)
        compute_budget = float(dispatch.compute_memory_budget_mb or 0.0)
        if mb_r <= 0 and reader_budget > 0 and reader_workers > 0:
            mb_r = reader_budget / float(reader_workers * preload)
        if mb_c <= 0 and compute_budget > 0 and compute_workers > 0:
            mb_c = compute_budget / float(compute_workers)
        if mb_r <= 0:
            mb_r = 10.0
        if mb_c <= 0:
            mb_c = 15.0
        if mb_p <= 0:
            mb_p = 5.0

        # concurrent 估：优先用 planner 已算好的 budget
        reader_conc_est = (
            reader_budget
            if reader_budget > 0
            else mb_r * float(max(1, reader_workers)) * float(preload)
        )
        compute_conc_est = (
            compute_budget
            if compute_budget > 0
            else mb_c * float(compute_workers)
        )
        payload_conc_est = mb_p * float(max(1, max_queue))
        total_est = reader_conc_est + compute_conc_est + payload_conc_est

        actual_peak = float(monitor.peak_rss_mb or memory.get("per_process_peak_rss_mb_max") or 0.0)
        actual_median = float(
            memory.get("per_process_peak_rss_mb_median") or monitor.peak_rss_mb or 0.0
        )
        actual_mb_r = float(monitor.mb_per_slice_reader_hat or 0.0)
        actual_mb_c = float(monitor.mb_per_slice_compute_hat or 0.0)
        actual_mb_p = float(monitor.mb_per_slice_payload_hat or 0.0)

        # plan accuracy：compute 等 reader
        est_wait = _ProfilerBlocks._compute_wait_for_reader_sec(
            sec_per_slice_read=sec_read_est,
            sec_per_slice_compute=sec_compute_est,
            reader_workers=reader_workers,
            compute_workers=compute_workers,
            total_slices=total_slices,
        )
        sec_read_act = float(monitor.sec_per_slice_reader_hat or 0.0)
        sec_compute_act = float(monitor.sec_per_slice_compute_hat or 0.0)
        act_wait = _ProfilerBlocks._compute_wait_for_reader_sec(
            sec_per_slice_read=sec_read_act or sec_read_est,
            sec_per_slice_compute=sec_compute_act or sec_compute_est,
            reader_workers=reader_workers,
            compute_workers=compute_workers,
            total_slices=total_slices,
        )
        wait_acc = _ProfilerBlocks._ratio_or_none(act_wait, est_wait) if est_wait > 0 else (
            0.0 if act_wait <= 0 else None
        )

        entity_per_sec = (float(n_entity) / took) if took > 0 else 0.0
        slice_per_sec = (float(total_slices) / took) if took > 0 and total_slices > 0 else 0.0
        success_rate = (
            round(float(completed_jobs) / float(total_jobs), 4) if total_jobs > 0 else 0.0
        )
        wall_jobs = float(job_wall_sum or 0.0)
        saved_sec = (
            round(wall_jobs - execute_took, 2) if wall_jobs > 0 and execute_took > 0 else 0.0
        )

        time_distribution = _ProfilerBlocks._build_time_distribution(
            pipeline_phases_sec=pipeline_phases_sec,
            phase_totals=phase_totals,
            wall_sec=took,
            mode="slice_based",
            monitor=monitor,
        )

        binding = (probe_block.get("accuracy") or {}).get("binding_constraint")
        if not binding:
            binding = "cpu"
            if dispatch.oom_adjusted:
                binding = "memory"

        return {
            "total_sec_spent": round(took, 2),
            "saved_sec": saved_sec,
            "parallelism": parallelism_factor,
            "parallelism_efficiency": parallelism_efficiency,
            "total_entity": n_entity,
            "total_slices": total_slices,
            "process_capacity": {
                "entity_per_sec": round(entity_per_sec, 2),
                "slice_per_sec": round(slice_per_sec, 2),
                "mb_per_sec": round(
                    (actual_median * float(total_slices) / took) if took > 0 and actual_median > 0 else 0.0,
                    2,
                ),
            },
            "job_batches": {
                "total": int(total_jobs),
                "success": int(completed_jobs),
                "fail": int(failed_jobs),
                "success_rate": success_rate,
            },
            "plan": {
                "total_entity": n_entity,
                "total_slices": total_slices,
                "slice_open_days": int(dispatch.slice_open_days or 0),
                "reader_workers": reader_workers,
                "compute_workers": compute_workers,
                "max_queue": max_queue,
                "sec_per_slice_read": round(sec_read_est, 4),
                "sec_per_slice_compute": round(sec_compute_est, 4),
                "reader_compute_ratio": ratio,
                "ideal_readers": ideal_readers,
            },
            "memory": {
                "unit": "MB",
                "overall_available": round(pool_mb, 1),
                "avg_usage_rate": _ProfilerBlocks._ratio_or_none(actual_median, pool_mb),
                "peak_usage_rate": _ProfilerBlocks._ratio_or_none(actual_peak, pool_mb),
                "per_slice": {
                    "reader": _ProfilerBlocks._memory_tier(
                        estimated=mb_r,
                        actual=actual_mb_r,
                        actual_peak=float(probe.get("peak_rss_mb_reader") or actual_mb_r or 0.0),
                    ),
                    "compute": _ProfilerBlocks._memory_tier(
                        estimated=mb_c,
                        actual=actual_mb_c,
                        actual_peak=float(probe.get("peak_rss_mb_compute") or actual_mb_c or 0.0),
                    ),
                    "payload": _ProfilerBlocks._memory_tier(
                        estimated=mb_p,
                        actual=actual_mb_p,
                        actual_peak=actual_mb_p,
                    ),
                },
                "concurrent": {
                    "reader": {"estimated": round(reader_conc_est, 3)},
                    "compute": {"estimated": round(compute_conc_est, 3)},
                    "payload": {"estimated": round(payload_conc_est, 3)},
                    "total": _ProfilerBlocks._memory_tier(
                        estimated=total_est,
                        actual=actual_median,
                        actual_peak=actual_peak,
                    ),
                },
                "estimate_source": (
                    "probe" if probe_ran else str(probe.get("source") or "plan_defaults")
                ),
            },
            "time_distribution": time_distribution,
            "plan_accuracy": {
                "estimated": {
                    "compute_wait_for_reader_sec": est_wait,
                    "sec_per_slice_read": round(sec_read_est, 4),
                    "sec_per_slice_compute": round(sec_compute_est, 4),
                    "reader_compute_ratio": ratio,
                    "planned_readers": reader_workers,
                    "ideal_readers": ideal_readers,
                },
                "actual": {
                    "compute_wait_for_reader_sec": act_wait,
                    "sec_per_slice_read": round(sec_read_act, 4),
                    "sec_per_slice_compute": round(sec_compute_act, 4),
                },
                "wait_estimate_accuracy": wait_acc,
                "wait_gap_sec": round(act_wait - est_wait, 4),
                "note": (
                    "wait≈max(0, sec_read/readers − sec_compute/compute)×total_slices；"
                    "estimated 用探针；actual 用 monitor 单片实测"
                ),
            },
            "probe_status": probe_block.get("status"),
            "binding_constraint": binding,
        }


    @staticmethod
    def _build_quick_summary(
        *,
        mode: str = "entity_based",
        elapsed_seconds: float,
        entity_count: int,
        total_jobs: int,
        completed_jobs: int,
        failed_jobs: int,
        dispatch: Optional[DispatchPlanSnapshot] = None,
        memory: Dict[str, Any],
        monitor: Optional[MonitorStatsSnapshot] = None,
        probe_block: Dict[str, Any],
        performance_config: Optional[Dict[str, Any]],
        parallelism_factor: float,
        parallelism_efficiency: float,
        phase_totals: Dict[str, float],
        job_wall_sum: float = 0.0,
        execute_elapsed_seconds: float = 0.0,
        pipeline_phases_sec: Optional[Dict[str, float]] = None,
        # legacy kwargs（旧调用兼容，已不用）
        entities_per_job: int = 0,
        max_workers: int = 0,
    ) -> Dict[str, Any]:
        """人读一眼摘要：吞吐 + job 批次 + 计划 + 内存估算/实测分层。"""
        disp = dispatch or DispatchPlanSnapshot()
        mon = monitor or MonitorStatsSnapshot()
        if str(mode or disp.mode or "") == "slice_based":
            return _ProfilerBlocks._build_slice_quick_summary(
                elapsed_seconds=elapsed_seconds,
                execute_elapsed_seconds=execute_elapsed_seconds,
                entity_count=entity_count,
                total_jobs=total_jobs,
                completed_jobs=completed_jobs,
                failed_jobs=failed_jobs,
                dispatch=disp,
                memory=memory,
                monitor=mon,
                probe_block=probe_block,
                parallelism_factor=parallelism_factor,
                parallelism_efficiency=parallelism_efficiency,
                phase_totals=phase_totals,
                job_wall_sum=job_wall_sum,
                pipeline_phases_sec=dict(pipeline_phases_sec or {}),
            )

        took = float(elapsed_seconds or 0.0)
        execute_took = float(execute_elapsed_seconds or 0.0) or took
        n_entity = int(entity_count or 0)
        epj = max(0, int(disp.entities_per_job or entities_per_job or 0))
        workers = max(1, int(disp.max_workers or max_workers or 1))
        pool_mb = float(memory.get("available_pool_mb") or 0.0)
        worker_actual = float(memory.get("per_process_peak_rss_mb_median") or 0.0)
        worker_peak = float(memory.get("per_process_peak_rss_mb_max") or 0.0)
        concurrent_actual = float(memory.get("estimated_concurrent_rss_mb") or 0.0)
        concurrent_peak = float(memory.get("estimated_concurrent_rss_mb_worst") or 0.0)

        cfg = dict(performance_config or {})
        if cfg.get("dispatch_probe_safety_factor") not in (None, ""):
            safety = float(cfg.get("dispatch_probe_safety_factor"))
        else:
            safety = 1.0
        buffer_rate = max(0.0, safety - 1.0)
        estimates = dict(probe_block.get("estimates") or {})
        probe_ran = str(probe_block.get("status") or "") == "ran"
        entity_est: Optional[float] = None
        if probe_ran:
            raw_est = estimates.get("mb_per_entity")
            if raw_est is not None:
                entity_est = float(raw_est)
            else:
                probe_n = max(1, int(estimates.get("probe_entities") or 0))
                probe_peak = float(estimates.get("probe_peak_rss_mb") or 0.0)
                if probe_peak > 0 and probe_n > 0:
                    entity_est = (probe_peak / float(probe_n)) * (1.0 + buffer_rate)

        entity_actual = (worker_actual / float(epj)) if epj > 0 and worker_actual > 0 else 0.0
        entity_peak = (worker_peak / float(epj)) if epj > 0 and worker_peak > 0 else 0.0

        worker_est: Optional[float] = (
            entity_est * float(epj) if entity_est is not None and epj > 0 else None
        )
        concurrent_est: Optional[float] = (
            worker_est * float(workers) if worker_est is not None else None
        )

        entity_per_sec = (float(n_entity) / took) if took > 0 else 0.0
        mb_per_sec = (
            (entity_actual * float(n_entity) / took)
            if took > 0 and entity_actual > 0
            else 0.0
        )

        success_rate = (
            round(float(completed_jobs) / float(total_jobs), 4) if total_jobs > 0 else 0.0
        )

        wall_jobs = float(job_wall_sum or 0.0)
        saved_sec = (
            round(wall_jobs - execute_took, 2) if wall_jobs > 0 and execute_took > 0 else 0.0
        )

        time_distribution = _ProfilerBlocks._build_time_distribution(
            pipeline_phases_sec=dict(pipeline_phases_sec or {}),
            phase_totals=phase_totals,
            wall_sec=took,
            mode="entity_based",
            monitor=mon,
        )

        binding = (probe_block.get("accuracy") or {}).get("binding_constraint")
        if not binding and probe_block.get("binding_constraint"):
            binding = probe_block.get("binding_constraint")

        return {
            "total_sec_spent": round(took, 2),
            "saved_sec": saved_sec,
            "parallelism": parallelism_factor,
            "parallelism_efficiency": parallelism_efficiency,
            "total_entity": n_entity,
            "process_capacity": {
                "entity_per_sec": round(entity_per_sec, 2),
                "mb_per_sec": round(mb_per_sec, 2),
            },
            "job_batches": {
                "total": int(total_jobs),
                "success": int(completed_jobs),
                "fail": int(failed_jobs),
                "success_rate": success_rate,
            },
            "plan": {
                "total_entity": n_entity,
                "entity_per_job": epj,
                "worker": workers,
            },
            "memory": {
                "unit": "MB",
                "overall_available": round(pool_mb, 1),
                "avg_usage_rate": _ProfilerBlocks._ratio_or_none(concurrent_actual, pool_mb),
                "peak_usage_rate": _ProfilerBlocks._ratio_or_none(concurrent_peak, pool_mb),
                "per_entity": _ProfilerBlocks._memory_tier(
                    estimated=entity_est,
                    actual=entity_actual,
                    actual_peak=entity_peak,
                    extra={"buffer_rate": round(buffer_rate, 4)},
                ),
                "worker": _ProfilerBlocks._memory_tier(
                    estimated=worker_est,
                    actual=worker_actual,
                    actual_peak=worker_peak,
                ),
                "concurrent": _ProfilerBlocks._memory_tier(
                    estimated=concurrent_est,
                    actual=concurrent_actual,
                    actual_peak=concurrent_peak,
                ),
            },
            "time_distribution": time_distribution,
            "probe_status": probe_block.get("status"),
            "binding_constraint": binding,
        }


    @staticmethod
    def _build_memory_usage(
        jobs: List[JobPerformance],
        monitor: MonitorStatsSnapshot,
        dispatch: DispatchPlanSnapshot,
    ) -> Dict[str, Any]:
        """内存口径一律标明范围：单进程 vs 估并发池。"""
        peaks = [
            float(job.peak_rss_mb or job.engine_perf.peak_rss_mb or 0.0)
            for job in jobs
            if job.success
        ]
        peaks = [p for p in peaks if p > 0]
        ok_jobs = [job for job in jobs if job.success and job.entities_count > 0]
        mb_per_entity = 0.0
        if peaks and ok_jobs:
            ratios = []
            for job in ok_jobs:
                peak = float(job.peak_rss_mb or job.engine_perf.peak_rss_mb or 0.0)
                if peak > 0:
                    ratios.append(peak / float(job.entities_count))
            if ratios:
                mb_per_entity = sum(ratios) / float(len(ratios))
        elif monitor.mb_per_entity_hat > 0:
            mb_per_entity = float(monitor.mb_per_entity_hat)

        median_peak = _ProfilerBlocks._median(peaks) if peaks else 0.0
        max_peak = max(peaks) if peaks else 0.0
        workers = max(1, int(dispatch.max_workers or 1))
        pool_mb = float(dispatch.memory_budget_mb or 0.0)
        # 无法拿到墙上同时刻的多进程 RSS 之和 → 用 workers × 单进程峰值近似「满仓并发」
        concurrent_est_mb = median_peak * workers if median_peak > 0 else 0.0
        concurrent_worst_mb = max_peak * workers if max_peak > 0 else 0.0
        fair_slot_mb = (pool_mb / workers) if workers > 0 and pool_mb > 0 else 0.0

        if not peaks:
            note = "未采集到子进程 RSS；无 per-process 峰值就估不出并发池"
        else:
            util = (concurrent_est_mb / pool_mb) if pool_mb > 0 else 0.0
            note = (
                f"单进程峰值≈{median_peak:.0f}MB（最大{max_peak:.0f}MB）；"
                f"估并发满仓≈{concurrent_est_mb:.0f}MB（{workers}进程×单进程中位）；"
                f"可用池≈{pool_mb:.0f}MB（利用率≈{util:.0%}）"
            )
        return {
            # 单进程（一个 worker 跑一个 job 时的进程 RSS）
            "per_process_peak_rss_mb_median": round(median_peak, 1),
            "per_process_peak_rss_mb_max": round(max_peak, 1),
            "mb_per_entity": round(mb_per_entity, 3),
            # 并发池（估算，不是墙上采样的全局 RSS）
            "workers": workers,
            "estimated_concurrent_rss_mb": round(concurrent_est_mb, 1),
            "estimated_concurrent_rss_mb_worst": round(concurrent_worst_mb, 1),
            "available_pool_mb": round(pool_mb, 1),
            "fair_share_per_worker_mb": round(fair_slot_mb, 1),
            "pool_utilization": round(concurrent_est_mb / pool_mb, 4) if pool_mb > 0 else 0.0,
            # 兼容旧字段名
            "peak_job_rss_mb_median": round(median_peak, 1),
            "peak_job_rss_mb_max": round(max_peak, 1),
            "plan_budget_mb": round(pool_mb, 1),
            "worker_job_budget_mb": round(float(dispatch.worker_job_budget_mb or 0.0), 1),
            "note": note,
        }


    @staticmethod
    def _build_slice_probe_block(
        dispatch: DispatchPlanSnapshot,
        monitor: MonitorStatsSnapshot,
        performance_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """slice 探针：读/算单片秒数 → reader_compute_ratio + wait 估准。"""
        _ = performance_config
        probe = dict(dispatch.probe or {})
        ran = bool(probe.get("ran")) or int(probe.get("slices_sampled") or 0) > 0
        has_mb = (
            float(probe.get("mb_per_slice_reader") or 0.0) > 0
            or float(dispatch.reader_memory_budget_mb or 0.0) > 0
        )
        detail = dict(probe) if probe else {}
        readers = max(0, int(dispatch.reader_workers or 0))
        computes = max(1, int(dispatch.compute_processes or 1))
        total_slices = max(0, int(dispatch.dispatch_jobs or 0))
        preload = max(1, int(dispatch.preload_depth or 1))
        max_queue = max(1, int(dispatch.queue_capacity or 1))

        mb_r = float(probe.get("mb_per_slice_reader") or 0.0)
        mb_c = float(probe.get("mb_per_slice_compute") or 0.0)
        mb_p = float(probe.get("mb_per_slice_payload") or 0.0)
        if mb_r <= 0 and dispatch.reader_memory_budget_mb > 0 and readers > 0:
            mb_r = float(dispatch.reader_memory_budget_mb) / float(readers * preload)
        if mb_c <= 0 and dispatch.compute_memory_budget_mb > 0:
            mb_c = float(dispatch.compute_memory_budget_mb) / float(computes)
        if mb_r <= 0:
            mb_r = 10.0
        if mb_c <= 0:
            mb_c = 15.0
        if mb_p <= 0:
            mb_p = 5.0

        sec_r = float(probe.get("sec_per_slice_reader") or 0.0)
        sec_c = float(probe.get("sec_per_slice_compute") or 0.0)
        ratio = round(sec_r / sec_c, 4) if sec_c > 0 else 0.0
        ideal = round(ratio * float(computes), 2) if ratio > 0 else 0.0
        est_wait = _ProfilerBlocks._compute_wait_for_reader_sec(
            sec_per_slice_read=sec_r,
            sec_per_slice_compute=sec_c,
            reader_workers=readers,
            compute_workers=computes,
            total_slices=total_slices,
        )
        act_r = float(monitor.sec_per_slice_reader_hat or 0.0)
        act_c = float(monitor.sec_per_slice_compute_hat or 0.0)
        act_wait = _ProfilerBlocks._compute_wait_for_reader_sec(
            sec_per_slice_read=act_r or sec_r,
            sec_per_slice_compute=act_c or sec_c,
            reader_workers=readers,
            compute_workers=computes,
            total_slices=total_slices,
        )
        wait_acc = _ProfilerBlocks._ratio_or_none(act_wait, est_wait) if est_wait > 0 else (
            0.0 if act_wait <= 0 else None
        )

        estimates = {
            "slices_sampled": int(probe.get("slices_sampled") or 0),
            "sec_per_slice_read": round(sec_r, 4),
            "sec_per_slice_compute": round(sec_c, 4),
            "reader_compute_ratio": ratio,
            "ideal_readers": ideal,
            "mb_per_slice_reader": round(mb_r, 4),
            "mb_per_slice_compute": round(mb_c, 4),
            "mb_per_slice_payload": round(mb_p, 4),
            "compute_wait_for_reader_sec": est_wait,
            "source": "probe" if ran else str(probe.get("source") or "plan_defaults"),
        }

        if ran:
            status = "ran"
            reason = (
                f"采样 {estimates['slices_sampled']} 片 → "
                f"{readers} reader × {computes} compute，max_queue={max_queue}"
            )
        elif has_mb:
            status = "defaults"
            reason = (
                f"未跑探针，用 plan 默认单价/预算估内存 "
                f"（{readers} reader × {computes} compute）"
            )
        else:
            return {
                "status": "skipped",
                "reason": "本次未跑 slice 探针且无可用 plan 预算",
                "verdict": "不适用：没法估读算搭配",
                "accuracy": None,
                "detail": detail or None,
            }

        if not ran:
            verdict = (
                "未跑探针：内存用 plan_defaults；"
                "sec/ratio/wait 需探针或 monitor 单片实测才有"
            )
        elif act_r <= 0 and act_c <= 0:
            verdict = "已跑探针，但缺 monitor 单片实测，wait 准确度待补"
        elif wait_acc is None:
            verdict = (
                f"估 wait≈{est_wait:.2f}s，实测 wait≈{act_wait:.2f}s；"
                f"理想 reader≈{ideal}，实配 {readers}"
            )
        else:
            parts = [
                f"估 wait≈{est_wait:.2f}s，实测≈{act_wait:.2f}s（acc={wait_acc:.2f}）",
                f"ratio={ratio} → 理想 reader≈{ideal}，实配 {readers}",
            ]
            if wait_acc > 1.3:
                parts.append("低估了 compute 等 reader")
            elif wait_acc < 0.7 and est_wait > 0:
                parts.append("高估了等读时间")
            else:
                parts.append("读算搭配估算基本靠谱")
            verdict = "；".join(parts)

        binding = "memory" if dispatch.oom_adjusted else "cpu"
        return {
            "status": status,
            "reason": reason,
            "verdict": verdict,
            "estimates": estimates,
            "accuracy": {
                "estimated_compute_wait_for_reader_sec": est_wait,
                "actual_compute_wait_for_reader_sec": act_wait,
                "wait_estimate_accuracy": wait_acc,
                "wait_gap_sec": round(act_wait - est_wait, 4),
                "binding_constraint": binding,
                "note": (
                    "wait≈max(0, sec_read/readers − sec_compute/compute)×total_slices；"
                    "≈1 最好，>1 低估挨饿"
                ),
            },
            "detail": detail,
        }


    @staticmethod
    def _build_probe_block(
        dispatch: DispatchPlanSnapshot,
        jobs: List[JobPerformance],
        monitor: MonitorStatsSnapshot,
        *,
        entity_count: int,
        performance_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """探针成败：entity=内存估准；slice=读算搭配/wait 估准。"""
        _ = entity_count
        if str(dispatch.mode or "") == "slice_based":
            return _ProfilerBlocks._build_slice_probe_block(dispatch, monitor, performance_config)

        probe = dict(dispatch.probe or {})
        ran = bool(probe.get("ran")) or int(probe.get("entities_sampled") or 0) > 0
        detail = dict(probe) if probe else {}
        cfg = dict(performance_config or {})
        epj = int(dispatch.entities_per_job or 0)
        epj_source = str(dispatch.source_entities_per_job or "")
        mw_source = str(dispatch.source_max_workers or "")
        memory = _ProfilerBlocks._build_memory_usage(jobs, monitor, dispatch)
        workers = max(1, int(dispatch.max_workers or 1))
        pool_mb = float(dispatch.memory_budget_mb or 0.0)

        if ran:
            probe_n = max(1, int(probe.get("entities_sampled") or 0))
            probe_peak = float(probe.get("peak_rss_mb") or 0.0)
            # 探针内部旧算法：delta_rss/n（去掉进程固定开销）—— planner worker_job_budget 仍用它
            mb_per_entity_delta = float(probe.get("mb_per_entity") or 0.0)
            # raw peak/n；estimated = raw × (1+buffer)，buffer_rate 仅展示
            mb_per_entity_raw = probe_peak / float(probe_n) if probe_n > 0 else 0.0
            safety = float(cfg.get("dispatch_probe_safety_factor") or 1.0)
            buffer_rate = max(0.0, safety - 1.0)
            mb_per_entity = mb_per_entity_raw * (1.0 + buffer_rate)
            # worker / concurrent 用已含 buffer 的 estimated，不再二次乘 buffer
            mb_per_worker = round(mb_per_entity * float(epj), 3) if epj > 0 else 0.0
            mb_per_worker_delta = (
                round(mb_per_entity_delta * float(epj), 3) if epj > 0 else 0.0
            )
            predicted_concurrent_mb = mb_per_worker * float(workers)
            actual_concurrent_mb = float(memory.get("estimated_concurrent_rss_mb") or 0.0)
            actual_per_process = float(
                memory.get("per_process_peak_rss_mb_median") or 0.0
            )
            actual_mb_per_entity = (
                actual_per_process / float(epj)
                if epj > 0 and actual_per_process > 0
                else float(memory.get("mb_per_entity") or 0.0)
            )
            estimate_ratio = _ProfilerBlocks._ratio(actual_concurrent_mb, predicted_concurrent_mb)
            safety_util = (
                round(actual_concurrent_mb / pool_mb, 4) if pool_mb > 0 else 0.0
            )

            if mw_source == "memory_capped":
                binding = "memory"
                binding_note = "workers 被内存上限压过，不是纯打满 CPU"
            else:
                binding = "cpu"
                binding_note = "workers 按 CPU/auto 取，内存未成为瓶颈"

            estimates = {
                "probe_entities": probe_n,
                "probe_peak_rss_mb": round(probe_peak, 3),
                "mb_per_entity": round(mb_per_entity, 4),
                "mb_per_entity_raw": round(mb_per_entity_raw, 4),
                "mb_per_entity_delta": round(mb_per_entity_delta, 4),
                "buffer_rate": round(buffer_rate, 4),
                "mb_per_worker": mb_per_worker,
                "mb_per_worker_delta": mb_per_worker_delta,
                "predicted_concurrent_mb": round(predicted_concurrent_mb, 1),
                "formula": (
                    "estimated=peak/n×(1+buffer)；"
                    "worker=estimated×epj；"
                    "concurrent=worker×workers"
                ),
                "note": (
                    "mb_per_entity 已含 buffer；buffer_rate 仅展示；"
                    "mb_per_entity_delta 是 (peak-baseline)/n，给 planner 内部预算用"
                ),
            }

            if actual_concurrent_mb <= 0 or predicted_concurrent_mb <= 0:
                verdict = "已跑探针，但缺实测单进程 RSS，无法对比估算"
            else:
                parts = [
                    f"预估并发≈{predicted_concurrent_mb:.0f}MB，"
                    f"实测并发≈{actual_concurrent_mb:.0f}MB"
                    f"（差 {estimate_ratio:.2f}x）",
                ]
                if estimate_ratio > 1.3:
                    parts.append("探针低估了内存")
                elif estimate_ratio < 0.7:
                    parts.append("探针高估了内存")
                else:
                    parts.append("估算基本靠谱")
                if pool_mb > 0:
                    parts.append(
                        f"相对可用池{pool_mb:.0f}MB 利用率{safety_util:.0%}"
                        + ("，安全" if safety_util < 0.85 else "，偏紧需警惕")
                    )
                parts.append(binding_note)
                verdict = "；".join(parts)

            return {
                "status": "ran",
                "reason": (
                    f"采样 {probe_n} 股（单进程峰值≈{probe_peak:.1f}MB）→ "
                    f"计划 {workers}×{epj}股/job"
                ),
                "verdict": verdict,
                "estimates": estimates,
                "accuracy": {
                    "formula": "estimated=peak/n×(1+buffer)；worker=estimated×epj；concurrent=worker×workers",
                    "probe": estimates,
                    "actual": {
                        "mb_per_entity": round(actual_mb_per_entity, 4),
                        "mb_per_worker": round(actual_per_process, 1),
                        "concurrent_mb": round(actual_concurrent_mb, 1),
                        "scope": (
                            "mb_per_worker=单进程峰值中位；"
                            "mb_per_entity≈mb_per_worker/epj；"
                            "concurrent=mb_per_worker×workers"
                        ),
                    },
                    "estimate_ratio": estimate_ratio,
                    "safety_utilization": safety_util,
                    "available_pool_mb": round(pool_mb, 1),
                    "binding_constraint": binding,
                    "note": (
                        "estimate_ratio=actual.concurrent/probe.predicted，≈1 最好，>1 低估；"
                        "safety_utilization=actual.concurrent/available_pool"
                    ),
                },
                "detail": detail,
            }

        if epj_source == "settings" or (
            epj > 0 and epj_source not in ("", "auto", "empty", "default")
        ):
            reason = f"已固定每批 {epj} 股（来源 {epj_source}），无需探针估 epj"
        elif cfg.get("dispatch_probe") is False:
            reason = "配置关闭了 dispatch_probe"
        else:
            reason = "本次未跑调度探针"
        return {
            "status": "skipped",
            "reason": reason,
            "verdict": "不适用：没跑探针就没法谈估得准不准",
            "accuracy": None,
            "detail": detail or None,
        }


    @staticmethod
    def _build_probe_accuracy(
        dispatch: DispatchPlanSnapshot,
        jobs: List[JobPerformance],
        monitor: MonitorStatsSnapshot,
        *,
        entity_count: int,
    ) -> Dict[str, Any]:
        block = _ProfilerBlocks._build_probe_block(
            dispatch,
            jobs,
            monitor,
            entity_count=entity_count,
        )
        return dict(block.get("accuracy") or {})


    @staticmethod
    def _median(values: List[float]) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        mid = len(ordered) // 2
        if len(ordered) % 2 == 1:
            return float(ordered[mid])
        return float(ordered[mid - 1] + ordered[mid]) / 2.0


    @staticmethod
    def _build_cold_start(jobs: List[JobPerformance]) -> Dict[str, Any]:
        walls = [float(job.wall_sec) for job in jobs if job.success and job.wall_sec > 0]
        if not walls:
            return {
                "first_job_wall_sec": 0.0,
                "median_job_wall_sec": 0.0,
                "ratio": 0.0,
            }
        first = float(walls[0])
        median = _ProfilerBlocks._median(walls)
        return {
            "first_job_wall_sec": round(first, 4),
            "median_job_wall_sec": round(median, 4),
            "ratio": _ProfilerBlocks._ratio(first, median),
        }


    @staticmethod
    def _build_failures(jobs: List[JobPerformance], *, failed_jobs: int) -> Dict[str, Any]:
        failed = [job for job in jobs if not job.success]
        samples = [
            {"job_id": job.job_id, "error": (job.error or "")[:240]}
            for job in failed[:10]
        ]
        return {
            "failed_jobs": max(int(failed_jobs), len(failed)),
            "failed_job_samples": samples,
        }



    @staticmethod
    def _aggregate_phase_totals(jobs: List[JobPerformance]) -> Dict[str, float]:
        totals: Dict[str, float] = {
            "engine_init": 0.0,
            "engine_execute": 0.0,
            "engine_complete": 0.0,
            "load_data": 0.0,
            "enumerate": 0.0,
            "flush_csv": 0.0,
            "enum_as_of_slice": 0.0,
            "enum_as_of_slice_unified": 0.0,
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
                    "enum_as_of_slice",
                    "enum_as_of_slice_unified",
                    "enum_contract_until",
                    "enum_process_tick",
                    "enum_context_fill",
                    "enum_scan",
                ):
                    totals[key] += float(phases.get(key) or 0.0)
        return {key: round(value, 4) for key, value in totals.items()}


    @staticmethod
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


    @staticmethod
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

    @staticmethod
    def _aggregate_calendar_totals(jobs: List[JobPerformance]) -> Dict[str, Any]:
        """跨 job 汇总日历沉默成本计数（entity_day miss / 全日 empty as_of_slice）。"""
        open_dates_count = 0
        days_total = 0
        days_with_any_bar = 0
        days_all_empty = 0
        days_skipped_before_ready = 0
        entity_day_bar_hit = 0
        entity_day_bar_miss = 0
        as_of_active_day_sec = 0.0
        as_of_empty_day_sec = 0.0
        entities_in_jobs = 0
        period_start = ""
        period_end = ""
        for job in jobs:
            calendar = (job.enum_perf or {}).get("calendar") or {}
            if not isinstance(calendar, dict):
                continue
            open_dates_count = max(
                open_dates_count, int(calendar.get("open_dates_count") or 0)
            )
            days_total += int(calendar.get("days_total") or 0)
            days_with_any_bar += int(calendar.get("days_with_any_bar") or 0)
            days_all_empty += int(calendar.get("days_all_empty") or 0)
            days_skipped_before_ready += int(
                calendar.get("days_skipped_before_ready") or 0
            )
            entity_day_bar_hit += int(calendar.get("entity_day_bar_hit") or 0)
            entity_day_bar_miss += int(calendar.get("entity_day_bar_miss") or 0)
            as_of_active_day_sec += float(calendar.get("as_of_active_day_sec") or 0.0)
            as_of_empty_day_sec += float(calendar.get("as_of_empty_day_sec") or 0.0)
            entities_in_jobs += int(calendar.get("entities_in_job") or 0)
            ps = str(calendar.get("period_start") or "").strip()
            pe = str(calendar.get("period_end") or "").strip()
            if ps and (not period_start or ps < period_start):
                period_start = ps
            if pe and (not period_end or pe > period_end):
                period_end = pe
        entity_days = entity_day_bar_hit + entity_day_bar_miss
        miss_ratio = (
            float(entity_day_bar_miss) / float(entity_days) if entity_days else 0.0
        )
        empty_day_ratio = (
            float(days_all_empty) / float(days_total) if days_total else 0.0
        )
        return {
            "open_dates_count": open_dates_count,
            "period_start": period_start,
            "period_end": period_end,
            "entities_in_jobs": entities_in_jobs,
            "days_total": days_total,
            "days_with_any_bar": days_with_any_bar,
            "days_all_empty": days_all_empty,
            "days_skipped_before_ready": days_skipped_before_ready,
            "empty_day_ratio": round(empty_day_ratio, 4),
            "entity_day_bar_hit": entity_day_bar_hit,
            "entity_day_bar_miss": entity_day_bar_miss,
            "entity_day_miss_ratio": round(miss_ratio, 4),
            "as_of_active_day_sec": round(as_of_active_day_sec, 4),
            "as_of_empty_day_sec": round(as_of_empty_day_sec, 4),
        }


__all__ = [
    "ProfilerReport",
]
