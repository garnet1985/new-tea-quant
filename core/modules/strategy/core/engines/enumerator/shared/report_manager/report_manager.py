"""枚举 run 产物编排：version 目录、runtime / performance / overall 落盘与展示。"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.enumerator.shared.report_manager.overall_report import (
    OverallReportHandle,
)
from core.modules.strategy.core.engines.enumerator.shared.report_manager.profiler import (
    ProfilerReport,
)
from core.modules.strategy.core.engines.enumerator.shared.report_manager.runtime_snapshot import (
    RuntimeReport,
    RuntimeSnapshot,
)
from core.modules.strategy.core.engines.enumerator.shared.report_manager.stock_investments import (
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
    performance_path: Path
    overall_report_path: Path
    runtime_env_path: Path
    entity_ids_path: Path


@dataclass
class ReportManager:
    """一次 enum run 的产物管理者（对外唯一入口）。"""

    output_dir: Path
    strategy_key: str
    version_id: int
    runtime: RuntimeReport = field(init=False, repr=False)
    profiler: ProfilerReport = field(init=False, repr=False)
    overall: OverallReportHandle = field(init=False, repr=False)
    investments: InvestmentsReport = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
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
    ) -> "ReportManager":
        """分配 version 目录并写入 0_runtime_env.json / 0_entity_ids.txt。"""
        root = ProjectContext.path.get_strategy_directory_simulation_enum(strategy_key)
        output_dir, version_id = SimulationOutputRecorder.allocate_version_dir(
            strategy_key,
            root,
        )
        manager = cls(
            output_dir=output_dir,
            strategy_key=strategy_key,
            version_id=int(version_id),
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
            runtime_env_path=self.output_dir / RuntimeSnapshot.RUNTIME_ENV_FILE,
            entity_ids_path=self.output_dir / RuntimeSnapshot.ENTITY_IDS_FILE,
        )

    # ── 展示（CLI / UI）──

    def present(self, stream: Optional[TextIO] = None) -> None:
        out = stream or sys.stdout
        runtime = self.runtime.load()
        period = runtime.get("period") or {}
        print(
            f"run: {runtime.get('strategy_key', self.strategy_key)} "
            f"v{runtime.get('version_id', self.version_id)}  "
            f"entities={len(runtime.get('entity_ids') or [])}  "
            f"period={period.get('start_date', '')}~{period.get('end_date', '')}",
            file=out,
            flush=True,
        )
        self.overall.present(stream=out)
        summary = self.profiler.summary()
        print(
            f"性能: elapsed={summary.get('elapsed_seconds', 0):.2f}s  "
            f"jobs={summary.get('completed_jobs', 0)}/{summary.get('total_jobs', 0)}  "
            f"parallelism={summary.get('parallelism_factor', 0)}",
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
