"""entity_based 核心计算：timeline 扫描。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.modules.data_contract.cache import ContractCacheManager
from core.modules.strategy.core.data.settings.strategy_settings import StrategySettings
from core.modules.strategy.core.engines.enumerator.entity_based.context.data import EntityDataContext
from core.modules.strategy.core.engines.shared.data_classes import Opportunity
from core.modules.strategy.core.helpers.opportunity_csv import OpportunityCsvHelper
from core.modules.strategy.core.helpers.opportunity_enrichment import OpportunityEnricher
from core.modules.strategy.core.helpers.stock_meta import StockMetaHelper
from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime
from core.modules.strategy.core.services.data.entity_data import EntityContractBatch, EntityDataLoader
from core.modules.strategy.core.services.data.strategy_data_config import StrategyDataConfig

logger = logging.getLogger(__name__)


class EntityBasedCompute:
    """单股 timeline：entity_init → 逐 K 线 scan。"""

    def __init__(
        self,
        payload: Dict[str, Any],
        *,
        contract_cache: Optional[ContractCacheManager] = None,
        job_batch: Optional[EntityContractBatch] = None,
    ) -> None:
        self.payload = dict(payload)
        self._contract_cache = contract_cache
        self._job_batch = job_batch

    def run(self) -> Dict[str, Any]:
        stock_id = str(self.payload["stock_id"]).strip()
        settings_dict = dict(self.payload["settings"])
        settings = StrategySettings(raw_settings=settings_dict)
        settings.apply_defaults()

        hook_runtime = StrategyHookRuntime.from_job_payload(self.payload, settings=settings)
        stock_info = StockMetaHelper.load(stock_id)
        stock_list = self._resolve_stock_list(stock_id)

        min_required = StrategyDataConfig(settings_dict).min_required_records
        actual_start = EntityDataLoader.enumeration_actual_start_date(
            str(self.payload["start_date"]),
            min_required,
        )

        data_loader = EntityDataLoader(
            stock_id=stock_id,
            settings=settings_dict,
            global_data=self.payload.get("global_data") or {},
            contract_cache=self._contract_cache,
        )
        try:
            data_loader.load(
                actual_start,
                str(self.payload["end_date"]),
                job_batch=self._job_batch,
                fresh_strategy_cache=self._job_batch is None,
            )

            entity_ctx = EntityDataContext.assemble_init(
                strategy_name=str(self.payload["strategy_name"]),
                settings=settings,
                stock_list=stock_list,
                entity_id=stock_id,
                entity_info=stock_info,
                data={},
            )
            hook_runtime.call_if_overridden("on_entity_init", entity_ctx)

            klines = data_loader.get_klines()
            if not klines or len(klines) < min_required:
                return self._success_payload(
                    stock_id=stock_id,
                    stock_info=stock_info,
                    opportunities=[],
                    skipped_short_data=True,
                )

            extra = entity_ctx.extra
            opportunities: List[Opportunity] = []
            opp_counter = 0
            passed_dates: List[str] = []

            for current_kline in klines:
                virtual_date = str(current_kline.get("date") or "")
                passed_dates.append(virtual_date)
                if len(passed_dates) < min_required:
                    continue

                data_of_today = data_loader.data_until(virtual_date)
                opportunity = self._scan_day(
                    hook_runtime=hook_runtime,
                    settings=settings,
                    stock_id=stock_id,
                    stock_info=stock_info,
                    stock_list=stock_list,
                    virtual_date=virtual_date,
                    data_of_today=data_of_today,
                    extra=extra,
                )
                if opportunity is None:
                    continue

                opp_counter += 1
                OpportunityEnricher.apply_trigger_fields(
                    opportunity,
                    settings=settings_dict,
                    strategy_name=str(self.payload["strategy_name"]),
                    stock_id=stock_id,
                    stock_info=stock_info,
                    trigger_date=virtual_date,
                    trigger_price=float(current_kline.get("close") or 0.0),
                    opportunity_index=opp_counter,
                )
                opportunities.append(opportunity)

            opportunities_dict = [row.to_dict() for row in opportunities]
            output_dir = str(self.payload.get("output_dir") or "").strip()
            if output_dir and opportunities_dict and not self.payload.get("_dispatch_probe"):
                OpportunityCsvHelper.write(Path(output_dir), stock_id, opportunities_dict)

            return self._success_payload(
                stock_id=stock_id,
                stock_info=stock_info,
                opportunities=opportunities_dict,
            )
        finally:
            data_loader.clear_working_state()

    def _scan_day(
        self,
        *,
        hook_runtime: StrategyHookRuntime,
        settings: StrategySettings,
        stock_id: str,
        stock_info: Dict[str, Any],
        stock_list: List[str],
        virtual_date: str,
        data_of_today: Dict[str, Any],
        extra: Dict[str, Any],
    ) -> Optional[Opportunity]:
        ctx = EntityDataContext.assemble_scan(
            strategy_name=str(self.payload["strategy_name"]),
            settings=settings,
            stock_list=stock_list,
            entity_id=stock_id,
            entity_info=stock_info,
            now=virtual_date,
            data=data_of_today,
            extra=extra,
        )
        hook_runtime.call("on_before_scan", ctx)
        opportunity = hook_runtime.call("scan_opportunity", ctx)
        hook_runtime.call(
            "on_after_scan",
            EntityDataContext.assemble_scan(
                strategy_name=str(self.payload["strategy_name"]),
                settings=settings,
                stock_list=stock_list,
                entity_id=stock_id,
                entity_info=stock_info,
                now=virtual_date,
                data=data_of_today,
                extra=extra,
                opportunity=opportunity if isinstance(opportunity, Opportunity) else None,
            ),
        )
        return opportunity if isinstance(opportunity, Opportunity) else None

    def _resolve_stock_list(self, stock_id: str) -> List[str]:
        global_data = self.payload.get("global_data")
        if isinstance(global_data, dict):
            stock_list = global_data.get("stock_list")
            if isinstance(stock_list, list) and stock_list:
                if all(isinstance(x, str) for x in stock_list):
                    return [str(x).strip() for x in stock_list if str(x).strip()]
        return [stock_id]

    @staticmethod
    def _success_payload(
        *,
        stock_id: str,
        stock_info: Dict[str, Any],
        opportunities: List[Dict[str, Any]],
        skipped_short_data: bool = False,
    ) -> Dict[str, Any]:
        return {
            "success": True,
            "stock_id": stock_id,
            "stock_name": str(stock_info.get("name") or stock_id),
            "opportunities": opportunities,
            "opportunity_count": len(opportunities),
            "skipped_short_data": skipped_short_data,
        }


__all__ = ["EntityBasedCompute"]
