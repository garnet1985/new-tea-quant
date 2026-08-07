"""价格回测 ReportManager — 三报告稿 + 引擎 artifact 编排。

报告稿（CMD / UI / DB 同一契约）:
- overall_report.json
- entity_list.json
- performance.json

引擎 artifact（非报告正文）:
- runtime_env.json / entity_ids.txt
- entities/*_investments.csv
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, TYPE_CHECKING

from core.infra.cmd_layout import CmdLayout
from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.price_factor.report_manager.entity_list_report import (
    EntityListReport,
    EntityListReportHandle,
)
from core.modules.strategy.core.engines.price_factor.report_manager.overall_report import (
    OverallReport,
    OverallReportHandle,
)
from core.modules.strategy.core.engines.price_factor.report_manager.performance_report import (
    PerformanceReport,
    PerformanceReportHandle,
)
from core.modules.strategy.core.engines.price_factor.report_manager.report_consts import (
    ReportPaths,
)
from core.modules.strategy.core.engines.price_factor.report_manager.report_scan import (
    PriceCsvScan,
)
from core.modules.strategy.core.engines.price_factor.report_manager.runtime_env import (
    PriceRuntimeEnv,
)
from core.modules.strategy.core.engines.shared.services.report_manager import (
    BaseReportManager,
)
from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    ENTITY_LIST_FILE,
    OVERALL_REPORT_FILE,
    PERFORMANCE_FILE,
)
from core.modules.strategy.core.services.data.simulation_output_recorder import (
    SimulationOutputRecorder,
)

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.shared.services.simulation_output.enum_source import (
        EnumSource,
    )
    from core.modules.strategy.core.engines.shared.data_class.simulate_session import (
        SimulateSession,
    )


@dataclass
class SavedRunArtifacts:
    """一次 finalize 写盘后的报告稿路径。"""

    overall_report_path: Path
    entity_list_path: Path
    performance_path: Path


@dataclass
class ReportManager(BaseReportManager):
    """价格回测产物编排。"""

    strategy_key: str = ""
    strategy_path: str = ""
    version_id: int = 0
    runtime: PriceRuntimeEnv = field(default=None)  # type: ignore[assignment]
    entity_ids: List[str] = field(default_factory=list)
    overall: OverallReportHandle = field(init=False, repr=False)
    entity_list: EntityListReportHandle = field(init=False, repr=False)
    performance: PerformanceReportHandle = field(init=False, repr=False)
    _run_result: Any = field(default=None, init=False, repr=False)
    _saved_artifacts: Optional[SavedRunArtifacts] = field(
        default=None, init=False, repr=False
    )

    def __post_init__(self) -> None:
        super().__post_init__()
        self.overall = OverallReportHandle(self)
        self.entity_list = EntityListReportHandle(self)
        self.performance = PerformanceReportHandle(self)

    @classmethod
    def begin(
        cls,
        ctx: "SimulateSession",
        data: "EnumSource",
        *,
        start: str,
        end: str,
    ) -> "ReportManager":
        """分配 price_factor version 目录并写入 runtime / entity_ids。"""
        info = ctx.strategy_info
        strategy_key = str(getattr(info, "key", "") or "").strip()
        strategy_path = str(
            getattr(info, "unique_relative_path", "") or getattr(ctx, "strategy_key", "") or ""
        ).strip()
        folder = getattr(ctx, "strategy_folder", None)
        if folder is None:
            resolved = getattr(info, "resolved_folder", None)
            if callable(resolved):
                folder = resolved()
            elif getattr(info, "folder", None) is not None:
                folder = Path(info.folder)
            else:
                from core.infra.project_context import ProjectContext

                folder = ProjectContext.path.coerce_strategy_folder(
                    strategy_path or strategy_key
                )
        if folder is None or not str(folder):
            raise ValueError("strategy_folder 不能为空")

        root = ProjectContext.path.get_strategy_simulation_price(folder)
        output_dir, version_id = SimulationOutputRecorder.allocate_version_dir(
            strategy_path or strategy_key or str(folder),
            root,
        )
        entity_ids = list(data.entity_ids)
        runtime = PriceRuntimeEnv(
            strategy_key=strategy_key or strategy_path,
            strategy_path=strategy_path,
            version_id=int(version_id),
            enum_version_id=str(data.version_id),
            enum_output_dir=str(data.output_dir),
            settings_fp=str(ctx.settings_fp or ""),
            env_fp=str(ctx.env_fp or ""),
            period={"start_date": start, "end_date": end},
            entity_ids=entity_ids,
            market_profile=str(data.runtime.market_profile or "").strip(),
        )
        runtime.save(output_dir)
        ReportPaths.entities_dir(output_dir).mkdir(parents=True, exist_ok=True)

        return cls(
            output_dir=output_dir,
            strategy_key=runtime.strategy_key,
            strategy_path=strategy_path,
            version_id=int(version_id),
            runtime=runtime,
            entity_ids=entity_ids,
        )

    @classmethod
    def from_output_dir(cls, output_dir: Path) -> "ReportManager":
        runtime = PriceRuntimeEnv.load(output_dir)
        return cls(
            output_dir=Path(output_dir),
            strategy_key=runtime.strategy_key,
            strategy_path=runtime.strategy_path or runtime.strategy_key,
            version_id=int(runtime.version_id),
            runtime=runtime,
            entity_ids=list(runtime.entity_ids),
        )

    def summarize(self) -> OverallReportHandle:
        """构建 performance + overall + entity_list（落盘前）。"""
        self.performance.build_from_run(self._run_result)
        scan = PriceCsvScan.collect(
            self.output_dir,
            entity_ids=list(self.entity_ids),
            strategy_key=self.strategy_key,
            version_id=self.version_id,
        )
        self.overall.build_from_scan(scan)
        self.entity_list.build_from_scan(scan)
        return self.overall

    def save(self) -> SavedRunArtifacts:
        """写三份报告稿。"""
        performance_path = self.performance.save()
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
        data: Any = None,
        present: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """聚合 CSV → 三稿；返回可供缓存的 UI 契约 dict。"""
        _ = data
        _ = kwargs
        self._run_result = run_result
        self.summarize()
        self.save()
        result = self.to_cache_dict()
        if present:
            self.present()
        return result

    def to_cache_dict(self) -> Dict[str, Any]:
        """DB ``result_report.price_factor`` / pipeline 返回值。"""
        overall = self.overall.report
        if overall is None:
            overall = OverallReport.load(self.output_dir)
        perf = None
        try:
            perf = PerformanceReport.load(self.output_dir)
        except Exception:
            perf = None
        success = True
        if self._run_result is not None:
            success = bool(getattr(self._run_result, "success", True))
        payload = overall.to_ui_dict()
        payload["success"] = success
        payload["output_dir"] = str(self.output_dir)
        payload["summary"] = overall.summary.to_dict()
        if perf is not None:
            payload["elapsed_seconds"] = perf.elapsed_seconds
            payload["total_jobs"] = perf.total_jobs
            payload["completed_jobs"] = perf.completed_jobs
            payload["failed_jobs"] = perf.failed_jobs
        return payload

    def present(self, stream: Optional[TextIO] = None) -> None:
        """CMD：依次 present 三份报告稿。"""
        out = stream or sys.stdout
        icon = CmdLayout.icon.get
        OverallReport.load(self.output_dir).present(stream=out)
        CmdLayout.separator.print_line(width=60, stream=out)
        EntityListReport.load(self.output_dir).present(stream=out)
        CmdLayout.separator.print_line(width=60, stream=out)
        try:
            PerformanceReport.load(self.output_dir).present(stream=out)
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


__all__ = ["ReportManager", "SavedRunArtifacts"]
