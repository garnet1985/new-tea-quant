#!/usr/bin/env python3
"""Entity-based enumerator pipeline（简化版，一个 run 方法一步带过）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import StrategySettings
from core.modules.strategy.core.engines.shared.services.finger_print.fingerprint import Fingerprint
from core.modules.strategy.core.services.discovery.discovered_strategy import EnabledStrategyInfo
from core.modules.data_contract import DataKey



class EnumeratorPipeline:
    """Entity-based enumerator pipeline（简化版，一个 run 方法一步带过）。"""
    global_entity_cache: GlobalEntityCache = None

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
            strategy_info=strategy_info,
            runtime_settings=runtime_settings or {},
        )

        settings_fp = Fingerprint.to_settings_diff_fingerprint(settings_diff)

        # Step 2: 获取 entity_ids 和必要参数（用于 env 指纹）
        from core.modules.strategy.core.engines.shared.services.entity_loader.global_entity_loader import GlobalEntityCache
        # 初始化 GlobalEntityCache（解析 settings，获取数据声明分组）

        cls.global_entity_cache = GlobalEntityCache(effective_settings_obj)

        stock_ids = cls._resolve_stock_ids(global_entity_cache.get(DataKey.STOCK_LIST))

        env_fp = Fingerprint.to_env_fingerprint(
            strategy_info=strategy_info,
            effective_settings=effective_settings_obj,
            entity_ids=stock_ids,  # 传递已获取的 entity_ids，避免重复计算
        )

        results = None

        if ignore_cache or fingerprint_is_not_matching(settings_fp, env_fp):
            global_entity_cache.load_required_data()
            # Step 5: 准备执行（加载全局数据、构建 bundle job）
            # cls._warmup_global_data(
            #     effective_settings=effective_settings,
            #     global_entity_cache=global_entity_cache,
            #     entity_ids=entity_ids,
            # )

            # Step 6: 构建 bundle job
            jobs = cls._build_backtest_engine_jobs(
                strategy_info=strategy_info,
                effective_settings_obj=effective_settings_obj,
                global_data=global_entity_cache.get_data(),
            )

            # Step 8: 执行回测
            results = cls._execute_backtest(jobs, strategy_info, effective_settings_obj)

            # Step 9: Report 生成
            # version_info = cls._save_results_and_metadata(
            #     results=results,
            #     strategy_info=strategy_info,
            #     effective_settings_obj=effective_settings_obj,
            #     settings_fp=settings_fp,
            #     env_fp=env_fp,
            # )


        else:
            cache = cls._find_cache_by_fingerprints(settings_fp, env_fp)
            if cache:
                results = cls._cache_to_results(cache)

        report = self._to_report(results)

        return report

    @classmethod
    def _warmup_global_data(cls,
        effective_settings: StrategySettings,
        global_entity_cache: Any, 
        entity_ids: List[str]):
        """预热全局数据（preload_global_data）。

        Args:
            global_entity_cache: GlobalEntityCache 实例
            entity_ids: Entity ID 列表
        """
        # 从 effective_settings_obj 获取 simulation 配置
        simulation_settings = effective_settings_obj.raw_settings.get("simulation", {})
        global_entity_cache.preload_global_data(
            start_date=simulation_settings["start_date"],
            end_date=simulation_settings["end_date"],
            entity_ids=entity_ids,
        )

    @classmethod
    def _build_backtest_engine_jobs(
        cls,
        strategy_info: EnabledStrategyInfo,
        effective_settings: StrategySettings,
        global_entity_cache: Any,
    ) -> List[Dict[str, Any]]:
        """准备执行：加载全局数据、构建 bundle job。

        Args:
            strategy_info: EnabledStrategyInfo 对象
            effective_settings: 有效策略配置
            global_entity_cache: GlobalEntityCache 实例
            entity_ids: Entity ID 列表
            start_date: 回测开始日期
            end_date: 回测结束日期

        Returns:
            Bundle job 列表（包含所有 entity 信息）

        流程：
        1. 加载全局数据（preload_global_data）
        2. 构建 bundle job（JobBuilder）
        """
        from core.modules.strategy.core.engines.enumerator.entity_based.services.job_builder import JobBuilder

        simulation_settings = effective_settings.raw_settings.get("simulation", {})

        bundle_job = JobBuilder.build_bundle_job(
            strategy_info=strategy_info,
            effective_settings=effective_settings,
            global_entity_cache=global_entity_cache,
            start_date=simulation_settings["start_date"],
            end_date=simulation_settings["end_date"],
        )

        # 将 bundle job 转换为 jobs 列表（BacktestEngine 要求）
        return [bundle_job.to_dict()]

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
    def _load_result_from_cache(cls, cache: Dict[str, Any]) -> Dict[str, Any]:
        """从缓存加载结果。

        Args:
            cache: 缓存信息

        Returns:
            回测结果

        TODO: 实现完整的缓存加载逻辑
        """
        # TODO: 实现缓存加载逻辑
        return {}

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
        """
        from core.modules.backtest_engine import BacktestEngine
        from core.modules.backtest_engine.contracts import RunCallbacks
        from core.modules.strategy.core.engines.enumerator.entity_based.child_process_worker import (
            ChildProcessWorker,
        )

        # 1. 准备 execute_fn（业务逻辑）
        def execute_fn(job_context):
            """Execute 函数：遍历 entity，调用 hooks.find_opportunity()。"""
            # 从 job_context.init 获取加载的数据
            loaded_data = job_context.init or {}
            entity_data = loaded_data.get("entity_data", {})
            global_data = loaded_data.get("global_data", {})

            # 从 payload 获取 strategy_info 和 settings
            payload = job_context.payload
            strategy_info_dict = payload.get("strategy_info", {})
            settings_dict = payload.get("settings", {})

            # 动态加载 hooks 类
            hooks_module_path = strategy_info_dict.get("hooks_module_path")
            hooks_class_name = strategy_info_dict.get("hooks_class_name")

            if not hooks_module_path or not hooks_class_name:
                raise ValueError("缺少 hooks 信息")

            import importlib
            hooks_module = importlib.import_module(hooks_module_path)
            hooks_class = getattr(hooks_module, hooks_class_name)
            hooks_instance = hooks_class()

            # 遍历每个 entity，调用 find_opportunity()
            results = []
            entity_specified = payload.get("entity_specified", [])

            for entity_item in entity_specified:
                entity_id = entity_item.get("id")
                if not entity_id:
                    continue

                # 获取该 entity 的数据
                per_entity_data = entity_data.get(entity_id, {})

                # 合并数据：per_entity_data + global_data
                complete_data = {
                    "entity_id": entity_id,
                    "per_entity": per_entity_data,
                    "global": global_data,
                    "settings": settings_dict,
                }

                # 调用 hooks.find_opportunity()
                try:
                    opportunity = hooks_instance.find_opportunity(complete_data)
                    results.append({
                        "entity_id": entity_id,
                        "success": True,
                        "opportunity": opportunity,
                    })
                except Exception as e:
                    results.append({
                        "entity_id": entity_id,
                        "success": False,
                        "error": str(e),
                    })

            return {
                "success": True,
                "results": results,
                "entities_count": len(entity_specified),
            }

        # 2. 准备 callbacks（钩子函数）
        callbacks = RunCallbacks(
            on_single_job_start=ChildProcessWorker.on_init,
        )

        # 3. 调用 BacktestEngine.entity_based.run()
        run_result = BacktestEngine.entity_based.run(
            jobs=jobs,
            execute_fn=execute_fn,
            callbacks=callbacks,
            task_name=f"strategy_{strategy_info.key}",
        )

        # 4. 返回执行结果
        return {
            "success": run_result.success,
            "total_jobs": run_result.total_jobs,
            "completed_jobs": run_result.completed_jobs,
            "failed_jobs": run_result.failed_jobs,
            "elapsed_seconds": run_result.elapsed_seconds,
            "job_results": run_result.job_results,
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


__all__ = ["EnumeratorPipeline"]