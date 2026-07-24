"""价格回测 ReportManager — version 目录与产物落盘。

本文件:
- ReportManager: begin / merge worker CSV / finalize → report dict
  边界: 负责 price_factor 落盘；不负责 BE 调度或 tick 回放（类级边界见 docstring）
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, TYPE_CHECKING

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
from core.modules.strategy.core.services.data.simulation_output_recorder import (
    SimulationOutputRecorder,
)

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.price_factor.enum_data import EnumVersionData
    from core.modules.strategy.core.engines.shared.data_class.simulate_session import SimulateSession


@dataclass
class ReportManager:
    """价格回测产物编排。

    边界:
    - 负责: version 目录、runtime/overall/entity investments 落盘、返回 report dict
    - 不负责: BE 调度、tick 业务回放
    - 调用方: PriceFactorPipeline
    """

    output_dir: Path
    strategy_key: str
    strategy_path: str
    version_id: int
    runtime: PriceRuntimeEnv
    entity_ids: List[str] = field(default_factory=list)

    @classmethod
    def begin(
        cls,
        ctx: "SimulateSession",
        data: "EnumVersionData",
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

    def finalize(
        self,
        run_result: Any,
        *,
        data: "EnumVersionData",
    ) -> Dict[str, Any]:
        """聚合 entities CSV → overall；返回可供缓存的 report dict。"""
        _ = data
        overall = OverallReport.build_and_save(
            self.output_dir,
            entity_ids=self.entity_ids,
            period=dict(self.runtime.period or {}),
            enum_version_id=self.runtime.enum_version_id,
        )
        self._write_performance_stub(run_result)

        success = True
        if run_result is not None:
            success = bool(getattr(run_result, "success", True))

        return {
            "success": success,
            "output_dir": str(self.output_dir),
            "version_id": int(self.version_id),
            "strategy_key": self.strategy_key,
            "strategy_path": self.strategy_path,
            "enum_version_id": self.runtime.enum_version_id,
            "period": dict(self.runtime.period or {}),
            "entity_count": len(self.entity_ids),
            "summary": overall.get("summary") or {},
            "total_jobs": int(getattr(run_result, "total_jobs", 0) or 0),
            "completed_jobs": int(getattr(run_result, "completed_jobs", 0) or 0),
            "failed_jobs": int(getattr(run_result, "failed_jobs", 0) or 0),
            "elapsed_seconds": float(getattr(run_result, "elapsed_seconds", 0.0) or 0.0),
        }

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
