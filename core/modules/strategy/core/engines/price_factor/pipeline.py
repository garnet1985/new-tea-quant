"""价格因子 Pipeline — enum 产物 → BE 回放 → price_factor 报告。

本文件:
- PriceFactorPipeline: load_enum_data → window → jobs → BE → ReportManager.finalize
  边界: 负责 price step 编排；不负责指纹缓存、legacy CSV 格式、tick 回放细节（JobExecutor）
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from core.modules.backtest_engine import BacktestEngine
from core.modules.strategy.core.engines.shared.services.simulation_input.enum_loader import (
    EnumVersionData,
    load_enum_version,
    resolve_enum_version_dir,
)
from core.modules.strategy.core.engines.price_factor.executor import JobExecutor
from core.modules.strategy.core.engines.price_factor.job_builder import JobBuilder
from core.modules.strategy.core.engines.price_factor.report_manager import ReportManager
from core.modules.strategy.core.engines.price_factor.timeline import resolve_simulation_window

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.shared.data_class.simulate_session import SimulateSession


class PriceFactorPipeline:
    """价格因子统一编排入口。"""

    @classmethod
    def run(cls, ctx: "SimulateSession") -> Dict[str, Any]:
        return cls.run_by_steps(ctx)

    @classmethod
    def run_by_steps(cls, ctx: "SimulateSession") -> Dict[str, Any]:
        """按步骤串起各步，返回本 step 的 report dict。"""
        data = cls.load_enum_data(ctx)
        start, end = cls.resolve_window(data)
        report = ReportManager.begin(ctx, data, start=start, end=end)
        jobs = cls.build_jobs(data, report=report)
        run_result = cls.execute_backtest(jobs, start=start, end=end, data=data)
        return report.finalize(run_result, data=data)

    @classmethod
    def load_enum_data(cls, ctx: "SimulateSession") -> EnumVersionData:
        """解析 enum version 目录，加载 runtime + entity_ids（不读 CSV）。"""
        if ctx.enum_version is None or not str(ctx.enum_version).strip():
            raise ValueError("SimulateSession.enum_version 不能为空")
        version_id = str(ctx.enum_version).strip()
        output_dir = resolve_enum_version_dir(ctx.strategy_key, version_id)
        return load_enum_version(output_dir, version_id)

    @classmethod
    def resolve_window(cls, data: EnumVersionData) -> Tuple[str, str]:
        """枚举 runtime period → 已 resolve 的 simulation window。"""
        return resolve_simulation_window(data)

    @classmethod
    def build_jobs(
        cls,
        data: EnumVersionData,
        *,
        report: ReportManager,
    ) -> List[Dict[str, Any]]:
        """组装 BacktestEngine entity_based bundle jobs。"""
        return JobBuilder.build_jobs(data, report=report)

    @classmethod
    def execute_backtest(
        cls,
        jobs: List[Dict[str, Any]],
        *,
        start: str,
        end: str,
        data: EnumVersionData,
    ) -> Any:
        """BE 自管调度；``start``/``end`` window 必传；钩子仅 ``JobExecutor.build_run_callbacks()``。"""
        if not jobs:
            return None

        strategy_key = str(data.runtime.strategy_key or data.version_id).strip()
        return BacktestEngine.entity_based.run(
            jobs=jobs,
            start=start,
            end=end,
            callbacks=JobExecutor.build_run_callbacks(),
            task_name=f"price_factor_{strategy_key}",
        )


__all__ = ["PriceFactorPipeline"]
