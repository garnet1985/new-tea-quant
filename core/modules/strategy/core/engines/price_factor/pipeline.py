"""价格因子 Pipeline — 主流程骨架（逐步落地）。

主流程::

    1. load_enum_data       — 读 enum version 的 runtime + entity_ids（不读 entities CSV）
    2. resolve_window       — 枚举 period start–end（已 resolve；传给 BE）
    3. JobBuilder.build_jobs — bundle：entity ids + enum_dir；CSV 在 worker 读
    4. BacktestEngine.entity_based — 调度自管；callbacks=JobExecutor；
       start/end window 必传（BE 校验 data.json 并建轴）
    5. ReportManager        — （待实现）新格式落盘

Worker 输入契约（仅新格式）::

    enum_version/entities/{entity_id}_stock_investments.csv
    enum_version/entities/{entity_id}_goal_achievements.csv

边界:
    - 负责: 准备 jobs + simulation window + JobExecutor 回调
    - 不负责: 切 batch / worker 数（BE）、指纹缓存、legacy 格式
    - 调用方: Strategy._run_steps（cache miss 之后）
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from core.modules.backtest_engine import BacktestEngine
from core.modules.strategy.core.engines.price_factor.enum_data import (
    EnumVersionData,
    load_enum_version,
    resolve_enum_version_dir,
)
from core.modules.strategy.core.engines.price_factor.executor import JobExecutor
from core.modules.strategy.core.engines.price_factor.job_builder import JobBuilder
from core.modules.strategy.core.engines.price_factor.timeline import resolve_simulation_window

if TYPE_CHECKING:
    from core.modules.strategy.strategy import SimulateRuntimeContext


class PriceFactorPipeline:
    """价格因子统一编排入口。"""

    @classmethod
    def run(cls, ctx: "SimulateRuntimeContext") -> Dict[str, Any]:
        # TODO: 待实现
        # cache = CacheManager.get_cache(ctx)
        # if cache.is_hit():
        #     return cache.get_result()

        result = cls.run_by_steps(ctx)

        # TODO: 待实现
        # cache = CacheManager.set_cache(ctx, result)

        return result

    @classmethod
    def run_by_steps(cls, ctx: "SimulateRuntimeContext") -> Dict[str, Any]:
        """按步骤串起各步，返回本 step 的 report dict。"""
        data = cls.load_enum_data(ctx)
        start, end = cls.resolve_window(data)
        jobs = cls.build_jobs(data)
        run_result = cls.execute_backtest(jobs, start=start, end=end, data=data)
        raise NotImplementedError(
            "PriceFactorPipeline: execute 已接 BE（start/end + JobExecutor）；"
            f"ReportManager 待实现 (entities={len(data.entity_ids)}, "
            f"version={data.version_id}, window={start}~{end}, "
            f"jobs={len(jobs)}, success={getattr(run_result, 'success', None)})"
        )

    @classmethod
    def load_enum_data(cls, ctx: "SimulateRuntimeContext") -> EnumVersionData:
        """解析 enum version 目录，加载 runtime + entity_ids（不读 CSV）。"""
        if ctx.enum_version is None or not str(ctx.enum_version).strip():
            raise ValueError("SimulateRuntimeContext.enum_version 不能为空")
        version_id = str(ctx.enum_version).strip()
        output_dir = resolve_enum_version_dir(ctx.strategy_key, version_id)
        return load_enum_version(output_dir, version_id)

    @classmethod
    def resolve_window(cls, data: EnumVersionData) -> Tuple[str, str]:
        """枚举 runtime period → 已 resolve 的 simulation window。"""
        return resolve_simulation_window(data)

    @classmethod
    def build_jobs(cls, data: EnumVersionData) -> List[Dict[str, Any]]:
        """组装 BacktestEngine entity_based bundle jobs。"""
        return JobBuilder.build_jobs(data)

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
