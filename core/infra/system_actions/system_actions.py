"""SystemActions 门面 — cache / pipeline / scaffold。

方法内懒导入，避免包 import 时拉起 strategy/tag 重链。
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


class CacheNamespace:
    """缓存与模拟产物清理。"""

    @staticmethod
    def run(
        *,
        clear_db_cache: bool = False,
        clear_backtest_results: bool = False,
        clear_scan_results: bool = False,
        clear_userspace_ntq: bool = False,
    ) -> Dict[str, Any]:
        from core.infra.system_actions.cache_cleanup.cache_cleanup import CacheCleanup

        return CacheCleanup.run(
            clear_db_cache=clear_db_cache,
            clear_backtest_results=clear_backtest_results,
            clear_scan_results=clear_scan_results,
            clear_userspace_ntq=clear_userspace_ntq,
        )

    @staticmethod
    def clear_workbench_db() -> int:
        from core.infra.system_actions.cache_cleanup.cache_cleanup import CacheCleanup

        return CacheCleanup.clear_workbench_db_cache()

    @staticmethod
    def clear_backtest_results(*, strategy_names: Optional[Iterable[str]] = None) -> int:
        from core.infra.system_actions.cache_cleanup.cache_cleanup import CacheCleanup

        return CacheCleanup.clear_backtest_results_disk(strategy_names=strategy_names)

    @staticmethod
    def clear_scan_results(*, strategy_names: Optional[Iterable[str]] = None) -> int:
        from core.infra.system_actions.cache_cleanup.cache_cleanup import CacheCleanup

        return CacheCleanup.clear_scan_results_disk(strategy_names=strategy_names)

    @staticmethod
    def clear_strategy_results(*, strategy_names: Optional[Iterable[str]] = None) -> int:
        from core.infra.system_actions.cache_cleanup.cache_cleanup import CacheCleanup

        return CacheCleanup.clear_strategy_results_disk(strategy_names=strategy_names)

    @staticmethod
    def clear_userspace_ntq() -> None:
        from core.infra.system_actions.cache_cleanup.cache_cleanup import CacheCleanup

        CacheCleanup.clear_userspace_ntq_dir()


class PipelineNamespace:
    """全局 DuckDB pipeline 租约。"""

    @staticmethod
    def read_status() -> Dict[str, Any]:
        from core.infra.system_actions.cache_cleanup.pipeline_lease import PipelineLease

        return PipelineLease.read_status()

    @staticmethod
    def lease(
        *,
        kind: str,
        job_id: str,
        resource_key: str = "",
        label: str = "",
        domains: Optional[list] = None,
    ):
        """构造 ``PipelineLease`` 上下文管理器（等价于 contracts.PipelineLease）。"""
        from core.infra.system_actions.cache_cleanup.pipeline_lease import PipelineLease

        return PipelineLease(
            kind=kind,
            job_id=job_id,
            resource_key=resource_key,
            label=label,
            domains=domains,
        )


class ScaffoldNamespace:
    """从模板新建策略 / Tag。"""

    @staticmethod
    def create_strategy(raw_path: str):
        from core.infra.system_actions.shortcuts.create_new_strategy.scaffold import (
            StrategyScaffold,
        )

        return StrategyScaffold.create(raw_path)

    @staticmethod
    def create_tag(raw_path: str):
        from core.infra.system_actions.shortcuts.create_new_tag.scaffold import (
            TagScaffold,
        )

        return TagScaffold.create(raw_path)


class SystemActions:
    """系统级操作门面（Facade）。"""

    cache = CacheNamespace()
    pipeline = PipelineNamespace()
    scaffold = ScaffoldNamespace()


__all__ = ["SystemActions"]
