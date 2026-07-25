"""价格回测 ReportManager — version 目录与产物落盘。

本文件:
- ReportManager: begin / collect / summarize / save / finalize / present
  边界: 负责 price_factor 落盘；不负责 BE 调度或 tick 回放
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TextIO, TYPE_CHECKING

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.price_factor.report_manager.investments import (
    EntityInvestments,
)
from core.modules.strategy.core.engines.price_factor.report_manager.overall_report import (
    OverallReport,
)
from core.modules.strategy.core.engines.price_factor.report_manager.report_consts import (
    ReportPaths,
)
from core.modules.strategy.core.engines.price_factor.report_manager.runtime_env import (
    PriceRuntimeEnv,
)
from core.modules.strategy.core.engines.shared.services.report_manager import (
    BaseReportManager,
)
from core.modules.strategy.core.services.data.simulation_output_recorder import (
    SimulationOutputRecorder,
)

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.shared.services.simulation_output.enum_source import EnumSource
    from core.modules.strategy.core.engines.shared.data_class.simulate_session import SimulateSession


@dataclass
class ReportManager(BaseReportManager):
    """价格回测产物编排。

    边界:
    - 负责: version 目录、runtime/overall/entity investments 落盘、返回 report dict
    - 不负责: BE 调度、tick 业务回放
    - 调用方: PriceFactorPipeline
    """

    strategy_key: str = ""
    strategy_path: str = ""
    version_id: int = 0
    runtime: PriceRuntimeEnv = field(default=None)  # type: ignore[assignment]
    entity_ids: List[str] = field(default_factory=list)
    _overall_payload: Dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    _run_result: Any = field(default=None, init=False, repr=False)
    _report_dict: Dict[str, Any] = field(default_factory=dict, init=False, repr=False)

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
            getattr(info, "unique_relative_path", "") or ctx.strategy_key or ""
        ).strip()
        if not strategy_path:
            raise ValueError("strategy_path 不能为空")

        root = ProjectContext.path.get_strategy_directory_simulation_price(strategy_path)
        output_dir, version_id = SimulationOutputRecorder.allocate_version_dir(
            strategy_path,
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

    def collect(self, item: Any) -> None:
        """可选：``(entity_id, rows)`` 写入 entity investments CSV。"""
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            return
        entity_id, rows = item[0], item[1]
        self.save_entity_investments(str(entity_id), list(rows or []))

    def summarize(self) -> Dict[str, Any]:
        """扫描 entity CSV → overall payload（未落盘）。"""
        self._overall_payload = OverallReport.build(
            self.output_dir,
            entity_ids=self.entity_ids,
            period=dict(self.runtime.period or {}),
            enum_version_id=self.runtime.enum_version_id,
        )
        return self._overall_payload

    def save(self) -> Dict[str, Any]:
        """写 overall + performance stub；组装可缓存 report dict。"""
        if not self._overall_payload:
            self.summarize()
        OverallReport.save_payload(self.output_dir, self._overall_payload)
        self._write_performance_stub(self._run_result)

        success = True
        run_result = self._run_result
        if run_result is not None:
            success = bool(getattr(run_result, "success", True))

        self._report_dict = {
            "success": success,
            "output_dir": str(self.output_dir),
            "version_id": int(self.version_id),
            "strategy_key": self.strategy_key,
            "strategy_path": self.strategy_path,
            "enum_version_id": self.runtime.enum_version_id,
            "period": dict(self.runtime.period or {}),
            "entity_count": len(self.entity_ids),
            "summary": self._overall_payload.get("summary") or {},
            "total_jobs": int(getattr(run_result, "total_jobs", 0) or 0),
            "completed_jobs": int(getattr(run_result, "completed_jobs", 0) or 0),
            "failed_jobs": int(getattr(run_result, "failed_jobs", 0) or 0),
            "elapsed_seconds": float(getattr(run_result, "elapsed_seconds", 0.0) or 0.0),
        }
        return self._report_dict

    def finalize(
        self,
        run_result: Any = None,
        *,
        data: Any = None,
        present: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """聚合 entities CSV → overall；返回可供缓存的 report dict。"""
        _ = data
        _ = kwargs
        self._run_result = run_result
        self.summarize()
        result = self.save()
        if present:
            self.present()
        return result

    def present(self, stream: Optional[TextIO] = None) -> None:
        out = stream or sys.stdout
        period = dict(self.runtime.period or {})
        summary = dict((self._report_dict or self._overall_payload or {}).get("summary") or {})
        if not summary and ReportPaths.overall_report_path(self.output_dir).is_file():
            try:
                summary = dict(
                    json.loads(
                        ReportPaths.overall_report_path(self.output_dir).read_text(
                            encoding="utf-8"
                        )
                    ).get("summary")
                    or {}
                )
            except Exception:
                summary = {}
        print(
            f"price: {self.strategy_key} v{self.version_id}  "
            f"path={self.strategy_path or '-'}  "
            f"entities={len(self.entity_ids)}  "
            f"period={period.get('start_date', '')}~{period.get('end_date', '')}",
            file=out,
            flush=True,
        )
        print(
            f"summary: investments={summary.get('total_investments', 0)}  "
            f"win={summary.get('total_win', 0)}  "
            f"loss={summary.get('total_loss', 0)}",
            file=out,
            flush=True,
        )
        print(f"产物目录: {self.output_dir}", file=out, flush=True)

    def save_entity_investments(
        self,
        entity_id: str,
        rows: List[Any],
    ) -> Path:
        """供 worker / tick 回放写入每股投资记录。"""
        return EntityInvestments.save(self.output_dir, entity_id, rows)

    def _write_performance_stub(self, run_result: Any) -> None:
        path = ReportPaths.performance_path(self.output_dir)
        payload = {
            "elapsed_seconds": float(getattr(run_result, "elapsed_seconds", 0.0) or 0.0)
            if run_result is not None
            else 0.0,
            "total_jobs": int(getattr(run_result, "total_jobs", 0) or 0)
            if run_result is not None
            else 0,
            "completed_jobs": int(getattr(run_result, "completed_jobs", 0) or 0)
            if run_result is not None
            else 0,
            "failed_jobs": int(getattr(run_result, "failed_jobs", 0) or 0)
            if run_result is not None
            else 0,
        }
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


__all__ = ["ReportManager"]
