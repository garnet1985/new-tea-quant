"""价格因子 Pipeline — enum 产物 → BE 回放 → price_factor 报告。

本文件:
- PriceFactorPipeline: load_enum_data → window → jobs → BE → ReportManager.finalize
  边界: 负责 price step 编排；不负责指纹缓存、legacy CSV 格式、tick 回放细节（PriceFactorJobExecutor）
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from core.modules.backtest_engine import BacktestEngine
from core.modules.strategy.core.services.artifacts import EnumerateStore
from core.modules.strategy.core.engines.price_factor.executor import PriceFactorJobExecutor
from core.modules.strategy.core.engines.price_factor.job_builder import PriceFactorJobBuilder
from core.modules.strategy.core.engines.price_factor.report_manager import ReportManager
from core.modules.strategy.core.engines.price_factor.timeline import resolve_simulation_window
from core.modules.strategy.core.services.progress import PipelineProgress

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.shared.data_class.simulate_session import SimulateSession

_PROGRESS_PIPELINE = "price"


class PriceFactorPipeline:
    """价格因子统一编排入口。"""

    @classmethod
    def run(cls, ctx: "SimulateSession") -> Dict[str, Any]:
        return cls.run_by_steps(ctx)

    @classmethod
    def run_by_steps(cls, ctx: "SimulateSession") -> Dict[str, Any]:
        """按步骤串起各步，返回本 step 的 report dict。"""
        drive = PipelineProgress.drives_pipeline(_PROGRESS_PIPELINE)
        if drive:
            PipelineProgress.enter_step_bound("load")
        data = cls.load_enum_data(ctx)
        start, end = cls.resolve_window(data)
        report = ReportManager.begin(ctx, data, start=start, end=end)
        if drive:
            PipelineProgress.complete_step_bound("load")
            PipelineProgress.enter_step_bound("dispatch")
        jobs = cls.build_jobs(data, report=report)
        if drive:
            PipelineProgress.complete_step_bound("dispatch")
            PipelineProgress.enter_step_bound("execute")
        run_result = cls.execute_backtest(jobs, start=start, end=end, data=data)
        if drive:
            PipelineProgress.complete_step_bound("execute")
            PipelineProgress.enter_step_bound("report")
        out = report.finalize(run_result, data=data)
        if drive:
            PipelineProgress.complete_step_bound("report")
        return out

    @classmethod
    def load_enum_data(cls, ctx: "SimulateSession") -> EnumerateStore:
        """解析 enum version 目录，加载 runtime + entity_ids（不读 CSV）。"""
        if ctx.enum_version is None or not str(ctx.enum_version).strip():
            raise ValueError("SimulateSession.enum_version 不能为空")
        version_id = str(ctx.enum_version).strip()
        return EnumerateStore.resolve(
            ctx.strategy_folder, version_id=version_id
        )

    @classmethod
    def resolve_window(cls, data: EnumerateStore) -> Tuple[str, str]:
        """枚举 runtime period → 已 resolve 的 simulation window。"""
        return resolve_simulation_window(data)

    @classmethod
    def build_jobs(
        cls,
        data: EnumerateStore,
        *,
        report: ReportManager,
    ) -> List[Dict[str, Any]]:
        """组装 BacktestEngine entity_based bundle jobs。"""
        return PriceFactorJobBuilder.build_jobs(data, report=report)

    @classmethod
    def execute_backtest(
        cls,
        jobs: List[Dict[str, Any]],
        *,
        start: str,
        end: str,
        data: EnumerateStore,
    ) -> Any:
        """BE 自管调度；``start``/``end`` window 必传；钩子仅 ``PriceFactorJobExecutor.build_run_callbacks()``。"""
        if not jobs:
            return None

        strategy_key = str(data.runtime.strategy_key or data.version_id).strip()
        return BacktestEngine.entity_based.run(
            jobs=jobs,
            start=start,
            end=end,
            callbacks=PriceFactorJobExecutor.build_run_callbacks(),
            task_name=f"price_factor_{strategy_key}",
        )


__all__ = ["PriceFactorPipeline"]
