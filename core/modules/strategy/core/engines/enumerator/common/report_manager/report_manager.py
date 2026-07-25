"""枚举 run 产物编排（version 目录、runtime / overall / investments）。

本文件:
- ReportManager: begin / buffer / flush / finalize / present
- SavedRunArtifacts: finalize 后关键路径句柄
  边界: 负责 enum 落盘与展示；不负责 BE 调度或枚举 tick 业务（类级边界见各类 docstring）
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.enumerator.common.report_manager.overall_report import (
    OverallReportHandle,
)
from core.modules.strategy.core.engines.enumerator.common.report_manager.profiler import (
    ProfilerReport,
)
from core.modules.strategy.core.engines.enumerator.common.report_manager.runtime_snapshot import (
    RuntimeReport,
    RuntimeEnv,
)
from core.modules.strategy.core.engines.enumerator.common.report_manager.stock_investments import (
    InvestmentsReport,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.data.simulation_output_recorder import (
    SimulationOutputRecorder,
)


@dataclass
class SavedRunArtifacts:
    """一次 finalize 写盘后的关键文件路径。

    边界:
    - 负责: 携带 performance/overall/runtime/entity_ids 路径
    - 不负责: 写盘逻辑
    - 调用方: ReportManager.finalize
    """

    performance_path: Path
    overall_report_path: Path
    runtime_env_path: Path
    entity_ids_path: Path


@dataclass
class ReportManager:
    """枚举 run 产物编排（entity / slice 共用）。

    边界:
    - 负责: version 目录、runtime/performance/overall 落盘、worker buffer/flush、present
    - 不负责: BE 调度、枚举模拟逻辑、指纹索引
    - 调用方: EnumeratorPipeline / JobExecutor
    """

    output_dir: Path
    strategy_key: str
    version_id: int
    strategy_path: str = ""
    runtime: RuntimeReport = field(init=False, repr=False)
    profiler: ProfilerReport = field(init=False, repr=False)
    overall: OverallReportHandle = field(init=False, repr=False)
    investments: InvestmentsReport = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        self.strategy_path = str(self.strategy_path or self.strategy_key or "").strip()
        self.runtime = RuntimeReport(self)
        self.profiler = ProfilerReport(self)
        self.overall = OverallReportHandle(self)
        self.investments = InvestmentsReport(self)

    # ── 工厂 ──

    @classmethod
    def begin(
        cls,
        strategy_key: str,
        *,
        entity_ids: List[str],
        settings_fp: str,
        env_fp: str,
        effective_settings: StrategySettings,
        settings_diff: Dict[str, Any],
        execution_mode: str,
        market_profile: str,
        strategy_path: str = "",
    ) -> "ReportManager":
        """分配 version 目录并写入 0_runtime_env.json / 0_entity_ids.txt。

        strategy_key: settings.meta.key（展示 / 指纹身份）
        strategy_path: strategies 根下相对路径（落盘位置；缺省回退到 key）
        """
        path_id = str(strategy_path or strategy_key or "").strip()
        if not path_id:
            raise ValueError("strategy_path / strategy_key 不能为空")
        root = ProjectContext.path.get_strategy_directory_simulation_enum(path_id)
        output_dir, version_id = SimulationOutputRecorder.allocate_version_dir(
            path_id,
            root,
        )
        manager = cls(
            output_dir=output_dir,
            strategy_key=str(strategy_key or path_id).strip(),
            version_id=int(version_id),
            strategy_path=path_id,
        )
        manager.runtime.save_begin(
            entity_ids=entity_ids,
            settings_fp=settings_fp,
            env_fp=env_fp,
            effective_settings=effective_settings,
            settings_diff=settings_diff,
            execution_mode=execution_mode,
            market_profile=market_profile,
        )
        return manager

    @classmethod
    def open(
        cls,
        output_dir: Path,
        *,
        strategy_key: str,
        version_id: int,
        strategy_path: str = "",
    ) -> "ReportManager":
        return cls(
            output_dir=Path(output_dir),
            strategy_key=str(strategy_key or "").strip(),
            version_id=int(version_id or 0),
            strategy_path=str(strategy_path or strategy_key or "").strip(),
        )

    @classmethod
    def from_output_dir(cls, output_dir: Path) -> "ReportManager":
        runtime = RuntimeEnv.load(Path(output_dir))
        return cls(
            output_dir=Path(output_dir),
            strategy_key=runtime.strategy_key,
            version_id=runtime.version_id,
            strategy_path=runtime.strategy_path or runtime.strategy_key,
        )

    # ── run 结束 ──

    def finalize_from_run_result(
        self,
        run_result: Any,
        *,
        entity_count: int,
        opportunities_count: int,
        performance_config: Optional[Dict[str, Any]] = None,
    ) -> SavedRunArtifacts:
        self.profiler.build_from_run(
            run_result,
            entity_count=entity_count,
            opportunities_count=opportunities_count,
            performance_config=performance_config,
        )
        performance_path = self.profiler.save()
        overall_report_path = self.overall.build(total_entities=entity_count).save()
        return SavedRunArtifacts(
            performance_path=performance_path,
            overall_report_path=overall_report_path,
            runtime_env_path=self.output_dir / RuntimeEnv.RUNTIME_ENV_FILE,
            entity_ids_path=self.output_dir / RuntimeEnv.ENTITY_IDS_FILE,
        )

    # ── 展示（CLI / UI）──

    def present(self, stream: Optional[TextIO] = None) -> None:
        """CLI / UI 终局摘要（entity / slice 共用；handlers 应主要依赖本方法）。"""
        out = stream or sys.stdout
        runtime = self.runtime.load()
        period = runtime.get("period") or {}
        mode = str(runtime.get("execution_mode") or "").strip() or "-"
        entity_count = int(runtime.get("entity_count") or 0)
        if entity_count <= 0:
            entity_count = len(runtime.get("entity_ids") or [])
        print(
            f"run: {runtime.get('strategy_key', self.strategy_key)} "
            f"v{runtime.get('version_id', self.version_id)}  "
            f"path={runtime.get('strategy_path') or self.strategy_path or '-'}  "
            f"mode={mode}  "
            f"entities={entity_count}  "
            f"period={period.get('start_date', '')}~{period.get('end_date', '')}",
            file=out,
            flush=True,
        )
        self.overall.present(stream=out)

        perf_payload: Dict[str, Any] = {}
        try:
            perf_payload = self.profiler.load()
        except Exception:
            perf_payload = {}
        summary = dict(perf_payload.get("summary") or {})
        glance = dict(
            perf_payload.get("quick_summary")
            or perf_payload.get("at_a_glance")
            or {}
        )
        child = dict(perf_payload.get("child_process") or {})
        planner = dict(perf_payload.get("planner") or {})
        mode_hint = str(perf_payload.get("mode") or mode)

        if glance:
            plan = dict(glance.get("plan") or {})
            batches = dict(glance.get("job_batches") or {})
            mem = dict(glance.get("memory") or {})
            cap = dict(glance.get("process_capacity") or {})
            pe = dict(mem.get("per_entity") or {})
            wk = dict(mem.get("worker") or {})
            cc = dict(mem.get("concurrent") or {})
            print(
                f"quick: {glance.get('total_sec_spent', glance.get('took_sec', '?'))}s  "
                f"saved={glance.get('saved_sec', plan.get('saved_sec', '?'))}s  "
                f"entities={glance.get('total_entity', '?')}  "
                f"jobs={batches.get('success', '?')}/{batches.get('total', '?')}  "
                f"workers={plan.get('worker', '?')}  "
                f"parallelism≈{glance.get('parallelism', plan.get('parallelism', plan.get('speedup', '?')))}x  "
                f"eff={glance.get('parallelism_efficiency', plan.get('parallelism_efficiency', '?'))}",
                file=out,
                flush=True,
            )
            where = dict(
                glance.get("time_distribution") or glance.get("time_share") or {}
            )
            if where.get("planning") or where.get("load_data") or where.get("read"):
                pl = dict(where.get("planning") or {})
                ld = dict(where.get("load_data") or where.get("read") or {})
                cp = dict(where.get("compute") or {})
                rp = dict(where.get("report") or {})
                mid = "read" if where.get("read") else "load"
                print(
                    f"  time: plan={pl.get('pct', '?')}%  "
                    f"{mid}={ld.get('pct', '?')}%  "
                    f"compute={cp.get('pct', '?')}%  "
                    f"report={rp.get('pct', '?')}%",
                    file=out,
                    flush=True,
                )
            elif where:
                print(
                    f"  time: load={where.get('load_data_pct', '?')}%  "
                    f"strategy={where.get('strategy_pct', '?')}%",
                    file=out,
                    flush=True,
                )
            if cap:
                print(
                    f"  capacity: {cap.get('entity_per_sec', '?')} entity/s  "
                    f"{cap.get('mb_per_sec', '?')} MB/s",
                    file=out,
                    flush=True,
                )
            if mem:
                unit = mem.get("unit") or "MB"
                print(
                    f"  mem({unit}): pool={mem.get('overall_available', mem.get('overall_available_mb', '?'))}  "
                    f"avg_util={mem.get('avg_usage_rate', '?')}  "
                    f"peak_util={mem.get('peak_usage_rate', '?')}",
                    file=out,
                    flush=True,
                )
                print(
                    f"  entity: est={pe.get('estimated')}  "
                    f"actual={pe.get('actual')}  "
                    f"acc={pe.get('estimate_accuracy')}  "
                    f"overshoot={pe.get('peak_overshoot', pe.get('peak_OOM_rate'))}  "
                    f"buf={pe.get('buffer_rate')}",
                    file=out,
                    flush=True,
                )
                print(
                    f"  worker: est={wk.get('estimated')}  "
                    f"actual={wk.get('actual')}  "
                    f"acc={wk.get('estimate_accuracy')}  "
                    f"overshoot={wk.get('peak_overshoot', wk.get('peak_OOM_rate'))}",
                    file=out,
                    flush=True,
                )
                print(
                    f"  concurrent: est={cc.get('estimated')}  "
                    f"actual={cc.get('actual')}  "
                    f"acc={cc.get('estimate_accuracy')}  "
                    f"overshoot={cc.get('peak_overshoot', cc.get('peak_OOM_rate'))}",
                    file=out,
                    flush=True,
                )
            if glance.get("probe_status"):
                print(
                    f"  probe: {glance.get('probe_status')}  "
                    f"bind={glance.get('binding_constraint')}",
                    file=out,
                    flush=True,
                )

        if mode_hint == "slice_based":
            planner_line = (
                f"planner: slices={planner.get('total_slices', planner.get('dispatch_jobs', 0))}  "
                f"readers={planner.get('reader_workers', 0)}  "
                f"compute={planner.get('compute_workers', planner.get('compute_processes', 0))}  "
                f"max_queue={planner.get('max_queue', planner.get('queue_capacity', 0))}  "
                f"days={planner.get('slice_open_days', 0)}"
            )
            pa = dict(glance.get("plan_accuracy") or {}) if glance else {}
            if pa:
                est = dict(pa.get("estimated") or {})
                act = dict(pa.get("actual") or {})
                print(
                    f"  wait: est={est.get('compute_wait_for_reader_sec', '?')}s  "
                    f"actual={act.get('compute_wait_for_reader_sec', '?')}s  "
                    f"acc={pa.get('wait_estimate_accuracy', '?')}  "
                    f"gap={pa.get('wait_gap_sec', '?')}s",
                    file=out,
                    flush=True,
                )
        elif mode_hint == "entity_based":
            planner_line = (
                f"planner: jobs={planner.get('dispatch_jobs', 0)}  "
                f"epj={planner.get('entities_per_job', 0)}  "
                f"workers={planner.get('max_workers', 0)}"
            )
        else:
            planner_line = f"planner: mode={mode_hint or '-'}"
        print(planner_line, file=out, flush=True)
        staged = dict(child.get("staged") or {})
        if staged:
            print(
                f"child: load={float(staged.get('load_data') or 0):.2f}s  "
                f"enumerate={float(staged.get('enumerate') or 0):.2f}s  "
                f"flush={float(staged.get('flush_csv') or 0):.2f}s",
                file=out,
                flush=True,
            )
        print(
            f"性能: elapsed={float(glance.get('total_sec_spent') or summary.get('elapsed_seconds') or 0):.2f}s  "
            f"saved={glance.get('saved_sec', '?')}s  "
            f"parallelism={glance.get('parallelism', summary.get('parallelism_factor', 0))}  "
            f"efficiency={glance.get('parallelism_efficiency', summary.get('parallelism_efficiency', 0))}",
            file=out,
            flush=True,
        )
        print(f"产物目录: {self.output_dir}", file=out, flush=True)

    def to_worker_binding(self) -> Dict[str, Any]:
        """写入 job payload，供 worker 子进程还原 output 目录。"""
        return {
            "output_dir": str(self.output_dir),
            "strategy_id": self.strategy_key,
            "version_id": self.version_id,
            "version_dir_name": str(self.version_id),
        }

    to_recorder_binding = to_worker_binding

    # ── worker 子进程（job payload 内 buffer + flush）──

    WORKER_SNAPSHOT_KEY = SimulationOutputRecorder.SNAPSHOT_KEY
    WORKER_INSTANCE_KEY = "_report_manager"
    JOB_BUFFER_KEY = "_enum_job_buffer"

    @classmethod
    def resolve_worker(cls, payload: Dict[str, Any]) -> "ReportManager":
        """子进程：从 payload binding 还原 ReportManager（同 job 内复用）。"""
        cached = payload.get(cls.WORKER_INSTANCE_KEY)
        if isinstance(cached, cls):
            return cached

        snapshot = payload.get(cls.WORKER_SNAPSHOT_KEY)
        if not isinstance(snapshot, dict):
            raise ValueError(f"payload 缺少 {cls.WORKER_SNAPSHOT_KEY} binding")

        manager = cls.from_output_dir(Path(str(snapshot["output_dir"])))
        payload[cls.WORKER_INSTANCE_KEY] = manager
        return manager

    @classmethod
    def worker_buffer_opportunities(
        cls,
        payload: Dict[str, Any],
        opportunities: List[Dict[str, Any]],
    ) -> None:
        payload.setdefault(cls.JOB_BUFFER_KEY, []).extend(list(opportunities or []))

    @classmethod
    def worker_flush_job_investments(cls, payload: Dict[str, Any]) -> Dict[str, int]:
        manager = cls.resolve_worker(payload)
        buffer = list(payload.pop(cls.JOB_BUFFER_KEY, []) or [])
        return manager.investments.flush_buffered(buffer)


__all__ = ["ReportManager", "SavedRunArtifacts"]
