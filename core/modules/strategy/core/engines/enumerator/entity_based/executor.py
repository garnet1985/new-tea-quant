# """entity_based execute_fn 实现：单股 timeline 枚举（只消费 job init 已装载的数据）。"""
# from __future__ import annotations

# import logging
# from pathlib import Path
# from typing import Any, Dict, List, Mapping, Optional, Tuple

# from core.modules.strategy.core.data.settings.strategy_settings import StrategySettings
# from core.modules.strategy.core.engines.enumerator.entity_based.runtime_context.data import EntityBasedDataContext
# from core.modules.strategy.core.engines.enumerator.entity_based.execute_payload import EntityBasedExecutePayload
# from core.modules.strategy.core.engines.enumerator.entity_based.execute_result import EntityBasedExecuteResult
# from core.modules.strategy.core.engines.enumerator.entity_based.job_session import (
#     EntityBasedJobSession,
# )
# from core.modules.strategy.core.engines.shared.data_classes import Opportunity
# from core.modules.strategy.core.helpers.opportunity_csv import OpportunityCsvHelper
# from core.modules.strategy.core.helpers.opportunity_enrichment import OpportunityEnricher
# from core.modules.strategy.core.helpers.stock_meta import StockMetaHelper
# from core.modules.strategy.core.hooks.runtime import StrategyHookRuntime
# from core.modules.strategy.core.services.data.strategy_data_config import StrategyDataConfig

# logger = logging.getLogger(__name__)


# class EntityBasedExecutor:
#     """单股执行体：按开市日历推进，仅在新 base bar 日跑 hook。"""

#     def __init__(
#         self,
#         payload: EntityBasedExecutePayload,
#         *,
#         session: EntityBasedJobSession,
#     ) -> None:
#         self.payload = payload
#         self._session = session
#         self._data_loader = session.loader_for(payload.entity_id)

#     @classmethod
#     def from_mapping(
#         cls,
#         raw: Mapping[str, Any],
#         *,
#         session: EntityBasedJobSession,
#     ) -> EntityBasedExecutor:
#         return cls(EntityBasedExecutePayload.from_mapping(raw), session=session)

#     def execute(self) -> Dict[str, Any]:
#         """运行单股枚举逻辑（不含数据 IO，数据由 job init 提供）。"""
#         entity_id = self.payload.entity_id
#         settings_dict = dict(self.payload.settings)
#         settings = StrategySettings(raw_settings=settings_dict)
#         settings.apply_defaults()

#         data_config = StrategyDataConfig(settings_dict)
#         base_data_key = str(data_config.normalize_base(data_config.base)["data_key"])
#         min_required = data_config.min_required_records
#         open_dates = list(self.payload.open_dates)

#         hook_runtime = StrategyHookRuntime.from_job_payload(
#             self.payload.to_mapping(),
#             settings=settings,
#         )
#         entity_info = StockMetaHelper.load(entity_id)
#         stock_list = [
#             str(x).strip() for x in self.payload.global_data["stock_list"]
#         ]

#         entity_ctx = EntityBasedDataContext.assemble(
#             strategy_name=self.payload.strategy_name,
#             settings=settings,
#             stock_list=stock_list,
#             entity_id=entity_id,
#             entity_info=entity_info,
#         )
#         hook_runtime.call_if_overridden("on_entity_init", entity_ctx)

#         if not open_dates:
#             return EntityBasedExecuteResult.completed(
#                 entity_id=entity_id,
#                 entity_name=str(entity_info.get("name") or entity_id),
#                 opportunities=[],
#                 skipped_short_data=True,
#             ).to_dict()

#         opportunities: List[Opportunity] = []
#         opp_counter = 0
#         last_base_date: Optional[str] = None

#         for as_of in open_dates:
#             bar, data_as_of = self._base_bar_view(as_of, base_data_key=base_data_key)
#             if bar is None or data_as_of is None:
#                 continue
#             if len(data_as_of.get(base_data_key) or []) < min_required:
#                 continue

#             base_date = str(bar.get("date") or "")
#             if not base_date:
#                 continue
#             if last_base_date is not None and base_date == last_base_date:
#                 continue
#             last_base_date = base_date

#             opportunity = self._invoke_scan_hooks(
#                 hook_runtime=hook_runtime,
#                 base_ctx=entity_ctx,
#                 as_of=as_of,
#                 data_as_of=data_as_of,
#             )
#             if opportunity is None:
#                 continue

#             opp_counter += 1
#             close = float(bar["close"])
#             OpportunityEnricher.apply_trigger_fields(
#                 opportunity,
#                 settings=settings_dict,
#                 strategy_name=self.payload.strategy_name,
#                 stock_id=entity_id,
#                 stock_info=entity_info,
#                 trigger_date=base_date,
#                 trigger_price=close,
#                 opportunity_index=opp_counter,
#             )
#             opportunities.append(opportunity)

#         opportunities_dict = [row.to_dict() for row in opportunities]
#         if opportunities_dict and not self.payload.extras.get("_dispatch_probe"):
#             OpportunityCsvHelper.write(
#                 Path(self.payload.output_dir),
#                 entity_id,
#                 opportunities_dict,
#             )

#         return EntityBasedExecuteResult.completed(
#             entity_id=entity_id,
#             entity_name=str(entity_info.get("name") or entity_id),
#             opportunities=opportunities_dict,
#         ).to_dict()

#     def _base_bar_view(
#         self,
#         as_of: str,
#         *,
#         base_data_key: str,
#     ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
#         """Calendar as_of 的 PIT 视图；返回 (末根 base bar, hook data)。"""
#         data = self._data_loader.data_until(as_of)
#         base_rows = data.get(base_data_key)
#         if not isinstance(base_rows, list) or not base_rows:
#             return None, None
#         last = base_rows[-1]
#         if not isinstance(last, dict):
#             return None, None
#         for key in ("open", "high", "low", "close", "date"):
#             if key not in last:
#                 raise ValueError(
#                     f"K 线缺少字段 {key!r}: stock_id={self.payload.entity_id} as_of={as_of}"
#                 )
#         return last, data

#     def _invoke_scan_hooks(
#         self,
#         *,
#         hook_runtime: StrategyHookRuntime,
#         base_ctx: EntityBasedDataContext,
#         as_of: str,
#         data_as_of: Dict[str, Any],
#     ) -> Optional[Opportunity]:
#         ctx = EntityBasedDataContext.fill(
#             base_ctx,
#             now=as_of,
#             data=data_as_of,
#         )
#         hook_runtime.call("on_before_scan", ctx)
#         opportunity = hook_runtime.call("scan_opportunity", ctx)
#         hook_runtime.call(
#             "on_after_scan",
#             EntityBasedDataContext.fill(
#                 base_ctx,
#                 now=as_of,
#                 data=data_as_of,
#                 opportunity=opportunity if isinstance(opportunity, Opportunity) else None,
#             ),
#         )
#         return opportunity if isinstance(opportunity, Opportunity) else None


# __all__ = ["EntityBasedExecutor"]
