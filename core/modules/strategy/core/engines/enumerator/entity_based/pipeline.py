#!/usr/bin/env python3
"""Entity-based enumerator pipeline（简化版，一个 run 方法一步带过）。"""

from __future__ import annotations

from typing import Any, ClassVar, Dict, List, Optional

from core.modules.strategy.core.engines.enumerator.entity_based.executor import JobExecutor
from core.modules.strategy.core.engines.enumerator.entity_based.services.job_builder import JobBuilder
from core.modules.strategy.core.engines.shared.services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
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
    """Entity-based enumerator pipeline（简化版，一个 run 方法一步带过）。"""

    global_entity_cache: ClassVar[Optional[GlobalEntityCache]] = None


    @classmethod
    def run(
        cls,
        strategy_info: EnabledStrategyInfo,
        runtime_settings: dict = None,
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        """运行回测流程（一个 run 方法一步带过）。

        Args:
            strategy_info: EnabledStrategyInfo 对象（包含策略信息）
            runtime_settings: 运行时配置（可选，覆盖 disk settings）
            ignore_cache: 是否忽略缓存（强制重新计算）

        Returns:
            回测结果（包含 version_id、output_dir 等）

        流程：
        1. Settings 处理（计算 effective settings 和 settings_diff）
        2. Fingerprint 生成（settings_fp 和 env_fp）
        3. 查缓存（根据 fingerprint 查找缓存）
        4. 准备执行（加载 global data、构建 jobs）
        5. 执行回测（调用 backtest engine）
        6. Report 生成（保存结果和 metadata）

        设计：
        - 不再区分 preprocess/execute/postprocess（简化为一个 run 方法）
        - 参数获取逻辑内聚在 Fingerprint 内部（不再分散）
        - 查缓存、执行回测、生成报告都在一个流程中完成
        """

        # Step 1: Settings 处理
        effective_settings_obj, settings_diff = StrategySettings.calculate_effective_settings(
            disk_settings=strategy_info.settings,
            user_settings=runtime_settings or {},
        )

        # Step 2: 初始化 GlobalEntityCache（系统 global 数据）
        cls.global_entity_cache = GlobalEntityCache(effective_settings_obj)

        # 强制加载系统 global 数据（stock_list、trade_calendar、latest completed trading date）
        stock_ids = cls.global_entity_cache.init_system_globals().get_stock_ids()

        # 声明分组 → StrategyDataResolver；global 加载 → GlobalEntityCache
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
            cls.global_entity_cache.load_global_declarations(
                declaration_groups["global_declarations"]
            )

            stock_ids = cls.global_entity_cache.get_stock_ids()
            global_declarations = declaration_groups["global_declarations"]
            per_entity_declarations = declaration_groups["per_entity_declarations"]
            shm_info = cls.global_entity_cache.get_shm_info()

            jobs = JobBuilder.build_backtest_engine_jobs(
                strategy_info=strategy_info,
                effective_settings=effective_settings_obj,
                entity_ids=stock_ids,
                global_declarations=global_declarations,
                per_entity_declarations=per_entity_declarations,
                shm_info=shm_info,
            )

            results = cls._execute_backtest(jobs, strategy_info, effective_settings_obj)

            # TODO: cls._save_results_and_metadata(...)

        return cls._to_report(results)

    @classmethod
    def _find_cache_by_fingerprints(cls, settings_fp: str, env_fp: str) -> Optional[Dict[str, Any]]:
        """根据 fingerprint 查找缓存。

        Args:
            settings_fp: Settings 指纹
            env_fp: Env 指纹

        Returns:
            缓存信息（如果存在），否则返回 None

        TODO: 实现完整的缓存查找逻辑
        """
        # TODO: 实现缓存查找逻辑（从数据库查询）
        return None

    @classmethod
    def _cache_to_results(cls, cache: Dict[str, Any]) -> Dict[str, Any]:
        """从缓存记录转换为 pipeline 结果。"""
        return dict(cache.get("results") or cache)

    @classmethod
    def _to_report(cls, results: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """将执行结果包装为对外 report。"""
        if not results:
            return {"success": False, "opportunities": [], "failed_entities": []}
        return {
            "success": bool(results.get("success", True)),
            "opportunities": list(results.get("opportunities") or []),
            "failed_entities": list(results.get("failed_entities") or []),
            "total_jobs": results.get("total_jobs", 0),
            "completed_jobs": results.get("completed_jobs", 0),
            "failed_jobs": results.get("failed_jobs", 0),
            "elapsed_seconds": results.get("elapsed_seconds", 0.0),
        }

    # 移除冗余的 _load_global_data() 方法（已在 Step 4 中集成）

    @classmethod
    def _execute_backtest(
        cls,
        jobs: List[Dict[str, Any]],
        strategy_info: EnabledStrategyInfo,
        effective_settings_obj: StrategySettings,
    ) -> Dict[str, Any]:
        """执行回测（调用 BacktestEngine）。

        Args:
            jobs: Bundle job 列表（包含 entity_specified、entity_shared、global、shm_info）
            strategy_info: EnabledStrategyInfo 对象
            effective_settings: 有效策略配置

        Returns:
            回测结果（包含 version_id、output_dir 等）

        流程：
        1. 准备 BacktestEngine 参数（execute_fn、callbacks）
        2. 调用 BacktestEngine.entity_based.run()
        3. 返回执行结果

        钩子映射（统一命名）：
        - 子进程钩子：
          - on_child_process_task_start → JobExecutor.on_child_process_task_start（数据加载）
          - on_child_process_task_complete → None（strategy不使用子进程清理）
          - execute_fn → JobExecutor.execute（执行逻辑）
        - 主进程钩子：
          - on_after_all_tasks_complete → JobExecutor.on_after_all_tasks_complete（全局清理）
        """
        from core.modules.backtest_engine import BacktestEngine
        from core.modules.backtest_engine.contracts import RunCallbacks

        # 准备累积数据的存储（主进程维护）
        all_opportunities = []
        failed_entities = []

        # 创建闭包，访问JobExecutor的静态方法，并累积数据
        def on_single_task_result_closure(report: Any, progress: Any) -> None:
            """主进程钩子：调用JobExecutor.on_single_task_result，并累积数据。"""
            JobExecutor.on_single_task_result(report, progress)

            # 累积数据（pipeline维护）
            if report.success and report.data:
                opportunities = report.data.get("opportunities", [])
                all_opportunities.extend(opportunities)

            # Catch错误的entity（pipeline维护）
            if not report.success:
                error_msg = report.error or "Unknown error"
                failed_entities.append({
                    "job_id": report.job_id,
                    "error": error_msg,
                })

        def on_after_all_tasks_complete_closure(job_reports: List) -> None:
            """主进程钩子：调用JobExecutor.on_after_all_tasks_complete，并传递global_entity_cache。"""
            JobExecutor.on_after_all_tasks_complete(job_reports, cls.global_entity_cache)

        # 准备 callbacks（钩子函数，统一命名）
        callbacks = RunCallbacks(
            on_child_process_task_start=JobExecutor.on_child_process_task_start,  # 子进程钩子：数据加载
            on_child_process_task_complete=None,  # 子进程钩子：清理（strategy不使用）
            on_after_all_tasks_complete=on_after_all_tasks_complete_closure,  # 主进程钩子：全局清理
        )

        # 调用 BacktestEngine.entity_based.run()
        run_result = BacktestEngine.entity_based.run(
            jobs=jobs,
            execute_fn=JobExecutor.execute,  # 子进程钩子：执行逻辑
            callbacks=callbacks,
            task_name=f"strategy_{strategy_info.key}",
        )

        # 返回执行结果（包含累积的数据）
        return {
            "success": run_result.success,
            "total_jobs": run_result.total_jobs,
            "completed_jobs": run_result.completed_jobs,
            "failed_jobs": run_result.failed_jobs,
            "elapsed_seconds": run_result.elapsed_seconds,
            "job_results": run_result.job_results,
            "opportunities": all_opportunities,  # 累积的opportunities
            "failed_entities": failed_entities,  # 失败的entity列表
        }

    @classmethod
    def _save_results_and_metadata(
        cls,
        results: Dict[str, Any],
        strategy_info: EnabledStrategyInfo,
        effective_settings_obj: StrategySettings,
        settings_fp: str,
        env_fp: str,
    ) -> Dict[str, Any]:
        """保存结果和 metadata。

        Args:
            results: 回测结果
            strategy_info: EnabledStrategyInfo 对象
            effective_settings_obj: 有效策略配置对象
            settings_fp: Settings 指纹
            env_fp: Env 指纹

        Returns:
            Version 信息（包含 version_id、output_dir 等）

        TODO: 实现完整的结果保存逻辑
        """
        # TODO: 实现结果保存逻辑
        return {}


# 兼容 engine.py 中的旧名称
EntityBasedJobPipeline = EnumeratorPipeline

__all__ = ["EnumeratorPipeline", "EntityBasedJobPipeline"]