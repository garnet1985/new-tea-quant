"""枚举器统一编排（entity_based / slice_based）。

本文件:
- EnumeratorPipeline: 采样 → JobBuilder → BE.run(callbacks=JobExecutor) → ReportManager
  边界: 周边编排与落盘；不负责指纹/DB 缓存；不复写 BE Timeline
  模式内核仅两件套: JobBuilder（喂 jobs）+ JobExecutor（RunCallbacks）
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Tuple, Type

from core.modules.backtest_engine.core.performance.worker_profile import (
    WorkerProfiles,
    profile_calendar_slice_config,
    resolve_entity_based_performance_for_profile,
)
from core.infra.project_context import ProjectContext
from core.modules.backtest_engine.core.performance.settings import resolve_slice_based_performance
from core.modules.strategy.core.engines.enumerator.common.report_manager import ReportManager
from core.modules.strategy.core.engines.enumerator.common.report_manager.report_output import (
    ReportOutput,
)
from core.modules.strategy.core.services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
)
from core.modules.strategy.core.services.entity_loader.stock_sampling import (
    StockSampler,
)
from core.modules.strategy.core.services.entity_loader.strategy_data_resolver import (
    StrategyDataResolver,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)
from core.modules.strategy.core.services.progress import PipelineProgress

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.shared.data_class.simulate_session import SimulateSession

logger = logging.getLogger(__name__)

_MODE_ENTITY = "entity_based"
_MODE_SLICE = "slice_based"
_PROGRESS_PIPELINE = "enum"


class EnumeratorPipeline:
    """枚举统一编排入口。

    边界:
    - 负责: SimulateSession 上跑枚举（采样 / jobs / BE / 报告）
    - 不负责: 指纹、系统级 GlobalEntityCache 加载、DB 缓存；不建平行 session / TimelineBuilder
    - 调用方: Strategy._run_steps（cache miss 之后）
    """

    global_entity_cache: ClassVar[Optional[GlobalEntityCache]] = None

    @classmethod
    def find_output_version_via_fps(cls, ctx: "SimulateSession") -> Optional[str]:
        """按双指纹查工作台 enum 槽的 ``version_id``；未找到返回 None。"""
        from core.modules.strategy.core.services.simulation_cache.cache_manager import (
            SimulationCacheManager,
        )

        return SimulationCacheManager.find_enum_output_version(
            ctx.strategy_key,
            ctx.fp_res,
        )

    @classmethod
    def run(cls, ctx: "SimulateSession") -> Dict[str, Any]:
        """运行枚举；复用 ctx 内已 seed 的 cache / settings / 指纹。"""
        execution_mode = ctx.strategy_info.get_execution_mode()
        if execution_mode not in {_MODE_ENTITY, _MODE_SLICE}:
            raise ValueError(f"不支持的execution_mode: {execution_mode}")

        cls.global_entity_cache = ctx.global_entity_cache
        declaration_groups = StrategyDataResolver.group_from_settings(
            ctx.effective_settings
        )
        results = cls._run_by_steps(ctx, declaration_groups=declaration_groups)
        return cls._to_report(results)

    @classmethod
    def _run_by_steps(
        cls,
        ctx: "SimulateSession",
        *,
        declaration_groups: Dict[str, Any],
    ) -> Dict[str, Any]:
        strategy_info = ctx.strategy_info
        execution_mode = strategy_info.get_execution_mode()
        effective_settings_obj = ctx.effective_settings
        stock_ids = list(ctx.entity_ids)

        drive = PipelineProgress.drives_pipeline(_PROGRESS_PIPELINE)
        if drive:
            PipelineProgress.enter_step_bound("load")

        cls.global_entity_cache.load_global_declarations(
            declaration_groups["global_declarations"]
        )

        if not stock_ids:
            stock_ids = cls.global_entity_cache.get_stock_ids()
        stock_ids = cls._resolve_entity_ids(
            stock_ids,
            effective_settings_obj,
            strategy_info.key,
        )

        report_manager = cls._step_to_begin_report_manager(
            strategy_info=strategy_info,
            stock_ids=stock_ids,
            settings_fp=ctx.settings_fp,
            env_fp=ctx.env_fp,
            effective_settings_obj=effective_settings_obj,
            settings_diff=ctx.settings_diff,
        )

        if drive:
            PipelineProgress.complete_step_bound("load")
            PipelineProgress.enter_step_bound("dispatch")

        jobs = cls._build_jobs(
            strategy_info=strategy_info,
            effective_settings_obj=effective_settings_obj,
            stock_ids=stock_ids,
            declaration_groups=declaration_groups,
            report_manager=report_manager,
            execution_mode=execution_mode,
        )

        if drive:
            PipelineProgress.complete_step_bound("dispatch")
            PipelineProgress.enter_step_bound("execute")

        results = cls._step_to_execute_backtest(
            jobs=jobs,
            report_manager=report_manager,
            effective_settings_obj=effective_settings_obj,
            execution_mode=execution_mode,
        )

        if drive:
            PipelineProgress.complete_step_bound("execute")
            PipelineProgress.enter_step_bound("report")

        cls._step_to_generate_reports(
            results=results,
            report_manager=report_manager,
            entity_count=len(stock_ids),
            effective_settings_obj=effective_settings_obj,
        )

        if drive:
            PipelineProgress.complete_step_bound("report")
        return results

    @classmethod
    def _mode_job_stack(
        cls, execution_mode: str
    ) -> Tuple[Type[Any], Type[Any], Type[Any]]:
        """按 mode 返回 (JobBuilder类, JobExecutor类, ExecutorHooksContext)。"""
        from core.modules.strategy.core.engines.enumerator.common.base_executor import (
            ExecutorHooksContext,
        )

        if execution_mode == _MODE_SLICE:
            from core.modules.strategy.core.engines.enumerator.slice_based.executor import (
                EnumSliceJobExecutor,
            )
            from core.modules.strategy.core.engines.enumerator.slice_based.job_builder import (
                EnumSliceJobBuilder,
            )

            return EnumSliceJobBuilder, EnumSliceJobExecutor, ExecutorHooksContext

        from core.modules.strategy.core.engines.enumerator.entity_based.executor import (
            EnumEntityJobExecutor,
        )
        from core.modules.strategy.core.engines.enumerator.entity_based.job_builder import (
            EnumEntityJobBuilder,
        )

        return EnumEntityJobBuilder, EnumEntityJobExecutor, ExecutorHooksContext

    @classmethod
    def _build_jobs(
        cls,
        *,
        strategy_info: EnabledStrategyInfo,
        effective_settings_obj: StrategySettings,
        stock_ids: List[str],
        declaration_groups: Dict[str, Any],
        report_manager: ReportManager,
        execution_mode: str,
    ) -> List[Dict[str, Any]]:
        job_builder, _, _ = cls._mode_job_stack(execution_mode)
        return job_builder.build_backtest_engine_jobs(
            strategy_info=strategy_info,
            effective_settings=effective_settings_obj,
            entity_ids=stock_ids,
            global_declarations=declaration_groups["global_declarations"],
            per_entity_declarations=declaration_groups["per_entity_declarations"],
            shm_info=cls.global_entity_cache.get_shm_info(),
            output_recorder_snapshot=report_manager.to_worker_binding(),
        )

    @classmethod
    def _step_to_execute_backtest(
        cls,
        *,
        jobs: List[Dict[str, Any]],
        report_manager: ReportManager,
        effective_settings_obj: StrategySettings,
        execution_mode: str,
    ) -> Dict[str, Any]:
        from core.modules.backtest_engine import BacktestEngine
        _, job_executor, hooks_ctx_cls = cls._mode_job_stack(execution_mode)
        report_manager.profiler.begin_collect(
            entity_count=cls._count_entities_in_jobs(jobs),
        )
        callbacks = job_executor.build_run_callbacks(
            hooks_ctx_cls(
                report_manager=report_manager,
                global_entity_cache=cls.global_entity_cache,
            )
        )
        performance = cls._resolve_backtest_performance(
            effective_settings_obj, execution_mode=execution_mode
        )
        task_name = f"strategy_{report_manager.strategy_key}"
        period = effective_settings_obj.resolve_period()

        if execution_mode == _MODE_SLICE:
            run_result = BacktestEngine.slice_based.run(
                jobs=jobs,
                start=period.start_date,
                end=period.end_date,
                performance=performance,
                callbacks=callbacks,
                task_name=task_name,
            )
        else:
            run_result = BacktestEngine.entity_based.run(
                jobs=jobs,
                start=period.start_date,
                end=period.end_date,
                performance=performance,
                callbacks=callbacks,
                task_name=task_name,
            )

        return cls._pack_backtest_results(run_result, report_manager=report_manager)

    @classmethod
    def _resolve_backtest_performance(
        cls,
        effective_settings: StrategySettings,
        *,
        execution_mode: str,
    ) -> Dict[str, Any]:
        raw = effective_settings.raw_settings or {}
        cls._warn_ignore_settings_performance(raw)
        if execution_mode == _MODE_SLICE:
            override: Dict[str, Any] = dict(
                profile_calendar_slice_config(WorkerProfiles.ENUMERATOR)
            )
            calendar_slice = raw.get("calendar_slice")
            if isinstance(calendar_slice, dict):
                override.update(calendar_slice)
            return resolve_slice_based_performance(override)
        return resolve_entity_based_performance_for_profile(WorkerProfiles.ENUMERATOR)

    @classmethod
    def _step_to_begin_report_manager(
        cls,
        *,
        strategy_info: EnabledStrategyInfo,
        stock_ids: List[str],
        settings_fp: str,
        env_fp: str,
        effective_settings_obj: StrategySettings,
        settings_diff: Dict[str, Any],
    ) -> ReportManager:
        return ReportManager.begin(
            strategy_info.key,
            strategy_path=strategy_info.unique_relative_path,
            entity_ids=stock_ids,
            settings_fp=settings_fp,
            env_fp=env_fp,
            effective_settings=effective_settings_obj,
            settings_diff=settings_diff,
            execution_mode=strategy_info.get_execution_mode(),
            market_profile=str(
                effective_settings_obj.raw_settings.get("market_profile")
                or ProjectContext.config.get_default_market_profile_key()
            ),
        )

    @classmethod
    def _step_to_generate_reports(
        cls,
        *,
        results: Dict[str, Any],
        report_manager: ReportManager,
        entity_count: int,
        effective_settings_obj: StrategySettings,
    ) -> None:
        run_result = results.pop("_run_result", None)
        if run_result is None:
            return
        report_manager.finalize(
            run_result,
            entity_count=entity_count,
            opportunities_count=int(results.get("opportunities_count") or 0),
            performance_config=ReportOutput.config_from_settings(
                effective_settings_obj.raw_settings
            ),
        )

    @staticmethod
    def _count_entities_in_jobs(jobs: List[Dict[str, Any]]) -> int:
        total = 0
        for job in jobs:
            if not isinstance(job, dict):
                continue
            payload = job.get("payload") or job
            if not isinstance(payload, dict):
                continue
            entity_ids = payload.get("entity_ids")
            if isinstance(entity_ids, list) and entity_ids:
                total += len(entity_ids)
                continue
            specified = payload.get("entity_specified")
            if isinstance(specified, list):
                total += len(specified)
        return total

    @staticmethod
    def _pack_backtest_results(
        run_result: Any,
        *,
        report_manager: ReportManager,
    ) -> Dict[str, Any]:
        failed_entities: List[Dict[str, Any]] = []
        opportunities_count = 0

        for job_report in run_result.job_results:
            if not job_report.success:
                failed_entities.append(
                    {
                        "job_id": job_report.job_id,
                        "error": job_report.error or "Unknown error",
                    }
                )
            elif isinstance(job_report.data, dict):
                opportunities_count += int(job_report.data.get("opportunities_count") or 0)

        return {
            "success": run_result.success,
            "output_dir": str(report_manager.output_dir),
            "version_id": report_manager.version_id,
            "strategy_key": report_manager.strategy_key,
            "total_jobs": run_result.total_jobs,
            "completed_jobs": run_result.completed_jobs,
            "failed_jobs": run_result.failed_jobs,
            "elapsed_seconds": run_result.elapsed_seconds,
            "opportunities_count": opportunities_count,
            "failed_entities": failed_entities,
            "_run_result": run_result,
        }

    @classmethod
    def _resolve_entity_ids(
        cls,
        stock_ids: List[str],
        effective_settings: StrategySettings,
        strategy_key: str,
    ) -> List[str]:
        """按 sampling 配置缩小 entity 范围（smoke / 抽样）。"""
        if not effective_settings.sampling.use_sampling:
            return stock_ids
        return StockSampler.sample(
            stock_ids,
            effective_settings.sampling.sampling,
            strategy_key,
        )

    @classmethod
    def _to_report(cls, results: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not results:
            return {"success": False, "failed_entities": []}
        out: Dict[str, Any] = {
            "success": bool(results.get("success", True)),
            "output_dir": results.get("output_dir"),
            "version_id": results.get("version_id"),
            "strategy_key": results.get("strategy_key"),
            "opportunities_count": results.get("opportunities_count", 0),
            "failed_entities": list(results.get("failed_entities") or []),
            "total_jobs": results.get("total_jobs", 0),
            "completed_jobs": results.get("completed_jobs", 0),
            "failed_jobs": results.get("failed_jobs", 0),
            "elapsed_seconds": results.get("elapsed_seconds", 0.0),
        }
        # DB / BFF：附带 ``enumMetrics``（与 price/portfolio ``to_cache_dict`` 对齐）
        output_dir = results.get("output_dir")
        if output_dir:
            try:
                from core.modules.strategy.core.engines.enumerator.common.report_manager.overall_report import (
                    OverallReport,
                )

                out.update(OverallReport.load(Path(output_dir)).to_ui_dict())
            except Exception:
                logger.debug(
                    "enum _to_report: overall_report unavailable at %s",
                    output_dir,
                    exc_info=True,
                )
        return out

    @staticmethod
    def _warn_ignore_settings_performance(raw: Dict[str, Any]) -> None:
        if isinstance(raw.get("performance"), dict) and raw["performance"]:
            logger.warning(
                "忽略 settings.performance=%s；请用 userspace/config/worker.json → job_pipeline.enumerator",
                sorted(raw["performance"].keys()),
            )


__all__ = ["EnumeratorPipeline"]
