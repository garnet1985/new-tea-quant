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
from typing import Any, Dict, List, Optional, TextIO, Tuple

from core.infra.cmd_layout import CmdLayout
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
from core.modules.strategy.core.engines.shared.services.report_manager import (
    BaseReportManager,
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
class ReportManager(BaseReportManager):
    """枚举 run 产物编排（entity / slice 共用）。

    边界:
    - 负责: version 目录、runtime/performance/overall 落盘、worker buffer/flush、present
    - 不负责: BE 调度、枚举模拟逻辑、指纹索引
    - 调用方: EnumeratorPipeline / JobExecutor
    """

    strategy_key: str = ""
    version_id: int = 0
    strategy_path: str = ""
    runtime: RuntimeReport = field(init=False, repr=False)
    profiler: ProfilerReport = field(init=False, repr=False)
    overall: OverallReportHandle = field(init=False, repr=False)
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
        """分配 version 目录并写入 runtime_env.json / entity_ids.txt。

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

    # ── 生命周期（BaseReportManager）──

    def collect(self, item: Any) -> None:
        """主进程：收集 BE job report 性能样本。"""
        self.profiler.collect(item)

    def summarize(self) -> OverallReportHandle:
        """构建 performance + overall（落盘前）。"""
        self.profiler.build_from_run(
            self._finalize_run_result,
            entity_count=self._finalize_entity_count,
            opportunities_count=self._finalize_opportunities_count,
            performance_config=self._finalize_performance_config,
        )
        return self.overall.build(total_entities=self._finalize_entity_count)

    def save(self) -> SavedRunArtifacts:
        """写 performance.json + overall_report.json。"""
        performance_path = self.profiler.save()
        overall_report_path = self.overall.save()
        artifacts = SavedRunArtifacts(
            performance_path=performance_path,
            overall_report_path=overall_report_path,
            runtime_env_path=self.output_dir / RuntimeEnv.RUNTIME_ENV_FILE,
            entity_ids_path=self.output_dir / RuntimeEnv.ENTITY_IDS_FILE,
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

    # ── 展示（CLI / UI）──

    def present(self, stream: Optional[TextIO] = None) -> None:
        """CLI 终局摘要：机会能力为主，性能只留一行速览。"""
        out = stream or sys.stdout
        icon = CmdLayout.icon.get
        runtime = self.runtime.load()
        period = runtime.get("period") or {}
        mode = str(runtime.get("execution_mode") or "").strip() or "-"
        entity_count = int(runtime.get("entity_count") or 0)
        if entity_count <= 0:
            entity_count = len(runtime.get("entity_ids") or [])

        CmdLayout.title.print_banner(
            f"{icon('search')} 枚举报告",
            stream=out,
        )
        print(
            f"{icon('gear')} {runtime.get('strategy_key', self.strategy_key)} "
            f"v{runtime.get('version_id', self.version_id)}  "
            f"{icon('calendar')} {period.get('start_date', '')}~{period.get('end_date', '')}  "
            f"{icon('blue_dot')} {mode}  "
            f"entities={entity_count}",
            file=out,
            flush=True,
        )
        path = runtime.get("strategy_path") or self.strategy_path or "-"
        print(f"   path={path}", file=out, flush=True)

        CmdLayout.separator.print_line(width=60, stream=out)
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

        CmdLayout.separator.print_line(width=60, stream=out)
        CmdLayout.title.print_section(f"{icon('clock')} 性能", stream=out)
        elapsed = float(
            glance.get("total_sec_spent") or summary.get("elapsed_seconds") or 0.0
        )
        plan = dict(glance.get("plan") or {}) if glance else {}
        batches = dict(glance.get("job_batches") or {}) if glance else {}
        print(
            f"{icon('rocket')} {elapsed:.2f}s  "
            f"saved={glance.get('saved_sec', plan.get('saved_sec', '?'))}s  "
            f"parallelism≈{glance.get('parallelism', plan.get('parallelism', plan.get('speedup', '?')))}x  "
            f"jobs={batches.get('success', '?')}/{batches.get('total', '?')}",
            file=out,
            flush=True,
        )
        where = dict(
            (glance.get("time_distribution") or glance.get("time_share") or {})
            if glance
            else {}
        )
        time_buckets = self._time_distribution_buckets(where)
        if time_buckets:
            CmdLayout.bar_chart.print(
                time_buckets,
                title=f"{icon('ongoing')} 时间占比",
                width=24,
                stream=out,
            )

        CmdLayout.separator.print_line(width=60, stream=out)
        print(f"{icon('info')} 产物: {self.output_dir}", file=out, flush=True)

    @staticmethod
    def _time_distribution_buckets(where: Dict[str, Any]) -> List[Tuple[str, float]]:
        """Build bar-chart buckets from quick_summary time_distribution."""
        if not where:
            return []
        buckets: List[Tuple[str, float]] = []
        if where.get("planning") or where.get("load_data") or where.get("read"):
            mid_key = "read" if where.get("read") else "load_data"
            mid_label = "read" if where.get("read") else "load"
            for key, label in (
                ("planning", "plan"),
                (mid_key, mid_label),
                ("compute", "compute"),
                ("report", "report"),
            ):
                block = dict(where.get(key) or {})
                try:
                    pct = float(block.get("pct") or 0.0)
                except (TypeError, ValueError):
                    pct = 0.0
                buckets.append((label, pct))
            return buckets
        for key, label in (
            ("load_data_pct", "load"),
            ("strategy_pct", "strategy"),
        ):
            if key not in where:
                continue
            try:
                pct = float(where.get(key) or 0.0)
            except (TypeError, ValueError):
                pct = 0.0
            buckets.append((label, pct))
        return buckets

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
