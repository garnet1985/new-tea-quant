#!/usr/bin/env python3
"""Entity-based enumerator pipeline（编排层）。"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from core.infra.project_context import ProjectContext
from core.modules.strategy.core.engines.enumerator.entity_based.executor import (
    ExecutorHooksContext,
    JobExecutor,
)
from core.modules.strategy.core.engines.enumerator.entity_based.services.job_builder import JobBuilder
from core.modules.strategy.core.engines.enumerator.shared.report_manager import ReportManager
from core.modules.strategy.core.engines.enumerator.shared.report_manager.report_consts import (
    report_output_config,
)
from core.modules.strategy.core.engines.shared.services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
)
from core.modules.strategy.core.engines.shared.services.entity_loader.stock_sampling import (
    StockSampler,
)
from core.modules.strategy.core.engines.shared.services.entity_loader.strategy_data_resolver import (
    StrategyDataResolver,
)
from core.modules.strategy.core.engines.shared.services.finger_print.fingerprint import Fingerprint
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery.data.discovered_strategy import EnabledStrategyInfo


class EnumeratorPipeline:
    """Entity-based enumerator pipeline（编排层）。"""

    global_entity_cache: ClassVar[Optional[GlobalEntityCache]] = None

    @classmethod
    def run(
        cls,
        strategy_info: EnabledStrategyInfo,
        runtime_settings: dict = None,
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        """运行 entity-based 枚举（settings → 执行 → 产物落盘）。"""
        effective_settings_obj, settings_diff = StrategySettings.calculate_effective_settings(
            disk_settings=strategy_info.settings,
            user_settings=runtime_settings or {},
        )

        cls.global_entity_cache = GlobalEntityCache(effective_settings_obj)
        stock_ids = cls.global_entity_cache.init_system_globals().get_stock_ids()

        declaration_groups = StrategyDataResolver.group_from_settings(
            effective_settings_obj.raw_settings
        )
        settings_fp = Fingerprint.to_settings_diff_fingerprint(settings_diff, stock_ids)
        env_fp = Fingerprint.to_env_fingerprint(
            strategy_info=strategy_info,
            effective_settings=effective_settings_obj,
            entity_ids=stock_ids,
        )

        results: Optional[Dict[str, Any]] = None
        if not ignore_cache:
            cache = cls._find_cache_by_fingerprints(settings_fp, env_fp)
            if cache:
                results = cls._cache_to_results(cache)

        if results is None:
            results = cls._run_by_steps(
                strategy_info=strategy_info,
                effective_settings_obj=effective_settings_obj,
                settings_diff=settings_diff,
                settings_fp=settings_fp,
                env_fp=env_fp,
                declaration_groups=declaration_groups,
            )

        return cls._to_report(results)

    # ── 编排 steps ──

    @classmethod
    def _run_by_steps(
        cls,
        *,
        strategy_info: EnabledStrategyInfo,
        effective_settings_obj: StrategySettings,
        settings_diff: Dict[str, Any],
        settings_fp: str,
        env_fp: str,
        declaration_groups: Dict[str, Any],
    ) -> Dict[str, Any]:
        cls.global_entity_cache.load_global_declarations(
            declaration_groups["global_declarations"]
        )

        stock_ids = cls.global_entity_cache.get_stock_ids()
        stock_ids = cls._resolve_entity_ids(
            stock_ids,
            effective_settings_obj,
            strategy_info.key,
        )

        report_manager = cls._step_to_begin_report_manager(
            strategy_info=strategy_info,
            stock_ids=stock_ids,
            settings_fp=settings_fp,
            env_fp=env_fp,
            effective_settings_obj=effective_settings_obj,
            settings_diff=settings_diff,
        )

        jobs = JobBuilder.build_backtest_engine_jobs(
            strategy_info=strategy_info,
            effective_settings=effective_settings_obj,
            entity_ids=stock_ids,
            global_declarations=declaration_groups["global_declarations"],
            per_entity_declarations=declaration_groups["per_entity_declarations"],
            shm_info=cls.global_entity_cache.get_shm_info(),
            output_recorder_snapshot=report_manager.to_worker_binding(),
        )

        results = cls._step_to_execute_backtest(
            jobs=jobs,
            report_manager=report_manager,
        )
        cls._step_to_generate_reports(
            results=results,
            report_manager=report_manager,
            entity_count=len(stock_ids),
            effective_settings_obj=effective_settings_obj,
        )
        return results

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
    def _step_to_execute_backtest(
        cls,
        *,
        jobs: List[Dict[str, Any]],
        report_manager: ReportManager,
    ) -> Dict[str, Any]:
        from core.modules.backtest_engine import BacktestEngine

        report_manager.profiler.begin_collect(
            entity_count=cls._count_entities_in_jobs(jobs),
        )

        run_result = BacktestEngine.entity_based.run(
            jobs=jobs,
            execute_fn=JobExecutor.execute,
            callbacks=JobExecutor.build_run_callbacks(
                ExecutorHooksContext(
                    report_manager=report_manager,
                    global_entity_cache=cls.global_entity_cache,
                )
            ),
            task_name=f"strategy_{report_manager.strategy_key}",
        )

        return cls._pack_backtest_results(run_result, report_manager=report_manager)

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
        report_manager.finalize_from_run_result(
            run_result,
            entity_count=entity_count,
            opportunities_count=int(results.get("opportunities_count") or 0),
            performance_config=report_output_config(effective_settings_obj.raw_settings),
        )

    @staticmethod
    def _count_entities_in_jobs(jobs: List[Dict[str, Any]]) -> int:
        total = 0
        for job in jobs:
            if not isinstance(job, dict):
                continue
            payload = job.get("payload") or job
            specified = payload.get("entity_specified") if isinstance(payload, dict) else None
            if isinstance(specified, list):
                total += len(specified)
            elif isinstance(job.get("entity_specified"), list):
                total += len(job["entity_specified"])
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
        sampling = effective_settings.raw_settings.get("sampling") or {}
        stock_pool = sampling.get("stock_pool")
        if stock_pool:
            pool = [str(item).strip() for item in stock_pool if str(item).strip()]
            known = set(stock_ids)
            filtered = [entity_id for entity_id in pool if entity_id in known]
            return filtered or pool

        if sampling.get("use_sampling"):
            return StockSampler.sample(stock_ids, sampling, strategy_key)

        return stock_ids

    @classmethod
    def _find_cache_by_fingerprints(cls, settings_fp: str, env_fp: str) -> Optional[Dict[str, Any]]:
        # TODO: 实现缓存查找逻辑（从数据库查询）
        return None

    @classmethod
    def _cache_to_results(cls, cache: Dict[str, Any]) -> Dict[str, Any]:
        return dict(cache.get("results") or cache)

    @classmethod
    def _to_report(cls, results: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not results:
            return {"success": False, "failed_entities": []}
        return {
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


EntityBasedJobPipeline = EnumeratorPipeline

__all__ = ["EnumeratorPipeline", "EntityBasedJobPipeline"]
