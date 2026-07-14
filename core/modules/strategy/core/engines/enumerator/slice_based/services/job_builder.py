#!/usr/bin/env python3
"""slice_based Job 构建：对齐 entity_based payload，并补齐 BE.slice_based 契约字段。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from core.modules.strategy.core.engines.enumerator.slice_based.resolver.calendar import (
    BacktestCalendarResolver,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)

logger = logging.getLogger(__name__)


class JobBuilder:
    """无状态：组装单 bulk job 交给 ``BacktestEngine.slice_based``。

    TODO(extract-shared): payload 主体（entity_specified / entity_shared / global /
    shm_info / strategy_info / settings / output_recorder）与
    ``entity_based.services.job_builder.JobBuilder`` 同构；本类额外写入
    ``open_dates`` / ``backtest_calendar`` / ``stock_ids`` / ``entity_ids``。
    """

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
        from core.modules.strategy.core.engines.enumerator.shared.report_manager.runtime_snapshot import (
            RuntimeReport,
        )

        period = RuntimeReport.resolve_period(effective_settings)
        start_date = period.start_date
        end_date = period.end_date

        open_dates, calendar_dict = BacktestCalendarResolver.resolve(
            settings=effective_settings.raw_settings,
            start_date=start_date,
            end_date=end_date,
        )

        payload = JobBuilder._build_payload(
            strategy_info=strategy_info,
            effective_settings=effective_settings,
            entity_ids=entity_ids,
            global_declarations=global_declarations,
            per_entity_declarations=per_entity_declarations,
            shm_info=shm_info,
            start_date=start_date,
            end_date=end_date,
            open_dates=open_dates,
            backtest_calendar=calendar_dict,
            output_recorder_snapshot=output_recorder_snapshot,
        )
        return [{"id": "strategy_run", "payload": payload}]

    @staticmethod
    def _build_payload(
        *,
        strategy_info: EnabledStrategyInfo,
        effective_settings: StrategySettings,
        entity_ids: List[str],
        global_declarations: List[Dict[str, Any]],
        per_entity_declarations: List[Dict[str, Any]],
        shm_info: Dict[str, Any],
        start_date: str,
        end_date: str,
        open_dates: List[str],
        backtest_calendar: Dict[str, Any],
        output_recorder_snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        ids = [str(entity_id).strip() for entity_id in entity_ids if str(entity_id).strip()]
        if not ids:
            logger.warning("entity_ids 为空，无法构建 slice bulk job")
            return {
                "entity_specified": [],
                "entity_shared": {},
                "stock_ids": [],
                "entity_ids": [],
                "open_dates": [],
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

        # BE.slice_based：open_dates + stock_ids/entity_ids
        # 业务 worker：可继续用 entity_specified / entity_shared / shm_info（与 entity 对齐）
        payload: Dict[str, Any] = {
            "entity_specified": entity_specified,
            "entity_shared": entity_shared,
            "global": global_data_keys,
            "shm_info": shm_info,
            "entities_count": len(ids),
            "stock_ids": list(ids),
            "entity_ids": list(ids),
            "open_dates": list(open_dates),
            "backtest_calendar": dict(backtest_calendar),
            "start_date": start_date,
            "end_date": end_date,
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
            "slice JobBuilder._build_payload() 成功："
            "entity_count=%d, open_dates=%d, per_entity_keys=%d, global_keys=%d, shm_name=%s",
            len(ids),
            len(open_dates),
            len(entity_shared),
            len(global_data_keys),
            payload["shm_info"].get("shm_name"),
        )
        return payload


__all__ = ["JobBuilder"]
