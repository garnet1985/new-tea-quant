"""Portfolio ReportManager — 三报告稿 + 引擎 artifact。

报告稿（CMD / UI / DB 同一契约）:
- overall_report.json
- entity_list.json
- performance.json

引擎 artifact（非报告正文）:
- runtime_env.json
- trades.json / equity_curve.json
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, TYPE_CHECKING

from core.infra.cmd_layout import CmdLayout
from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.portfolio.report_manager.entity_list_report import (
    EntityListReport,
    EntityListReportHandle,
)
from core.modules.strategy.core.engines.portfolio.report_manager.overall_report import (
    OverallReport,
    OverallReportHandle,
)
from core.modules.strategy.core.engines.portfolio.report_manager.performance_report import (
    PerformanceReport,
    PerformanceReportHandle,
)
from core.modules.strategy.core.engines.portfolio.report_manager.report_consts import (
    ReportPaths,
)
from core.modules.strategy.core.engines.portfolio.report_manager.runtime_env import (
    PortfolioRuntimeEnv,
)
from core.modules.strategy.core.engines.shared.services.report_manager import (
    BaseReportManager,
)
from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    ENTITY_LIST_FILE,
    OVERALL_REPORT_FILE,
    PERFORMANCE_FILE,
)
from core.modules.strategy.core.engines.shared.services.simulation_output.io import (
    ArtifactIO,
)
from core.modules.strategy.core.services.data.simulation_output_recorder import (
    SimulationOutputRecorder,
)

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.portfolio.simulator import PortfolioSimResult
    from core.modules.strategy.core.engines.shared.data_class.simulate_session import (
        SimulateSession,
    )
    from core.modules.strategy.core.engines.shared.services.simulation_output.enum_source import (
        EnumSource,
    )

_DEFAULT_MARKET_PROFILE = "china_a_stock"


@dataclass
class SavedRunArtifacts:
    overall_report_path: Path
    entity_list_path: Path
    performance_path: Path


@dataclass
class ReportManager(BaseReportManager):
    """Portfolio 产物编排。"""

    strategy_key: str = ""
    strategy_path: str = ""
    version_id: int = 0
    enum_version_id: str = ""
    market_profile: str = _DEFAULT_MARKET_PROFILE
    overall: OverallReportHandle = field(init=False, repr=False)
    entity_list: EntityListReportHandle = field(init=False, repr=False)
    performance: PerformanceReportHandle = field(init=False, repr=False)
    _sim: Any = field(default=None, init=False, repr=False)
    _period: Dict[str, str] = field(default_factory=dict, init=False, repr=False)
    _save_trades: bool = field(default=True, init=False, repr=False)
    _save_equity_curve: bool = field(default=True, init=False, repr=False)
    _elapsed_seconds: float = field(default=0.0, init=False, repr=False)
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
    ) -> "ReportManager":
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
                folder = ProjectContext.path.coerce_strategy_folder(
                    strategy_path or strategy_key
                )
        if folder is None or not str(folder):
            raise ValueError("strategy_folder 不能为空")

        root = ProjectContext.path.get_strategy_simulation_portfolio_directory(folder)
        output_dir, version_id = SimulationOutputRecorder.allocate_version_dir(
            strategy_path or strategy_key or str(folder),
            root,
        )
        market_profile = (
            str(data.runtime.market_profile or "").strip() or _DEFAULT_MARKET_PROFILE
        )
        runtime = PortfolioRuntimeEnv(
            strategy_key=strategy_key or strategy_path,
            strategy_path=strategy_path,
            version_id=int(version_id),
            enum_version_id=str(data.version_id),
            enum_output_dir=str(data.output_dir),
            settings_fp=str(ctx.settings_fp or ""),
            env_fp=str(ctx.env_fp or ""),
            period={
                "start_date": data.start_date,
                "end_date": data.end_date,
            },
            entity_ids=list(data.entity_ids),
            market_profile=market_profile,
        )
        runtime.save(output_dir)
        return cls(
            output_dir=output_dir,
            strategy_key=runtime.strategy_key,
            strategy_path=strategy_path,
            version_id=int(version_id),
            enum_version_id=str(data.version_id),
            market_profile=market_profile,
        )

    @classmethod
    def from_output_dir(cls, output_dir: Path) -> "ReportManager":
        runtime = PortfolioRuntimeEnv.load(output_dir)
        mgr = cls(
            output_dir=Path(output_dir),
            strategy_key=runtime.strategy_key,
            strategy_path=runtime.strategy_path or runtime.strategy_key,
            version_id=int(runtime.version_id),
            enum_version_id=str(runtime.enum_version_id),
            market_profile=str(runtime.market_profile or _DEFAULT_MARKET_PROFILE),
        )
        mgr._period = dict(runtime.period or {})
        return mgr

    def summarize(self) -> OverallReportHandle:
        sim = self._sim
        if sim is None:
            raise RuntimeError("portfolio summarize 需要先 finalize(sim)")
        self.performance.build(elapsed_seconds=self._elapsed_seconds)
        self.overall.build_from_sim(sim)
        self.entity_list.build_from_trades(list(sim.trades or []))
        return self.overall

    def save(self) -> SavedRunArtifacts:
        sim = self._sim
        if sim is None:
            raise RuntimeError("portfolio save 需要先 finalize(sim)")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if self._save_trades:
            ArtifactIO.write_json(
                ReportPaths.trades_path(self.output_dir),
                [t.to_dict() for t in sim.trades],
            )
        if self._save_equity_curve:
            ArtifactIO.write_json(
                ReportPaths.equity_curve_path(self.output_dir),
                list(sim.equity_curve),
            )
        performance_path = self.performance.save()
        overall_report_path = self.overall.save()
        entity_list_path = self.entity_list.save()
        artifacts = SavedRunArtifacts(
            overall_report_path=overall_report_path,
            entity_list_path=entity_list_path,
            performance_path=performance_path,
        )
        self._saved_artifacts = artifacts
        self._trace_feature_run()
        return artifacts

    def _trace_feature_run(self) -> None:
        snap = self.performance._report
        if snap is None:
            return
        mode = "unknown"
        entity_count = 0
        try:
            runtime = PortfolioRuntimeEnv.load(self.output_dir)
            entity_count = len(runtime.entity_ids or [])
            enum_dir = str(runtime.enum_output_dir or "").strip()
            if enum_dir:
                from core.modules.strategy.core.engines.enumerator.common.artifacts.runtime_env import (
                    RuntimeEnv,
                )

                mode = (
                    str(RuntimeEnv.load(Path(enum_dir)).execution_mode or "")
                    .strip()
                    .lower()
                    or "unknown"
                )
        except Exception:
            pass
        success = True
        if self._sim is not None:
            success = bool(getattr(self._sim, "success", True))
        self.trace_feature_run(
            action="strategy.portfolio",
            key=str(self.strategy_key or ""),
            mode=mode,
            success=success,
            elapsed_seconds=float(snap.elapsed_seconds or 0.0),
            entity_count=int(entity_count),
        )

    def finalize(
        self,
        sim: "PortfolioSimResult",
        *,
        period: Optional[Dict[str, str]] = None,
        save_trades: bool = True,
        save_equity_curve: bool = True,
        present: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        _ = kwargs
        started = time.perf_counter()
        self._sim = sim
        self._period = dict(period or {})
        self._save_trades = bool(save_trades)
        self._save_equity_curve = bool(save_equity_curve)
        self.summarize()
        self._elapsed_seconds = float(time.perf_counter() - started)
        self.performance.build(elapsed_seconds=self._elapsed_seconds)
        self.save()
        result = self.to_cache_dict()
        if present:
            self.present()
        return result

    def to_cache_dict(self) -> Dict[str, Any]:
        overall = self.overall.report
        if overall is None:
            overall = OverallReport.load(self.output_dir)
        entity = self.entity_list.report
        if entity is None:
            try:
                entity = EntityListReport.load(self.output_dir)
            except Exception:
                entity = None
        success = True
        if self._sim is not None:
            success = bool(getattr(self._sim, "success", True))
        payload = overall.to_ui_dict()
        payload["success"] = success
        payload["output_dir"] = str(self.output_dir)
        payload["summary"] = overall.summary.to_dict()
        if entity is not None:
            payload["stockRows"] = entity.to_ui_rows()
        return payload

    def present(self, stream: Optional[TextIO] = None) -> None:
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
