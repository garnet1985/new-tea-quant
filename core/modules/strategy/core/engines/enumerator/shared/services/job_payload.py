"""公共 job payload 组装（entity / slice JobBuilder 共用主体）。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)

logger = logging.getLogger(__name__)


class JobPayloadBuilder:
    """组装 BacktestEngine job payload 的公共字段。

    边界:
    - 负责: entity_specified / entity_shared / global / shm / strategy_info / settings
    - 不负责: slice 专有 open_dates / backtest_calendar（由 slice JobBuilder 追加）
    - 调用方: entity_based / slice_based JobBuilder
    """

    @staticmethod
    def resolve_period(effective_settings: StrategySettings) -> Any:
        from core.modules.strategy.core.engines.enumerator.shared.report_manager.runtime_snapshot import (
            RuntimeReport,
        )

        return RuntimeReport.resolve_period(effective_settings)

    @staticmethod
    def build_core_payload(
        *,
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
        ids = [str(entity_id).strip() for entity_id in entity_ids if str(entity_id).strip()]
        if not ids:
            logger.warning("entity_ids 为空，无法构建 bundle job")
            return {
                "entity_specified": [],
                "entity_shared": {},
            }

        entity_shared: Dict[str, Dict[str, Any]] = {}
        for declaration in per_entity_declarations:
            data_key = declaration["data_key"]
            entity_shared[data_key] = {
                "params": declaration.get("params", {}),
                "start": start_date,
                "end": end_date,
                "indicators": declaration.get("indicators", {}),
            }

        global_data_keys: Dict[str, Any] = {}
        for declaration in global_declarations:
            data_key = declaration["data_key"]
            global_data_keys[data_key] = {}

        entity_specified: List[Dict[str, Any]] = [{"id": entity_id} for entity_id in ids]

        payload: Dict[str, Any] = {
            "entity_specified": entity_specified,
            "entity_shared": entity_shared,
            "global": global_data_keys,
            "shm_info": shm_info,
            "entities_count": len(ids),
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
            "JobPayloadBuilder.build_core_payload() 成功："
            "entity_count=%d, per_entity_keys=%d, global_keys=%d, shm_name=%s",
            len(ids),
            len(entity_shared),
            len(global_data_keys),
            payload["shm_info"].get("shm_name"),
        )
        return payload


__all__ = ["JobPayloadBuilder"]
