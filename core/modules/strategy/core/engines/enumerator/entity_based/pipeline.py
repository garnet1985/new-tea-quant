"""entity_based 主执行流程（简化版）。

"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import BacktestJob, RunCallbacks
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import StrategySettings
from core.modules.strategy.core.services.discovery.data.discovered_strategy import EnabledStrategyInfo
from core.modules.strategy.core.engines.enumerator.entity_based.runtime_context.performance import PerformanceConfig
from core.modules.strategy.core.engines.shared.services.finger_print.fingerprint import Fingerprint

from .child_process import ChildProcess

logger = logging.getLogger(__name__)


class EntityBasedJobPipeline:
    """entity_based 回测流程（简化版）。"""

    # Pipeline持有的全局数据（生命周期内有效）
    strategy_info: EnabledStrategyInfo
    settings_obj: StrategySettings

    @classmethod
    def run(
        cls,
        strategy_info: EnabledStrategyInfo,
        runtime_settings: dict = None,
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        """完整的回测流程（一步带过）。"""

        # ── Step 1: Settings处理 ──
        # 使用StrategySettings.calculate_effective_settings()合并settings并计算diff
        effective_settings, settings_diff = StrategySettings.calculate_effective_settings(
            strategy_info.settings,  # disk_settings
            runtime_settings or {}   # user_settings（如果没有传入，使用空dict）
        )
        cls.settings_obj = effective_settings

        # ── Step 2: Fingerprint生成 ──
        settings_fp, env_fp = cls._generate_fingerprints(effective_settings, settings_diff, strategy_info)

        # ── Step 3: 查缓存 ──
        if not ignore_cache:
            cache = cls._find_cache_by_finger_prints(settings_fp, env_fp)
            if cache:
                logger.info("Cache found, skip execution")
                result = cls._load_result_from_cache(cache)
                report = cls._result_to_report(result)
                cls.present_report(report)
                return report

        # ── Step 4: 准备执行（无缓存或ignore_cache）──
        cls.strategy_info = strategy_info

        # 4.1 加载global data（从settings.data.extra_required_data_sources）
        global_data = cls._load_global_data(effective_settings)

        # 4.2 构建jobs（从context构建）
        jobs = cls._build_backtest_engine_jobs(strategy_info, effective_settings, global_data)

        # ── Step 5: 执行回测 ──
        performance_config = PerformanceConfig.init()  # 只在执行时使用，不作为全局变量

        result = BacktestEngine.entity_based.run(
            jobs,
            ChildProcess.execute,              # child process执行函数
            performance=performance_config.to_dict(),
            callbacks=RunCallbacks(
                on_single_job_start=ChildProcess.on_init,    # 子进程初始化
            ),
        )

        # ── Step 6: Report生成 ──
        report = cls._result_to_report(result)
        cls.present_report(report)

        return report

    # ── 辅助方法（私有方法）──

    @classmethod
    def _generate_fingerprints(
        cls,
        effective_settings: StrategySettings,
        settings_diff: Dict[str, Any],
        strategy_info: EnabledStrategyInfo,
    ) -> tuple[str, str]:
        """生成fingerprint对（settings_fp, env_fp）。

        Args:
            effective_settings: 有效settings（已合并）
            settings_diff: 设置差异（影响回测结果）
            strategy_info: 策略信息

        Returns:
            (settings_fp, env_fp)元组

        设计：
            - settings_fp: 基于settings_diff的hash（设置变化）
            - env_fp: 基于环境信息的hash（entity_ids, execution_mode, hooks等）
        """
        # ── settings_fp: 基于settings_diff ──
        settings_fp = Fingerprint.to_settings_fingerprint(settings_diff)

        # ── env_fp: 基于环境信息 ──
        # 从raw_settings获取回测参数（正确路径）
        simulation = effective_settings.raw_settings.get("simulation", {})
        start_date = simulation.get("start_date", "")
        end_date = simulation.get("end_date", "")

        # entity_ids获取逻辑（区分采样开启/关闭）
        sampling = effective_settings.raw_settings.get("sampling", {})
        use_sampling = sampling.get("use_sampling", False)

        if use_sampling:
            # 采样开启：根据sampling.strategy获取entity_ids
            # TODO: 实现完整的采样逻辑（从文件读取、对比配置等）
            entity_ids = cls._resolve_entity_ids_with_sampling(sampling, strategy_info)
        else:
            # 采样关闭：使用全量stock_ids（从0_metadata.json或其他全局配置）
            entity_ids = cls._resolve_full_entity_ids(strategy_info)

        execution_mode = effective_settings.execution_mode  # 这个是正确的（property）

        env_fp = Fingerprint.to_env_fingerprint(
            strategy_id=strategy_info.unique_relative_path,
            entity_ids=entity_ids,
            start_date=start_date,
            end_date=end_date,
            execution_mode=execution_mode,
            hooks_module_path=strategy_info.hooks_module_path,
            hooks_class_name=strategy_info.hooks_class.__name__,
            hooks_file_path=str(strategy_info.strategy_file),  # hooks源文件路径
        )

        return settings_fp, env_fp

    @classmethod
    def _resolve_entity_ids_with_sampling(
        cls,
        sampling: Dict[str, Any],
        strategy_info: EnabledStrategyInfo,
    ) -> List[str]:
        """采样开启时，获取entity_ids（根据sampling.strategy）。

        Args:
            sampling: sampling配置块
            strategy_info: 策略信息

        Returns:
            entity_ids列表

        TODO: 实现完整的采样逻辑（从文件读取、对比配置等）
        """
        # 简化版：暂时返回空列表（后续实现）
        logger.warning("Sampling enabled but not implemented yet, returning empty entity_ids")
        return []

    @classmethod
    def _resolve_full_entity_ids(cls, strategy_info: EnabledStrategyInfo) -> List[str]:
        """采样关闭时，获取全量entity_ids（从0_metadata.json或其他全局配置）。

        Args:
            strategy_info: 策略信息

        Returns:
            entity_ids列表

        TODO: 实现从0_metadata.json读取全量stock_ids
        """
        # 简化版：暂时从strategy_info.folder读取0_metadata.json
        metadata_file = strategy_info.folder / "0_metadata.json"
        if not metadata_file.exists():
            logger.warning("0_metadata.json not found, returning empty entity_ids")
            return []

        try:
            import json
            with metadata_file.open("r", encoding="utf-8") as f:
                metadata = json.load(f)
            # metadata中应该有stock_ids字段
            stock_ids = metadata.get("stock_ids", [])
            if isinstance(stock_ids, list):
                return stock_ids
            else:
                logger.warning("0_metadata.json stock_ids is not a list")
                return []
        except Exception as e:
            logger.error("Failed to read 0_metadata.json: %s", e)
            return []

    @classmethod
    def _load_global_data(cls, effective_settings: StrategySettings) -> Dict[str, List[Dict[str, Any]]]:
        """加载全局数据（从settings.data.extra_required_data_sources）。

        Args:
            effective_settings: 有效settings（已合并）

        Returns:
            global_data字典 {slot: List[rows]}

        设计：
            - 从settings.data.extra_required_data_sources筛选scope=GLOBAL的数据源
            - 使用DataContracts.issue()加载全局数据
            - 包含macro_data、gdp_data等全局数据
        """
        # 从raw_settings获取data块
        data_block = effective_settings.raw_settings.get("data", {})
        if not isinstance(data_block, dict):
            logger.warning("settings.data is not dict, skip loading global_data")
            return {}

        # 获取extra_required_data_sources
        extras = data_block.get("extra_required_data_sources", [])
        if not extras or not isinstance(extras, list):
            logger.info("No extra_required_data_sources, skip loading global_data")
            return {}

        # 简化版：暂时返回空dict（后续实现完整逻辑）
        logger.warning("Global data loading not implemented yet, returning empty dict")
        return {}

    @classmethod
    def _build_backtest_engine_jobs(
        cls,
        strategy_info: EnabledStrategyInfo,
        effective_settings: StrategySettings,
        global_data: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """构建BacktestEngine jobs（TODO）。"""
        # TODO: 实现job构建逻辑
        logger.warning("Job building not implemented yet, returning empty list")
        return []

    @classmethod
    def _find_cache_by_finger_prints(cls, settings_fp: str, env_fp: str) -> Optional[Dict[str, Any]]:
        """通过fingerprint查找缓存。"""
        # TODO: 实现缓存查找逻辑
        return None

    @classmethod
    def _load_result_from_cache(cls, cache: Dict[str, Any]) -> Dict[str, Any]:
        """从缓存加载结果。"""
        # TODO: 实现缓存加载逻辑
        return cache

    @classmethod
    def _load_global_data(cls, settings: StrategySettings) -> Dict[str, Any]:
        """加载global data。"""
        # TODO: 实现global data加载逻辑
        return {}

    @classmethod
    def _build_backtest_engine_jobs(
        cls,
        strategy_info: EnabledStrategyInfo,
        settings: StrategySettings,
        global_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """构建BacktestEngine需要的jobs。"""
        # TODO: 实现jobs构建逻辑
        # 从settings解析entity_ids
        entity_ids = ["stock_001", "stock_002"]  # placeholder

        jobs = []
        for entity_id in entity_ids:
            job = {
                "id": entity_id,
                "payload": {
                    "entity_id": entity_id,
                    "strategy_id": strategy_info.unique_relative_path,
                    "key": strategy_info.key,
                    "start_date": "2024-01-01",  # placeholder
                    "end_date": "2024-12-31",    # placeholder
                    "hooks_module_path": strategy_info.hooks_module_path,
                    "hooks_class_name": strategy_info.hooks_class.__name__,
                    "settings_dict": settings.to_dict(),
                    "global_data": global_data,  # 传递global_data
                }
            }
            jobs.append(job)

        return jobs

    @classmethod
    def _result_to_report(cls, result: Dict[str, Any]) -> Dict[str, Any]:
        """结果转换为report。"""
        # TODO: 实现report生成逻辑
        return {
            "success": True,
            "total_jobs": len(result.get("job_results", [])),
            "completed_jobs": sum(1 for r in result.get("job_results", []) if r.get("success")),
            "failed_jobs": sum(1 for r in result.get("job_results", []) if not r.get("success")),
        }

    @classmethod
    def present_report(cls, report: Dict[str, Any]) -> None:
        """展示report。"""
        logger.info(
            "Report: success=%s, total=%d, completed=%d, failed=%d",
            report.get("success"),
            report.get("total_jobs"),
            report.get("completed_jobs"),
            report.get("failed_jobs"),
        )


__all__ = ["EntityBasedJobPipeline"]