#!/usr/bin/env python3
"""Unified enumerator runtime facade for CLI and BFF."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.modules.data_manager import DataManager
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.simulator.enumerator import (
    OpportunityEnumeratorFlow,
    OpportunityEnumeratorSettings,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.services.cache.simulator_res_db_cache import (
    db_cache_fingerprint_pair_from_parts,
)
from core.modules.strategy.services.cache.simulator_res_db_cache.runtime.stock_universe import (
    stock_ids_for_enumerator_view,
)
from core.modules.strategy.services.cache.simulator_res_db_cache.config import derive_run_mode
from ..settings import StrategySettingsService
from core.modules.strategy.services.fingerprint import (
    StrategyFingerprintManager,
    StrategyFingerprintRuntimeService,
)
from core.modules.strategy.strategy_manager import StrategyManager
from core.utils.date.date_utils import DateUtils

logger = logging.getLogger(__name__)


def _run_mode_from_preprocessed(preprocessed: Any) -> str:
    api = getattr(preprocessed, "full_settings_snapshot_api", None)
    if not isinstance(api, dict) or not api:
        return "full"
    runtime = StrategySettingsService.api_to_runtime(dict(api))
    st = StrategySettings(raw_settings=dict(runtime))
    if not st.validate().is_usable():
        return "full"
    return derive_run_mode(st.to_dict())


@dataclass
class EnumeratorRuntimeContext:
    strategy_name: str
    strategy_info: Any
    settings_view: StrategySettingsView
    enum_settings: OpportunityEnumeratorSettings
    stock_list: List[str]
    start_date: str
    end_date: str
    flow: OpportunityEnumeratorFlow


class EnumeratorRuntimeService:
    """Single owner for canonical enumerate runtime/fingerprint/snapshot orchestration."""

    @staticmethod
    def build_canonical_settings(raw_settings: Dict[str, Any]) -> StrategySettingsView:
        return StrategySettingsView.from_dict(
            StrategyFingerprintManager.canonicalize_settings(raw_settings)
        )

    @classmethod
    def build_context(
        cls,
        *,
        strategy_name: str,
        strategy_info: Any,
        raw_settings_override: Optional[Dict[str, Any]] = None,
        stock_count: Optional[int] = None,
        workbench_run_id: Optional[str] = None,
        workbench_strategy_name: Optional[str] = None,
        force_refresh: bool = False,
    ) -> EnumeratorRuntimeContext:
        raw_settings = raw_settings_override if raw_settings_override is not None else strategy_info.settings.to_dict()
        settings_view = cls.build_canonical_settings(raw_settings)
        enum_settings = OpportunityEnumeratorSettings.from_base(settings_view)
        stock_list = stock_ids_for_enumerator_view(
            strategy_name=strategy_name,
            settings_view=settings_view,
            all_stocks=None,
            stock_count=stock_count,
        )
        data_manager = DataManager(is_verbose=False)
        latest_date = data_manager.service.calendar.get_latest_completed_trading_date()
        start_date = settings_view.start_date or DateUtils.DEFAULT_START_DATE
        end_date = settings_view.end_date or latest_date
        flow = OpportunityEnumeratorFlow(
            start_date=start_date,
            end_date=end_date,
            stock_list=stock_list,
            max_workers=enum_settings.max_workers,
            base_settings=settings_view,
            workbench_strategy_name=workbench_strategy_name,
            workbench_run_id=workbench_run_id,
            force_refresh=force_refresh,
        )
        return EnumeratorRuntimeContext(
            strategy_name=strategy_name,
            strategy_info=strategy_info,
            settings_view=settings_view,
            enum_settings=enum_settings,
            stock_list=stock_list,
            start_date=start_date,
            end_date=end_date,
            flow=flow,
        )

    @staticmethod
    def run_enum(context: EnumeratorRuntimeContext) -> List[Dict[str, Any]]:
        return context.flow.run(
            strategy_name=context.strategy_name,
            strategy_info=context.strategy_info,
        )

    @staticmethod
    def build_fingerprints(context: EnumeratorRuntimeContext) -> tuple[str, str]:
        return StrategyFingerprintRuntimeService.build_ids_for_runtime_context(context)

    @staticmethod
    def preprocess(context: EnumeratorRuntimeContext) -> Any:
        return context.flow.preprocess(
            strategy_name=context.strategy_name,
            strategy_info=context.strategy_info,
        )

    @staticmethod
    def build_ids_from_preprocessed(preprocessed: Any) -> tuple[str, str]:
        request_fp = getattr(preprocessed, "request_fingerprint", None)
        if request_fp is None:
            return "", ""
        return db_cache_fingerprint_pair_from_parts(
            semantic_core_payload=dict(request_fp.settings_core or {}),
            strategy_name=str(request_fp.strategy_name),
            stock_ids=list(request_fp.stock_ids),
            start_date=str(request_fp.start_date),
            end_date=str(request_fp.end_date),
            run_mode=_run_mode_from_preprocessed(preprocessed),
            worker_module_path=str(request_fp.worker_module_path),
            worker_class_name=str(request_fp.worker_class_name),
            worker_code_hash=str(request_fp.worker_code_hash),
            data_contract_mapping=str(request_fp.data_contract_mapping),
        )


__all__ = ["EnumeratorRuntimeContext", "EnumeratorRuntimeService"]
