"""枚举 run 产物编排（version 目录、三报告稿 + 引擎 artifact）。

报告稿（CMD / UI / DB 同一契约）:
- overall_report.json
- entity_list.json
- performance.json

引擎 artifact（非报告正文）:
- runtime_env.json / entity_ids.txt
- entities/*.csv
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO

from core.infra.cmd_layout import CmdLayout
from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.enumerator.common.report_manager.entity_list_report import (
    EntityListReport,
    EntityListReportHandle,
)
from core.modules.strategy.core.engines.enumerator.common.report_manager.overall_report import (
    OverallReport,
    OverallReportHandle,
)
from core.modules.strategy.core.engines.enumerator.common.report_manager.profiler import (
    ProfilerPerformance,
    ProfilerReport,
)
from core.modules.strategy.core.engines.enumerator.common.report_manager.report_scan import (
    EnumCsvScan,
)
from core.modules.strategy.core.engines.enumerator.common.artifacts.runtime_env import (
    RuntimeEnv,
)
from core.modules.strategy.core.engines.enumerator.common.report_manager.runtime_snapshot import (
    RuntimeReport,
)
from core.modules.strategy.core.engines.enumerator.common.report_manager.stock_investments import (
    InvestmentsReport,
)
from core.modules.strategy.core.engines.shared.services.report_manager import (
    BaseReportManager,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    ENTITY_LIST_FILE,
    OVERALL_REPORT_FILE,
    PERFORMANCE_FILE,
)
from core.modules.strategy.core.services.data.simulation_output_recorder import (
    SimulationOutputRecorder,
)


@dataclass
class SavedRunArtifacts:
    """一次 finalize 写盘后的报告稿路径。"""

    overall_report_path: Path
    entity_list_path: Path
    performance_path: Path


@dataclass
class ReportManager(BaseReportManager):
    """枚举 run 产物编排（entity / slice 共用）。

    边界:
    - 负责: version 目录、三报告落盘、worker buffer/flush、present
    - 不负责: BE 调度、枚举模拟逻辑、指纹索引
    - 调用方: EnumeratorPipeline / JobExecutor
    """

    strategy_key: str = ""
    version_id: int = 0
    strategy_path: str = ""
    runtime: RuntimeReport = field(init=False, repr=False)
    profiler: ProfilerReport = field(init=False, repr=False)
    overall: OverallReportHandle = field(init=False, repr=False)
    entity_list: EntityListReportHandle = field(init=False, repr=False)
    investments: InvestmentsReport = field(init=False, repr=False)
    _finalize_entity_count: int = field(default=0, init=False, repr=False)
    _finalize_run_result: Any = field(default=None, init=False, repr=False)
    _finalize_opportunities_count: int = field(default=0, init=False, repr=False)
    _finalize_performance_config: Optional[Dict[str, Any]] = field(
        default=None, init=False, repr=False
    )
    _saved_artifacts: Optional[SavedRunArtifacts] = field(
        default=None, init=False, repr=False
    )

    def __post_init__(self) -> None:
        super().__post_init__()
        self.strategy_path = str(self.strategy_path or self.strategy_key or "").strip()
        self.runtime = RuntimeReport(self)
        self.profiler = ProfilerReport(self)
        self.overall = OverallReportHandle(self)
        self.entity_list = EntityListReportHandle(self)
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
        strategy_folder: Optional[Path] = None,
    ) -> "ReportManager":
        """分配 version 目录并写入 runtime_env.json / entity_ids.txt。

        结果根基于 discovered ``strategy_folder``（``{folder}/results/simulations/enum``），
        不再用相对名重拼 userspace/strategies。
        """
        path_id = str(strategy_path or strategy_key or "").strip()
        folder = Path(strategy_folder) if strategy_folder is not None else None
        if folder is None or not str(folder):
            if not path_id:
                raise ValueError("strategy_folder / strategy_path / strategy_key 不能为空")
            root = ProjectContext.path.get_strategy_directory_simulation_enum(path_id)
        else:
            root = ProjectContext.path.get_strategy_directory_simulation_enum(folder)
        output_dir, version_id = SimulationOutputRecorder.allocate_version_dir(
            path_id or str(folder),
            root,
        )
        manager = cls(
            output_dir=output_dir,
            strategy_key=str(strategy_key or path_id).strip(),
            version_id=int(version_id),
            strategy_path=path_id or str(folder),
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

    # ── 生命周期（BaseReportManager）──

    def collect(self, item: Any) -> None:
        """主进程：收集 BE job report 性能样本。"""
        self.profiler.collect(item)

    def summarize(self) -> OverallReportHandle:
        """构建 performance + overall + entity_list（落盘前）。"""
        self.profiler.build_from_run(
            self._finalize_run_result,
            entity_count=self._finalize_entity_count,
            opportunities_count=self._finalize_opportunities_count,
            performance_config=self._finalize_performance_config,
        )
        scan = EnumCsvScan.collect(
            self.output_dir,
            total_entities=self._finalize_entity_count,
            strategy_key=self.strategy_key,
            version_id=self.version_id,
        )
        self.overall.build_from_scan(scan)
        self.entity_list.build_from_scan(scan)
        return self.overall

    def save(self) -> SavedRunArtifacts:
        """写三份报告稿。"""
        performance_path = self.profiler.save()
        overall_report_path = self.overall.save()
        entity_list_path = self.entity_list.save()
        artifacts = SavedRunArtifacts(
            overall_report_path=overall_report_path,
            entity_list_path=entity_list_path,
            performance_path=performance_path,
        )
        self._saved_artifacts = artifacts
        return artifacts

    def finalize(
        self,
        run_result: Any = None,
        *,
        entity_count: int = 0,
        opportunities_count: int = 0,
        performance_config: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> SavedRunArtifacts:
        _ = kwargs
        self._finalize_run_result = run_result
        self._finalize_entity_count = int(entity_count or 0)
        self._finalize_opportunities_count = int(opportunities_count or 0)
        self._finalize_performance_config = performance_config
        self.summarize()
        return self.save()

    # ── 展示（CLI）──

    def present(self, stream: Optional[TextIO] = None) -> None:
        """CMD：依次 present 三份报告稿（不再拼 runtime / 扫 CSV）。"""
        out = stream or sys.stdout
        icon = CmdLayout.icon.get

        OverallReport.load(self.output_dir).present(stream=out)
        CmdLayout.separator.print_line(width=60, stream=out)
        EntityListReport.load(self.output_dir).present(stream=out)
        CmdLayout.separator.print_line(width=60, stream=out)
        try:
            ProfilerPerformance.load(self.output_dir).present(stream=out)
        except Exception:
            CmdLayout.title.print_section(f"{icon('clock')} 性能", stream=out)
            print(f"{icon('warning')} 缺少 {PERFORMANCE_FILE}", file=out, flush=True)
        CmdLayout.separator.print_line(width=60, stream=out)
        print(f"{icon('info')} 产物: {self.output_dir}", file=out, flush=True)
        print(
            f"   reports: {OVERALL_REPORT_FILE}, {ENTITY_LIST_FILE}, {PERFORMANCE_FILE}",
            file=out,
            flush=True,
        )

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
