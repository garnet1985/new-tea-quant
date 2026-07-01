"""entity_based execute_fn 实现：单股 timeline 枚举（只消费 job init 已装载的数据）。"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from core.modules.strategy.core.data.settings.strategy_settings import StrategySettings
from core.modules.strategy.core.engines.enumerator.entity_based.context.data import EntityBasedDataContext
from core.modules.strategy.core.engines.enumerator.entity_based.execute_payload import EntityBasedExecutePayload
from core.modules.strategy.core.engines.enumerator.entity_based.execute_result import EntityBasedExecuteResult
from core.modules.strategy.core.engines.enumerator.entity_based.job_init import EntityBasedJobSession
from core.modules.strategy.core.engines.shared.data_classes import Opportunity
from core.modules.strategy.core.helpers.opportunity_csv import OpportunityCsvHelper
from core.modules.strategy.core.helpers.opportunity_enrichment import OpportunityEnricher
from core.modules.strategy.core.helpers.stock_meta import StockMetaHelper
from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime
from core.modules.strategy.core.services.data.entity_data import EntityDataLoader
from core.modules.strategy.core.services.data.strategy_data_config import StrategyDataConfig

logger = logging.getLogger(__name__)


class EntityBasedExecutor:
    """单股执行体：在 job init 已批量装载的数据上，逐 bar 跑 hook。"""

    def __init__(
        self,
        payload: EntityBasedExecutePayload,
        *,
        session: EntityBasedJobSession,
    ) -> None:
        self.payload = payload
        self._session = session
        self._data_loader = session.loader_for(payload.entity_id)

    @classmethod
    def from_mapping(
        cls,
        raw: Mapping[str, Any],
        *,
        session: EntityBasedJobSession,
    ) -> EntityBasedExecutor:
        return cls(EntityBasedExecutePayload.from_mapping(raw), session=session)

    def execute(self) -> Dict[str, Any]:
        """运行单股枚举逻辑（不含数据 IO，数据由 job init 提供）。"""
        entity_id = self.payload.entity_id
        settings_dict = dict(self.payload.settings)
        settings = StrategySettings(raw_settings=settings_dict)
        settings.apply_defaults()

        hook_runtime = StrategyHookRuntime.from_job_payload(
            self.payload.to_mapping(),
            settings=settings,
        )
        entity_info = StockMetaHelper.load(entity_id)
        stock_list = [
            str(x).strip() for x in self.payload.global_data["stock_list"]
        ]
        min_required = StrategyDataConfig(settings_dict).min_required_records

        entity_ctx = EntityBasedDataContext.assemble(
            strategy_name=self.payload.strategy_name,
            settings=settings,
            stock_list=stock_list,
            entity_id=entity_id,
            entity_info=entity_info,
        )
        hook_runtime.call_if_overridden("on_entity_init", entity_ctx)

        bars = self._data_loader.get_klines()
        if not bars or len(bars) < min_required:
            return EntityBasedExecuteResult.completed(
                entity_id=entity_id,
                entity_name=str(entity_info.get("name") or entity_id),
                opportunities=[],
                skipped_short_data=True,
            ).to_dict()

        opportunities: List[Opportunity] = []
        opp_counter = 0

        for bar_index, current_bar in enumerate(bars):
            as_of = str(current_bar.get("date") or "")
            if bar_index + 1 < min_required:
                continue

            data_as_of = self._data_loader.data_until(as_of)
            opportunity = self._invoke_scan_hooks(
                hook_runtime=hook_runtime,
                base_ctx=entity_ctx,
                as_of=as_of,
                data_as_of=data_as_of,
            )
            if opportunity is None:
                continue

            opp_counter += 1
            close = float(current_bar["close"])
            OpportunityEnricher.apply_trigger_fields(
                opportunity,
                settings=settings_dict,
                strategy_name=self.payload.strategy_name,
                stock_id=entity_id,
                stock_info=entity_info,
                trigger_date=as_of,
                trigger_price=close,
                opportunity_index=opp_counter,
            )
            opportunities.append(opportunity)

        opportunities_dict = [row.to_dict() for row in opportunities]
        if opportunities_dict and not self.payload.extras.get("_dispatch_probe"):
            OpportunityCsvHelper.write(
                Path(self.payload.output_dir),
                entity_id,
                opportunities_dict,
            )

        return EntityBasedExecuteResult.completed(
            entity_id=entity_id,
            entity_name=str(entity_info.get("name") or entity_id),
            opportunities=opportunities_dict,
        ).to_dict()

    def _invoke_scan_hooks(
        self,
        *,
        hook_runtime: StrategyHookRuntime,
        base_ctx: EntityBasedDataContext,
        as_of: str,
        data_as_of: Dict[str, Any],
    ) -> Optional[Opportunity]:
        ctx = EntityBasedDataContext.fill(
            base_ctx,
            now=as_of,
            data=data_as_of,
        )
        hook_runtime.call("on_before_scan", ctx)
        opportunity = hook_runtime.call("scan_opportunity", ctx)
        hook_runtime.call(
            "on_after_scan",
            EntityBasedDataContext.fill(
                base_ctx,
                now=as_of,
                data=data_as_of,
                opportunity=opportunity if isinstance(opportunity, Opportunity) else None,
            ),
        )
        return opportunity if isinstance(opportunity, Opportunity) else None


__all__ = ["EntityBasedExecutor"]
