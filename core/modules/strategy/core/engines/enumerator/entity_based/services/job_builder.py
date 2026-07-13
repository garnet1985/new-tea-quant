#!/usr/bin/env python3
"""Job构建工具类（无状态）。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.backtest_engine.contracts import BacktestJob  # 保留用于导入
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)

logger = logging.getLogger(__name__)


class JobBuilder:
    """Job构建工具类（无状态，每次调用传入足够参数）。"""

    @staticmethod
    def build_backtest_engine_jobs(
        strategy_info: EnabledStrategyInfo,
        effective_settings: StrategySettings,
        entity_ids: List[str],
        global_declarations: List[Dict[str, Any]],
        per_entity_declarations: List[Dict[str, Any]],
        shm_info: Dict[str, Any],
        output_recorder_snapshot: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """准备执行：构建 BacktestEngine jobs（bundle job）。
        
        Args:
            strategy_info: EnabledStrategyInfo 对象
            effective_settings: 有效策略配置
            entity_ids: Entity ID列表
            global_declarations: 全局数据声明列表
            per_entity_declarations: Per_entity数据声明列表
            shm_info: 共享内存信息
        
        Returns:
            Bundle job 列表（包含所有 entity 信息）
        
        流程：
        1. 从settings获取simulation配置
        2. 构建bundle job（entity_specified + entity_shared + global）
        3. 转换为BacktestEngine需要的格式
        
        设计：
        - 保持大类之间通信都是raw data
        - JobBuilder无状态，可复用
        """
        # Step 1: 从 settings 解析 sampling 区间
        from core.modules.strategy.core.engines.enumerator.shared.report_manager.runtime_snapshot import (
            RuntimeSnapshot,
        )

        period = RuntimeSnapshot.resolve_period(effective_settings)
        start_date = period.start_date
        end_date = period.end_date
        # Step 2: 构建 payload
        payload = JobBuilder._build_payload(
            strategy_info=strategy_info,
            effective_settings=effective_settings,
            entity_ids=entity_ids,
            global_declarations=global_declarations,
            per_entity_declarations=per_entity_declarations,
            shm_info=shm_info,
            start_date=start_date,
            end_date=end_date,
            output_recorder_snapshot=output_recorder_snapshot,
        )
        
        # Step 3: 直接返回dict列表（BacktestEngine会验证）
        return [{"id": "strategy_run", "payload": payload}]

    @staticmethod
    def _build_payload(
        strategy_info: EnabledStrategyInfo,
        effective_settings: StrategySettings,
        entity_ids: List[str],
        global_declarations: List[Dict[str, Any]],
        per_entity_declarations: List[Dict[str, Any]],
        shm_info: Dict[str, Any],
        start_date: str,
        end_date: str,
        output_recorder_snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        """构建bundle payload（内部方法）。
        
        Args:
            strategy_info: 启用的策略信息
            effective_settings: 有效策略配置
            entity_ids: Entity ID列表
            global_declarations: 全局数据声明列表
            per_entity_declarations: Per_entity数据声明列表
            shm_info: 共享内存信息
            start_date: 回测开始日期
            end_date: 回测结束日期
        
        Returns:
            payload dict
        
        设计：
        - 不创建BacktestJob对象
        - 直接返回payload dict
        - BacktestEngine会验证格式
        
        payload结构：
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
        """
        # 检查entity_ids
        if not entity_ids:
            logger.warning("entity_ids为空，无法构建 bundle job")
            return {
                "entity_specified": [],
                "entity_shared": {},
            }

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
            "shm_info": shm_info,  # 直接使用传入的shm_info
            "entities_count": len(entity_ids),
            "strategy_info": {
                "key": strategy_info.key,
                "unique_relative_path": strategy_info.unique_relative_path,
                "hooks_module_path": strategy_info.hooks_module_path,
                "hooks_class_name": strategy_info.hooks_class.__name__,
                "hooks_file_path": str(strategy_info.strategy_file.resolve()),
            },
            "settings": effective_settings.to_dict(),
            "output_recorder": output_recorder_snapshot,
        }

        logger.info(
            f"JobBuilder._build_payload() 成功："
            f"entity_count={len(entity_ids)}, "
            f"per_entity_keys={len(entity_shared)}, "
            f"global_keys={len(global_data_keys)}, "
            f"shm_name={payload['shm_info'].get('shm_name')}"
        )

        return payload


__all__ = ["JobBuilder"]