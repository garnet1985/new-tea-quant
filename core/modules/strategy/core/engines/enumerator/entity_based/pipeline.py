#!/usr/bin/env python3
"""Entity-based enumerator pipeline（简化版，一个 run 方法一步带过）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import StrategySettings
from core.modules.strategy.core.engines.shared.services.finger_print.fingerprint import Fingerprint
from core.modules.strategy.core.services.discovery.discovered_strategy import EnabledStrategyInfo


class EnumeratorPipeline:
    """Entity-based enumerator pipeline（简化版，一个 run 方法一步带过）。"""

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
        effective_settings, settings_diff = StrategySettings.calculate_effective_settings(
            strategy_info=strategy_info,
            runtime_settings=runtime_settings or {},
        )

        # Step 2: Fingerprint 生成（参数获取逻辑内聚在 Fingerprint 内部）
        settings_fp, env_fp = cls._generate_fingerprints(
            effective_settings=effective_settings,
            settings_diff=settings_diff,
            strategy_info=strategy_info,
        )

        # Step 3: 查缓存
        if not ignore_cache:
            cache = cls._find_cache_by_fingerprints(settings_fp, env_fp)
            if cache:
                return cls._load_result_from_cache(cache)

        # Step 4: 准备执行
        global_data = cls._load_global_data(effective_settings)
        jobs = JobBuilder.build_child_process_jobs(strategy_info, effective_settings, global_data)

        # Step 5: 执行回测
        results = cls._execute_backtest(jobs, strategy_info, effective_settings)

        # Step 6: Report 生成
        version_info = cls._save_results_and_metadata(
            results=results,
            strategy_info=strategy_info,
            effective_settings=effective_settings,
            settings_fp=settings_fp,
            env_fp=env_fp,
        )

        return version_info

    @classmethod
    def _generate_fingerprints(
        cls,
        effective_settings: StrategySettings,
        settings_diff: Dict[str, Any],
        strategy_info: EnabledStrategyInfo,
    ) -> tuple[str, str]:
        """生成 settings 和 env 指纹（参数获取逻辑内聚在 Fingerprint 内部）。

        Args:
            effective_settings: 有效策略配置（StrategySettings 对象）
            settings_diff: Settings 差异字段（用户修改的 settings）
            strategy_info: EnabledStrategyInfo 对象

        Returns:
            (settings_fp, env_fp) 元组

        设计：
        - settings_fp: 基于 settings_diff 的 hash（设置变化）
        - env_fp: 基于环境信息的 hash（entity_ids, execution_mode, hooks 等）
        - 参数获取逻辑内聚在 Fingerprint.to_env_fingerprint() 内部（不再分散）
        """
        settings_fp = Fingerprint.to_settings_diff_fingerprint(settings_diff)
        env_fp = Fingerprint.to_env_fingerprint(
            strategy_info=strategy_info,
            effective_settings=effective_settings,
        )

        return settings_fp, env_fp

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

    @classmethod
    def _load_global_data(cls, effective_settings: StrategySettings) -> Dict[str, Any]:
        """加载全局数据（用于共享内存）。

        Args:
            effective_settings: 有效策略配置

        Returns:
            全局数据字典

        TODO: 实现完整的全局数据加载逻辑（使用 GlobalEntityCache）
        """
        # TODO: 实现全局数据加载逻辑
        return {}

    @classmethod
    def _execute_backtest(
        cls,
        jobs: List[Dict[str, Any]],
        strategy_info: EnabledStrategyInfo,
        effective_settings: StrategySettings,
    ) -> Dict[str, Any]:
        """执行回测（调用 backtest engine）。

        Args:
            jobs: Job 列表
            strategy_info: EnabledStrategyInfo 对象
            effective_settings: 有效策略配置

        Returns:
            回测结果

        TODO: 实现完整的回测执行逻辑
        """
        # TODO: 实现回测执行逻辑
        return {}

    @classmethod
    def _save_results_and_metadata(
        cls,
        results: Dict[str, Any],
        strategy_info: EnabledStrategyInfo,
        effective_settings: StrategySettings,
        settings_fp: str,
        env_fp: str,
    ) -> Dict[str, Any]:
        """保存结果和 metadata。

        Args:
            results: 回测结果
            strategy_info: EnabledStrategyInfo 对象
            effective_settings: 有效策略配置
            settings_fp: Settings 指纹
            env_fp: Env 指纹

        Returns:
            Version 信息（包含 version_id、output_dir 等）

        TODO: 实现完整的结果保存逻辑
        """
        # TODO: 实现结果保存逻辑
        return {}


__all__ = ["EnumeratorPipeline"]