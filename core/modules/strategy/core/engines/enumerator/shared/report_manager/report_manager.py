"""枚举 run 产物编排：version 目录、runtime / performance / overall 落盘与展示。"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.enumerator.shared.report_manager.overall_report import (
    OverallReport,
)
from core.modules.strategy.core.engines.enumerator.shared.report_manager.profiler import (
    ProfilerPerformance,
    SavedPerformanceArtifact,
)
from core.modules.strategy.core.engines.enumerator.shared.report_manager.runtime_snapshot import (
    RuntimeSnapshot,
    SavedRuntimeArtifacts,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.data.simulation_output_recorder import (
    SimulationOutputRecorder,
)


@dataclass
class SavedRunArtifacts:
    runtime: SavedRuntimeArtifacts
    performance: SavedPerformanceArtifact
    overall_report_path: Path


@dataclass
class ReportManager:
    """一次 enum run 的产物管理者（entity / slice 共用入口）。"""

    output_dir: Path
    strategy_key: str
    version_id: int

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
    ) -> "ReportManager":
        """分配 version 目录并写入 runtime_env.json / entity_ids.txt。"""
        root = ProjectContext.path.get_strategy_directory_simulation_enum(strategy_key)
        output_dir, version_id = SimulationOutputRecorder.allocate_version_dir(
            strategy_key,
            root,
        )
        runtime = RuntimeSnapshot.build(
            strategy_key=strategy_key,
            version_id=version_id,
            entity_ids=entity_ids,
            settings_fp=settings_fp,
            env_fp=env_fp,
            effective_settings=effective_settings,
            settings_diff=settings_diff,
            execution_mode=execution_mode,
            market_profile=market_profile,
        )
        runtime.save(output_dir)
        return cls(
            output_dir=output_dir,
            strategy_key=strategy_key,
            version_id=int(version_id),
        )

    @classmethod
    def open(cls, output_dir: Path, *, strategy_key: str, version_id: int) -> "ReportManager":
        return cls(
            output_dir=Path(output_dir),
            strategy_key=str(strategy_key or "").strip(),
            version_id=int(version_id or 0),
        )

    @classmethod
    def from_output_dir(cls, output_dir: Path) -> "ReportManager":
        runtime = RuntimeSnapshot.load(Path(output_dir))
        return cls(
            output_dir=Path(output_dir),
            strategy_key=runtime.strategy_key,
            version_id=runtime.version_id,
        )

    # ── run 结束：performance + overall ──

    def finalize_run(
        self,
        *,
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
    ) -> SavedRunArtifacts:
        runtime = RuntimeSnapshot.load(self.output_dir)
        performance = ProfilerPerformance.build(
            strategy_key=self.strategy_key,
            version_id=self.version_id,
            elapsed_seconds=elapsed_seconds,
            total_jobs=total_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            entity_count=entity_count,
            opportunities_count=opportunities_count,
            job_results=job_results,
            plan=plan,
            monitor_stats=monitor_stats,
            performance_config=performance_config,
        )
        overall = OverallReport.build(
            self.output_dir,
            strategy_key=self.strategy_key,
            version_id=self.version_id,
            total_entities=entity_count or runtime.entity_count,
        )
        return SavedRunArtifacts(
            runtime=SavedRuntimeArtifacts(
                entity_ids_path=self.output_dir / RuntimeSnapshot.ENTITY_IDS_FILE,
                runtime_env_path=self.output_dir / RuntimeSnapshot.RUNTIME_ENV_FILE,
            ),
            performance=performance.save(self.output_dir),
            overall_report_path=overall.save(self.output_dir),
        )

    def finalize_from_run_result(
        self,
        run_result: Any,
        *,
        entity_count: int,
        opportunities_count: int,
        performance_config: Optional[Dict[str, Any]] = None,
    ) -> SavedRunArtifacts:
        return self.finalize_run(
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

    # ── 加载 ──

    def load_runtime(self) -> RuntimeSnapshot:
        return RuntimeSnapshot.load(self.output_dir)

    def load_performance(self) -> ProfilerPerformance:
        return ProfilerPerformance.load(self.output_dir)

    def load_overall_report(self) -> OverallReport:
        return OverallReport.load(self.output_dir)

    # ── 展示（CLI / UI）──

    def present(self, stream: Optional[TextIO] = None) -> None:
        out = stream or sys.stdout
        runtime = self.load_runtime()
        print(
            f"run: {runtime.strategy_key} v{runtime.version_id}  "
            f"entities={runtime.entity_count}  "
            f"period={runtime.period.start_date}~{runtime.period.end_date}",
            file=out,
            flush=True,
        )
        self.load_overall_report().present(stream=out)
        perf = self.load_performance()
        summary = perf.to_dict().get("summary") or {}
        print(
            f"性能: elapsed={summary.get('elapsed_seconds', 0):.2f}s  "
            f"jobs={summary.get('completed_jobs', 0)}/{summary.get('total_jobs', 0)}  "
            f"parallelism={summary.get('parallelism_factor', 0)}",
            file=out,
            flush=True,
        )
        print(f"产物目录: {self.output_dir}", file=out, flush=True)

    def to_recorder_binding(self) -> Dict[str, Any]:
        """供 EntityBasedEnumeratorRecorder 绑定的目录信息。"""
        return {
            "output_dir": str(self.output_dir),
            "strategy_id": self.strategy_key,
            "version_id": self.version_id,
            "version_dir_name": str(self.version_id),
        }


__all__ = ["ReportManager", "SavedRunArtifacts"]
