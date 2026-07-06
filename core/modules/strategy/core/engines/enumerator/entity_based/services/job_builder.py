#!/usr/bin/env python3
"""Job构建工具类（无状态）。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.backtest_engine.contracts import BacktestJob
from core.modules.strategy.core.engines.shared.services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery.discovered_strategy import (
    EnabledStrategyInfo,
)

logger = logging.getLogger(__name__)


class JobBuilder:
    """Job构建工具类（无状态，每次调用传入足够参数）。"""

    @staticmethod
    def build_bundle_job(
        strategy_info: EnabledStrategyInfo,
        effective_settings: StrategySettings,
        global_entity_cache: GlobalEntityCache,
        start_date: str,
        end_date: str,
    ) -> BacktestJob:
        """构建一个 bundle job（entity_specified + entity_shared + global 三层结构）。

        Args:
            strategy_info: 启用的策略信息
            effective_settings: 有效策略配置
            global_entity_cache: 全局数据缓存（包含entity_ids和declarations）
            start_date: 回测开始日期
            end_date: 回测结束日期

        Returns:
            BacktestJob: bundle job（包含所有 entity 信息）

        结构设计：
        {
            entity_specified: [{"id": "600000.SH"}, {"id": "600001.SH"}],
            entity_shared: {
                "stockline.daily": {params, start, end, indicators},
                "corporate_finance": {...}
            },
            global: {
                "gdp": {},  # 数据已在共享内存，只需声明
                "trade_calendar": {}
            },
            shm_info: {...},
            strategy_info: {...},
            settings: {...}
        }

        execute_fn逻辑：
        - 遍历entity_shared：加载per_entity数据（需要entity_id）
        - 遍历global：从共享内存读取global数据
        - 合并：per_entity_data + global_data = 完整数据
        """
        # 获取 entity_ids（从 GlobalEntityCache）
        entity_ids = global_entity_cache.get_entity_ids()
        if not entity_ids:
            logger.warning("entity_ids为空，无法构建 bundle job")
            return BacktestJob(
                id="strategy_run",
                payload={
                    "entity_specified": [],
                    "entity_shared": {},
                }
            )

        # 获取declarations（分组）
        global_declarations = global_entity_cache.get_global_declarations()
        per_entity_declarations = global_entity_cache.get_per_entity_declarations()

        # 构建 entity_shared（只包含per_entity数据的公用字段）
        entity_shared: Dict[str, Dict[str, Any]] = {}
        for declaration in per_entity_declarations:
            data_key = declaration["data_key"]
            entity_shared[data_key] = {
                "params": declaration.get("params", {}),
                "start": start_date,
                "end": end_date,
                "indicators": declaration.get("indicators", {}),
            }

        # 构建 global（只包含global数据的声明）
        global_data_keys: Dict[str, Any] = {}
        for declaration in global_declarations:
            data_key = declaration["data_key"]
            global_data_keys[data_key] = {}  # 数据已在共享内存，只需声明

        # 构建 entity_specified（entity元信息）
        entity_specified: List[Dict[str, Any]] = [
            {"id": entity_id} for entity_id in entity_ids
        ]

        # 构建 payload
        payload: Dict[str, Any] = {
            "entity_specified": entity_specified,
            "entity_shared": entity_shared,
            "global": global_data_keys,
            "shm_info": global_entity_cache.get_shm_info(),
            "strategy_info": {
                "key": strategy_info.key,
                "unique_relative_path": strategy_info.unique_relative_path,
                "hooks_module_path": strategy_info.hooks_module_path,
                "hooks_class_name": strategy_info.hooks_class.__name__,
            },
            "settings": effective_settings.to_dict(),
        }

        # 构建 bundle job
        job = BacktestJob(
            id="strategy_run",
            payload=payload,
        )

        logger.info(
            f"JobBuilder.build_bundle_job() 成功："
            f"entity_count={len(entity_ids)}, "
            f"per_entity_keys={len(entity_shared)}, "
            f"global_keys={len(global_data_keys)}, "
            f"shm_name={payload['shm_info'].get('shm_name')}"
        )

        return job


__all__ = ["JobBuilder"]